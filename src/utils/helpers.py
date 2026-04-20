"""
Yardimci fonksiyonlar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import OUTPUT_DIR, REPORTS_DIR, DASHBOARD_DIR


def ensure_directories():
    """Gerekli cikti dizinlerini olusturur."""
    for d in [OUTPUT_DIR, REPORTS_DIR, DASHBOARD_DIR]:
        os.makedirs(d, exist_ok=True)


def print_banner():
    """Program baslik banner'ini yazdirir."""
    banner = """
    ================================================
       Depresyon Analiz Sistemi (15 Soru)
       Pilot Calisma (10-50 Katilimci)
    ================================================
    """
    print(banner)


def print_section(title):
    """Bolum basligi yazdirir."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


def print_participant_summary(df):
    """Katilimci bazli ozet tablosu yazdirir."""
    print(f"\n{'Katilimci':<12} {'Yas':<8} {'Cinsiyet':<10} {'Skor':<6} {'Siddet':<15} {'Dep%':<8} {'Ensemble%':<10}")
    print("-" * 79)

    ensemble_col = "ensemble_depression_pct" if "ensemble_depression_pct" in df.columns else None

    for _, row in df.iterrows():
        pid = str(row.get("participant_id", "N/A"))[:10]
        age = str(row.get("age_range", "N/A"))[:6]
        gender = str(row.get("gender", "N/A"))[:8]
        score = int(row["total_score"])
        severity = row["severity"]
        dep_pct = row["depression_pct"]
        ens_pct = round(row[ensemble_col], 1) if ensemble_col else dep_pct
        print(f"{pid:<12} {age:<8} {gender:<10} {score:<6} {severity:<15} {dep_pct:<8} {ens_pct:<10}")
