"""
PHQ-9 klinik puanlama motoru.
Toplam skor hesaplama, siddet siniflandirmasi, soru bazli analiz ve
kritik soru 9 (intihar) icin ozel uyari mekanizmasi.
"""
import sys
import os

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import SEVERITY_LEVELS, PHQ9_QUESTIONS, MAX_SCORE, CRITICAL_QUESTION_INDEX
from src.google_forms.response_fetcher import get_question_columns


def calculate_total_scores(df):
    """Her katilimci icin toplam PHQ-9 skorunu (0-27) hesaplar."""
    q_cols = get_question_columns(df)
    df = df.copy()
    df["total_score"] = df[q_cols].sum(axis=1).astype(int)
    return df


def classify_severity(total_score):
    """Toplam skora gore depresyon siddet seviyesini belirler."""
    for level, info in SEVERITY_LEVELS.items():
        low, high = info["range"]
        if low <= total_score <= high:
            return level
    return "Bilinmiyor"


def get_depression_percentage(total_score):
    """Toplam skoru 0-100 arasi depresyon yuzdesi olarak dondurur."""
    return round((total_score / MAX_SCORE) * 100, 1)


def add_severity_classifications(df):
    """DataFrame'e siddet siniflandirmasi ve depresyon yuzdesini ekler."""
    df = df.copy()
    if "total_score" not in df.columns:
        df = calculate_total_scores(df)
    df["severity"] = df["total_score"].apply(classify_severity)
    df["depression_pct"] = df["total_score"].apply(get_depression_percentage)
    df["risk_level"] = df["severity"].apply(
        lambda s: SEVERITY_LEVELS.get(s, {}).get("risk_percent", "N/A")
    )
    return df


def analyze_question_scores(df):
    """Soru bazli ortalama, std ve frekans analizi yapar."""
    q_cols = get_question_columns(df)
    results = {}
    for i, col in enumerate(q_cols):
        question_text = PHQ9_QUESTIONS[i] if i < len(PHQ9_QUESTIONS) else f"Soru {i+1}"
        scores = df[col].astype(int)
        results[col] = {
            "question": question_text,
            "mean": round(scores.mean(), 2),
            "std": round(scores.std(), 2),
            "median": scores.median(),
            "score_distribution": {
                0: int((scores == 0).sum()),
                1: int((scores == 1).sum()),
                2: int((scores == 2).sum()),
                3: int((scores == 3).sum()),
            },
        }
    return results


def check_critical_question(df):
    """
    Kritik soru (kendine zarar verme dusuncesi) icin ozel uyari kontrolu.
    Skor >= 1 olan katilimcilari tespit eder.
    """
    q_cols = get_question_columns(df)
    crit_idx = CRITICAL_QUESTION_INDEX
    crit_col = q_cols[crit_idx] if len(q_cols) > crit_idx else None
    if crit_col is None:
        return []

    q_num = crit_idx + 1
    at_risk = df[df[crit_col].astype(int) >= 1].copy()
    warnings = []
    for _, row in at_risk.iterrows():
        pid = row.get("participant_id", "Bilinmiyor")
        crit_score = int(row[crit_col])
        severity_label = {1: "Dusuk", 2: "Orta", 3: "Yuksek"}
        warnings.append({
            "participant_id": pid,
            "q_critical_score": crit_score,
            "risk_label": severity_label.get(crit_score, "Bilinmiyor"),
            "message": (
                f"UYARI: {pid} katilimcisi Soru {q_num}'da (kendine zarar verme dusuncesi) "
                f"{crit_score}/3 skor vermistir. "
                f"Profesyonel degerlendirme onerilir."
            ),
        })
    return warnings


def get_severity_distribution(df):
    """Siddet seviyelerinin dagilimini dondurur."""
    if "severity" not in df.columns:
        df = add_severity_classifications(df)
    dist = df["severity"].value_counts().to_dict()
    # Tum seviyeleri dahil et (0 olanlar dahil)
    for level in SEVERITY_LEVELS:
        if level not in dist:
            dist[level] = 0
    return dist


def score_summary(df):
    """Genel skor ozetini dondurur."""
    if "total_score" not in df.columns:
        df = calculate_total_scores(df)
    if "severity" not in df.columns:
        df = add_severity_classifications(df)

    critical_warnings = check_critical_question(df)

    return {
        "total_participants": len(df),
        "mean_score": round(df["total_score"].mean(), 2),
        "median_score": df["total_score"].median(),
        "std_score": round(df["total_score"].std(), 2),
        "min_score": int(df["total_score"].min()),
        "max_score": int(df["total_score"].max()),
        "severity_distribution": get_severity_distribution(df),
        "mean_depression_pct": round(df["depression_pct"].mean(), 1),
        "q9_warnings_count": len(critical_warnings),
        "q9_warnings": critical_warnings,
    }


if __name__ == "__main__":
    from src.google_forms.response_fetcher import generate_demo_data

    df = generate_demo_data(30)
    df = calculate_total_scores(df)
    df = add_severity_classifications(df)

    print("\n=== PHQ-9 Skor Ozeti ===")
    summary = score_summary(df)
    for key, val in summary.items():
        if key != "q9_warnings":
            print(f"  {key}: {val}")

    print("\n=== Kritik Uyarilar ===")
    for w in summary["q9_warnings"]:
        print(f"  {w['message']}")

    print("\n=== Soru Bazli Analiz ===")
    q_analysis = analyze_question_scores(df)
    for col, info in q_analysis.items():
        print(f"  {col} ({info['question'][:40]}...): ort={info['mean']}, std={info['std']}")
