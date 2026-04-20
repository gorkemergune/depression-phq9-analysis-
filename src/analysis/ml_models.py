"""
ML modelleri modulu.
6 farkli algoritma: KMeans, Random Forest, Logistic Regression, SVM, Decision Tree, Gaussian NB.
Cross-validation, model karsilastirmasi ve ensemble voting.
Kucuk orneklem (5-50 kisi) icin optimize edilmistir.
"""
import sys
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import cross_val_score, train_test_split, LeaveOneOut
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report
from sklearn.decomposition import PCA

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import RANDOM_STATE, N_CLUSTERS_DEFAULT, CV_FOLDS, TEST_SIZE
from src.google_forms.response_fetcher import get_question_columns

warnings.filterwarnings("ignore")


def _prepare_features(df):
    """PHQ-9 soru skorlarini feature matrisi olarak hazirlar."""
    q_cols = get_question_columns(df)
    X = df[q_cols].values.astype(float)
    return X, q_cols


def _prepare_labels(df):
    """Severity etiketlerini encode eder."""
    le = LabelEncoder()
    y = le.fit_transform(df["severity"])
    return y, le


def _prepare_binary_labels(df):
    """Depresif (>=16) / Depresif degil (<16) binary etiketler."""
    y = (df["total_score"] >= 16).astype(int).values
    return y


def _safe_split(X, y, test_size=TEST_SIZE):
    """
    Kucuk orneklemde guvenli train/test split.
    Tek sinif varsa veya cok az veri varsa split yapmaz, tum veriyi kullanir.
    """
    n_classes = len(np.unique(y))
    n_samples = len(y)

    # Tek sinif varsa veya her sinifta en az 2 ornek yoksa split yapma
    if n_classes < 2:
        return X, X, y, y, False

    min_class_count = min(np.bincount(y))
    if min_class_count < 2 or n_samples < 6:
        return X, X, y, y, False

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_STATE, stratify=y
        )
        # Split sonrasi da tek sinif kalabilir
        if len(np.unique(y_train)) < 2:
            return X, X, y, y, False
        return X_train, X_test, y_train, y_test, True
    except ValueError:
        return X, X, y, y, False


def _safe_cv(model, X, y, cv_folds=CV_FOLDS):
    """Kucuk orneklemde guvenli cross-validation."""
    n_classes = len(np.unique(y))
    n_samples = len(y)

    if n_classes < 2:
        return np.array([1.0])

    if n_samples < 4:
        # Cok az veri, CV anlamsiz
        model.fit(X, y)
        return np.array([accuracy_score(y, model.predict(X))])

    # Leave-One-Out cok kucuk veri setleri icin (< 10)
    if n_samples < 10:
        try:
            scores = cross_val_score(model, X, y, cv=min(n_samples, n_classes + 1), scoring="accuracy")
            return scores
        except ValueError:
            model.fit(X, y)
            return np.array([accuracy_score(y, model.predict(X))])

    # Normal CV
    max_cv = min(cv_folds, n_samples, n_classes * 2)
    max_cv = max(max_cv, 2)
    try:
        return cross_val_score(model, X, y, cv=max_cv, scoring="accuracy")
    except ValueError:
        model.fit(X, y)
        return np.array([accuracy_score(y, model.predict(X))])


def run_kmeans_clustering(df, n_clusters=N_CLUSTERS_DEFAULT):
    """K-Means ile katilimcilari depresyon profil gruplarina ayirir."""
    X, q_cols = _prepare_features(df)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Cluster sayisi orneklem sayisindan fazla olamaz
    actual_clusters = min(n_clusters, len(df))
    if actual_clusters < 2:
        # 1 kisiyle clustering yapilamaz, tek gruplu sonuc dondur
        X_pca = np.column_stack([X_scaled[:, :1] if X_scaled.shape[1] >= 1 else X_scaled, np.zeros(len(X_scaled))])
        return {
            "model": None,
            "clusters": np.zeros(len(df), dtype=int),
            "pca_components": X_pca,
            "cluster_profiles": {"Grup 1": {"size": len(df), "mean_total": round(df["total_score"].mean(), 2)}},
            "inertia": 0.0,
            "n_clusters": 1,
            "scaler": scaler,
            "pca": None,
        }

    kmeans = KMeans(n_clusters=actual_clusters, random_state=RANDOM_STATE, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    # PCA - en az 2 feature olmali
    n_components = min(2, X_scaled.shape[1], X_scaled.shape[0])
    pca = PCA(n_components=n_components, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X_scaled)
    if n_components < 2:
        X_pca = np.column_stack([X_pca, np.zeros(len(X_pca))])

    cluster_profiles = {}
    for c in range(actual_clusters):
        mask = clusters == c
        cluster_profiles[f"Grup {c+1}"] = {
            "size": int(mask.sum()),
            "mean_total": round(df.loc[mask, "total_score"].mean(), 2) if mask.any() else 0,
        }

    return {
        "model": kmeans,
        "clusters": clusters,
        "pca_components": X_pca,
        "cluster_profiles": cluster_profiles,
        "inertia": round(kmeans.inertia_, 2),
        "n_clusters": actual_clusters,
        "scaler": scaler,
        "pca": pca,
    }


def run_random_forest(df):
    """Random Forest ile depresyon siddeti tahmini ve feature importance."""
    X, q_cols = _prepare_features(df)
    y, le = _prepare_labels(df)

    X_train, X_test, y_train, y_test, did_split = _safe_split(X, y)

    rf = RandomForestClassifier(
        n_estimators=100, random_state=RANDOM_STATE, class_weight="balanced"
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)

    cv_scores = _safe_cv(
        RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE, class_weight="balanced"),
        X, y
    )

    importances = rf.feature_importances_
    feature_importance = {
        q_cols[i]: round(importances[i], 4) for i in range(len(q_cols))
    }
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    return {
        "model": rf,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "feature_importance": feature_importance,
        "label_encoder": le,
        "classification_report": classification_report(
            y_test, y_pred, target_names=le.classes_, output_dict=True, zero_division=0
        ),
    }


def run_logistic_regression(df):
    """Logistic Regression ile binary siniflandirma ve olasilik skoru."""
    X, q_cols = _prepare_features(df)
    y_binary = _prepare_binary_labels(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_classes = len(np.unique(y_binary))

    if n_classes < 2:
        # Tek sinif: herkes ayni tarafta, klinik skora dayali olasilik uret
        probabilities = df["depression_pct"].values / 100.0
        return {
            "model": None,
            "scaler": scaler,
            "accuracy": 1.0,
            "cv_mean": 1.0,
            "cv_std": 0.0,
            "probabilities": probabilities,
            "precision": 1.0,
            "recall": 1.0,
        }

    X_train, X_test, y_train, y_test, did_split = _safe_split(X_scaled, y_binary)

    lr = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000, class_weight="balanced")
    lr.fit(X_train, y_train)
    y_pred = lr.predict(X_test)
    y_proba = lr.predict_proba(X_scaled)[:, 1]

    cv_scores = _safe_cv(
        LogisticRegression(random_state=RANDOM_STATE, max_iter=1000, class_weight="balanced"),
        X_scaled, y_binary
    )

    return {
        "model": lr,
        "scaler": scaler,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "probabilities": y_proba,
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
    }


def run_svm(df):
    """SVM ile cok sinifli siddet tahmini."""
    X, q_cols = _prepare_features(df)
    y, le = _prepare_labels(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test, did_split = _safe_split(X_scaled, y)

    svm = SVC(kernel="rbf", random_state=RANDOM_STATE, class_weight="balanced", probability=True)
    svm.fit(X_train, y_train)
    y_pred = svm.predict(X_test)

    cv_scores = _safe_cv(
        SVC(kernel="rbf", random_state=RANDOM_STATE, class_weight="balanced", probability=True),
        X_scaled, y
    )

    return {
        "model": svm,
        "scaler": scaler,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "label_encoder": le,
        "classification_report": classification_report(
            y_test, y_pred, target_names=le.classes_, output_dict=True, zero_division=0
        ),
    }


def run_decision_tree(df):
    """Decision Tree ile yorumlanabilir karar agaci."""
    X, q_cols = _prepare_features(df)
    y, le = _prepare_labels(df)

    X_train, X_test, y_train, y_test, did_split = _safe_split(X, y)

    dt = DecisionTreeClassifier(
        max_depth=min(5, len(df) - 1), random_state=RANDOM_STATE, class_weight="balanced"
    )
    dt.fit(X_train, y_train)
    y_pred = dt.predict(X_test)

    cv_scores = _safe_cv(
        DecisionTreeClassifier(max_depth=min(5, len(df) - 1), random_state=RANDOM_STATE, class_weight="balanced"),
        X, y
    )

    importances = dt.feature_importances_
    feature_importance = {
        q_cols[i]: round(importances[i], 4) for i in range(len(q_cols))
    }
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    return {
        "model": dt,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "feature_importance": feature_importance,
        "label_encoder": le,
        "tree_depth": dt.get_depth(),
    }


def run_gaussian_nb(df):
    """Gaussian Naive Bayes ile siniflandirma."""
    X, q_cols = _prepare_features(df)
    y, le = _prepare_labels(df)

    X_train, X_test, y_train, y_test, did_split = _safe_split(X, y)

    gnb = GaussianNB()
    gnb.fit(X_train, y_train)
    y_pred = gnb.predict(X_test)

    cv_scores = _safe_cv(GaussianNB(), X, y)

    return {
        "model": gnb,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "label_encoder": le,
    }


def compare_models(rf_result, lr_result, svm_result, dt_result, gnb_result):
    """Tum modellerin performansini karsilastirir."""
    comparison = {
        "Random Forest": {
            "accuracy": rf_result["accuracy"],
            "cv_mean": rf_result["cv_mean"],
            "cv_std": rf_result["cv_std"],
        },
        "Logistic Regression": {
            "accuracy": lr_result["accuracy"],
            "cv_mean": lr_result["cv_mean"],
            "cv_std": lr_result["cv_std"],
        },
        "SVM": {
            "accuracy": svm_result["accuracy"],
            "cv_mean": svm_result["cv_mean"],
            "cv_std": svm_result["cv_std"],
        },
        "Decision Tree": {
            "accuracy": dt_result["accuracy"],
            "cv_mean": dt_result["cv_mean"],
            "cv_std": dt_result["cv_std"],
        },
        "Gaussian NB": {
            "accuracy": gnb_result["accuracy"],
            "cv_mean": gnb_result["cv_mean"],
            "cv_std": gnb_result["cv_std"],
        },
    }

    best_model = max(comparison.items(), key=lambda x: x[1]["cv_mean"])

    return {
        "comparison": comparison,
        "best_model": best_model[0],
        "best_cv_score": best_model[1]["cv_mean"],
    }


def calculate_ensemble_depression_pct(df, lr_result):
    """
    Ensemble yaklasimla her katilimci icin nihai depresyon yuzdesi hesaplar.
    PHQ-9 klinik skoru ve LR olasiligini birlestirir.
    """
    clinical_pct = df["depression_pct"].values
    ml_pct = lr_result["probabilities"] * 100

    # Agirlikli ortalama: %60 klinik, %40 ML
    ensemble_pct = 0.6 * clinical_pct + 0.4 * ml_pct
    ensemble_pct = np.clip(ensemble_pct, 0, 100).round(1)

    return ensemble_pct


def _skip_ml_result():
    """ML atlandi durumunda varsayilan sonuc."""
    return {
        "accuracy": 0.0,
        "cv_mean": 0.0,
        "cv_std": 0.0,
    }


def run_all_models(df):
    """Tum ML modellerini calistirir ve sonuclari dondurur."""
    n = len(df)
    print(f"  Veri seti: {n} katilimci")

    # Cok az katilimci icin sadece klinik puanlama yap, ML atla
    if n < 3:
        print("  [!] Cok az katilimci - ML modelleri atlanarak sadece klinik puanlama yapiliyor.")
        df = df.copy()
        df["ensemble_depression_pct"] = df["depression_pct"]

        dummy_comparison = {
            "comparison": {},
            "best_model": "N/A (yetersiz veri)",
            "best_cv_score": 0.0,
        }

        return {
            "kmeans": None,
            "random_forest": None,
            "logistic_regression": None,
            "svm": None,
            "decision_tree": None,
            "gaussian_nb": None,
            "comparison": dummy_comparison,
            "df_with_ensemble": df,
        }

    print("  K-Means Clustering calistiriliyor...")
    kmeans_result = run_kmeans_clustering(df)

    print("  Random Forest calistiriliyor...")
    rf_result = run_random_forest(df)

    print("  Logistic Regression calistiriliyor...")
    lr_result = run_logistic_regression(df)

    print("  SVM calistiriliyor...")
    svm_result = run_svm(df)

    print("  Decision Tree calistiriliyor...")
    dt_result = run_decision_tree(df)

    print("  Gaussian Naive Bayes calistiriliyor...")
    gnb_result = run_gaussian_nb(df)

    print("  Model karsilastirmasi yapiliyor...")
    comparison = compare_models(rf_result, lr_result, svm_result, dt_result, gnb_result)

    # Ensemble depresyon yuzdesi
    ensemble_pct = calculate_ensemble_depression_pct(df, lr_result)
    df = df.copy()
    df["ensemble_depression_pct"] = ensemble_pct

    return {
        "kmeans": kmeans_result,
        "random_forest": rf_result,
        "logistic_regression": lr_result,
        "svm": svm_result,
        "decision_tree": dt_result,
        "gaussian_nb": gnb_result,
        "comparison": comparison,
        "df_with_ensemble": df,
    }
