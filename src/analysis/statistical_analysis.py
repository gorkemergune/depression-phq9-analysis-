"""
Istatistiksel analiz modulu.
Tanimlayici istatistikler, korelasyon, t-test, guven araligi, normallik testi.
"""
import sys
import os

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.google_forms.response_fetcher import get_question_columns


def descriptive_statistics(df):
    """Tanimlayici istatistikler: ortalama, medyan, std, min, max."""
    scores = df["total_score"]
    return {
        "mean": round(scores.mean(), 2),
        "median": float(scores.median()),
        "std": round(scores.std(), 2),
        "min": int(scores.min()),
        "max": int(scores.max()),
        "q25": float(scores.quantile(0.25)),
        "q75": float(scores.quantile(0.75)),
        "iqr": float(scores.quantile(0.75) - scores.quantile(0.25)),
        "skewness": round(scores.skew(), 3),
        "kurtosis": round(scores.kurtosis(), 3),
        "n": len(scores),
    }


def age_depression_correlation(df):
    """Yas-depresyon korelasyonu (Pearson/Spearman)."""
    age_mapping = {
        "18-24": 21, "25-34": 29.5, "35-44": 39.5,
        "45-54": 49.5, "55-64": 59.5, "65+": 70,
    }
    df = df.copy()
    df["age_numeric"] = df["age_range"].map(age_mapping)

    if df["age_numeric"].isna().all():
        return {"error": "Yas verisi bulunamadi"}

    valid = df.dropna(subset=["age_numeric", "total_score"])
    if len(valid) < 3:
        return {"error": "Yeterli veri yok"}

    pearson_r, pearson_p = stats.pearsonr(valid["age_numeric"], valid["total_score"])
    spearman_r, spearman_p = stats.spearmanr(valid["age_numeric"], valid["total_score"])

    return {
        "pearson_r": round(pearson_r, 4),
        "pearson_p": round(pearson_p, 4),
        "spearman_r": round(spearman_r, 4),
        "spearman_p": round(spearman_p, 4),
        "interpretation": _interpret_correlation(pearson_r),
        "age_numeric": valid["age_numeric"].values,
        "scores": valid["total_score"].values,
    }


def _interpret_correlation(r):
    """Korelasyon katsayisini yorumlar."""
    abs_r = abs(r)
    if abs_r < 0.1:
        strength = "ihmal edilebilir"
    elif abs_r < 0.3:
        strength = "zayif"
    elif abs_r < 0.5:
        strength = "orta"
    elif abs_r < 0.7:
        strength = "guclu"
    else:
        strength = "cok guclu"
    direction = "pozitif" if r > 0 else "negatif"
    return f"{strength} {direction} korelasyon"


def gender_based_analysis(df):
    """Cinsiyet bazli depresyon dagilimi ve istatistiksel testler."""
    groups = {}
    for gender in df["gender"].unique():
        group_data = df[df["gender"] == gender]["total_score"]
        groups[gender] = {
            "n": len(group_data),
            "mean": round(group_data.mean(), 2),
            "std": round(group_data.std(), 2),
            "median": float(group_data.median()),
            "scores": group_data.values,
        }

    # Erkek vs Kadin karsilastirmasi
    test_result = {}
    genders = list(groups.keys())
    if len(genders) >= 2:
        g1_scores = groups[genders[0]]["scores"]
        g2_scores = groups[genders[1]]["scores"]

        if len(g1_scores) >= 3 and len(g2_scores) >= 3:
            # Normallik testi
            _, p1 = stats.shapiro(g1_scores) if len(g1_scores) <= 50 else (0, 0.05)
            _, p2 = stats.shapiro(g2_scores) if len(g2_scores) <= 50 else (0, 0.05)

            if p1 > 0.05 and p2 > 0.05:
                # Normal dagilim -> t-test
                t_stat, p_val = stats.ttest_ind(g1_scores, g2_scores)
                test_result = {
                    "test": "Independent t-test",
                    "statistic": round(t_stat, 4),
                    "p_value": round(p_val, 4),
                    "significant": p_val < 0.05,
                }
            else:
                # Normal olmayan -> Mann-Whitney U
                u_stat, p_val = stats.mannwhitneyu(g1_scores, g2_scores, alternative="two-sided")
                test_result = {
                    "test": "Mann-Whitney U",
                    "statistic": round(u_stat, 4),
                    "p_value": round(p_val, 4),
                    "significant": p_val < 0.05,
                }
            test_result["groups_compared"] = f"{genders[0]} vs {genders[1]}"

    return {"groups": groups, "test_result": test_result}


def question_frequency_analysis(df):
    """Soru bazli frekans analizi."""
    q_cols = get_question_columns(df)
    results = {}
    for col in q_cols:
        freq = df[col].astype(int).value_counts().sort_index().to_dict()
        # 0-3 arasi tum skorlari dahil et
        for i in range(4):
            freq.setdefault(i, 0)
        results[col] = dict(sorted(freq.items()))
    return results


def confidence_interval(df, confidence=0.95):
    """Ortalama skor icin %95 guven araligi hesaplar."""
    scores = df["total_score"].values
    n = len(scores)
    mean = np.mean(scores)
    if n < 2:
        return {
            "mean": round(mean, 2),
            "ci_lower": round(mean, 2),
            "ci_upper": round(mean, 2),
            "confidence": confidence,
            "se": 0.0,
            "margin_of_error": 0.0,
        }
    se = stats.sem(scores)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return {
        "mean": round(mean, 2),
        "ci_lower": round(mean - h, 2),
        "ci_upper": round(mean + h, 2),
        "confidence": confidence,
        "se": round(se, 3),
        "margin_of_error": round(h, 3),
    }


def normality_test(df):
    """Shapiro-Wilk normallik testi."""
    scores = df["total_score"].values
    if len(scores) < 3:
        return {"error": "Yeterli veri yok (min 3 gerekli)"}

    # Shapiro-Wilk (n <= 5000)
    stat, p_value = stats.shapiro(scores[:5000])
    return {
        "test": "Shapiro-Wilk",
        "statistic": round(stat, 4),
        "p_value": round(p_value, 4),
        "is_normal": p_value > 0.05,
        "interpretation": (
            "Normal dagilim varsayimi RED EDILEMEZ (p > 0.05)"
            if p_value > 0.05
            else "Normal dagilim varsayimi REDDEDILDI (p <= 0.05)"
        ),
    }


def question_correlation_matrix(df):
    """Sorular arasi korelasyon matrisi."""
    q_cols = get_question_columns(df)
    corr_matrix = df[q_cols].astype(float).corr()
    return corr_matrix


def run_all_statistical_analyses(df):
    """Tum istatistiksel analizleri calistirir."""
    print("  Tanimlayici istatistikler hesaplaniyor...")
    desc_stats = descriptive_statistics(df)

    print("  Yas-depresyon korelasyonu hesaplaniyor...")
    age_corr = age_depression_correlation(df)

    print("  Cinsiyet bazli analiz yapiliyor...")
    gender_analysis = gender_based_analysis(df)

    print("  Soru frekans analizi yapiliyor...")
    freq_analysis = question_frequency_analysis(df)

    print("  Guven araligi hesaplaniyor...")
    ci = confidence_interval(df)

    print("  Normallik testi yapiliyor...")
    normality = normality_test(df)

    print("  Korelasyon matrisi hesaplaniyor...")
    corr_matrix = question_correlation_matrix(df)

    return {
        "descriptive": desc_stats,
        "age_correlation": age_corr,
        "gender_analysis": gender_analysis,
        "frequency_analysis": freq_analysis,
        "confidence_interval": ci,
        "normality_test": normality,
        "correlation_matrix": corr_matrix,
    }
