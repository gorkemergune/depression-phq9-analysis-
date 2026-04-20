import sys
import os
import argparse
import platform
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import REPORTS_DIR, DASHBOARD_DIR
from src.utils.helpers import ensure_directories, print_banner, print_section, print_participant_summary


def open_file(path):
    """Dosyayi varsayilan uygulamayla acar."""
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        elif platform.system() == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def cmd_anket_olustur():
    """Google Forms'da PHQ-9 anketi olusturur."""
    print_section("Google Forms Anketi Olusturuluyor")
    from src.google_forms.form_creator import create_phq9_form
    form_id, form_url = create_phq9_form()
    return form_id, form_url


def cmd_analyze(df):
    """Tam analiz: PHQ-9 puanlama + ML + istatistik."""
    print_section("PHQ-9 Puanlama")
    from src.analysis.phq9_scorer import (
        calculate_total_scores, add_severity_classifications, score_summary,
    )
    df = calculate_total_scores(df)
    df = add_severity_classifications(df)
    summary = score_summary(df)

    print(f"  Toplam Katilimci: {summary['total_participants']}")
    print(f"  Ortalama Skor: {summary['mean_score']}")
    print(f"  Siddet Dagilimi: {summary['severity_distribution']}")

    critical_warnings = summary["q9_warnings"]
    if critical_warnings:
        print(f"\n  [!] {len(critical_warnings)} katilimcida kritik soru uyarisi:")
        for w in critical_warnings:
            print(f"      {w['message']}")

    print_section("ML Modelleri Calistiriliyor")
    from src.analysis.ml_models import run_all_models
    ml_results = run_all_models(df)
    df = ml_results["df_with_ensemble"]

    comp = ml_results["comparison"]
    print(f"\n  En iyi model: {comp['best_model']} (CV: {comp['best_cv_score']})")
    if comp["comparison"]:
        for name, metrics in comp["comparison"].items():
            print(f"    {name}: Acc={metrics['accuracy']}, CV={metrics['cv_mean']}+/-{metrics['cv_std']}")

    print_section("Istatistiksel Analiz")
    from src.analysis.statistical_analysis import run_all_statistical_analyses
    stat_results = run_all_statistical_analyses(df)

    desc = stat_results["descriptive"]
    ci = stat_results["confidence_interval"]
    norm = stat_results["normality_test"]
    print(f"  Ortalama: {desc['mean']}, Medyan: {desc['median']}, Std: {desc['std']}")
    print(f"  %95 Guven Araligi: [{ci['ci_lower']}, {ci['ci_upper']}]")
    print(f"  Normallik: {norm.get('interpretation', norm.get('error', 'Yetersiz veri'))}")

    print_section("Katilimci Sonuclari")
    print_participant_summary(df)

    return df, summary, ml_results, stat_results


def cmd_generate_report(df, summary, ml_results, stat_results):
    """Dashboard ve PDF raporlari olusturur."""
    ensure_directories()

    print_section("Grafikler Olusturuluyor")
    from src.reporting.visualizations import save_static_charts
    chart_dir = os.path.join(REPORTS_DIR, "charts")
    chart_paths = save_static_charts(df, ml_results, stat_results, chart_dir)
    print(f"  {len(chart_paths)} grafik kaydedildi")

    print_section("HTML Dashboard Olusturuluyor")
    from src.reporting.dashboard_generator import generate_dashboard
    dashboard_path = generate_dashboard(df, summary, ml_results, stat_results)

    print_section("PDF Raporlar Olusturuluyor")
    from src.reporting.pdf_report import generate_summary_report, generate_individual_reports
    summary_pdf = generate_summary_report(df, summary, ml_results, stat_results, chart_paths)
    individual_paths = generate_individual_reports(df)

    print_section("TAMAMLANDI!")
    print(f"  Dashboard : {dashboard_path}")
    print(f"  Genel PDF : {summary_pdf}")
    print(f"  Bireysel  : {len(individual_paths)} adet PDF")
    print()
    print("  Bireysel raporlar:")
    for p in individual_paths:
        print(f"    {os.path.basename(p)}")

    # Dashboard'u otomatik ac
    open_file(dashboard_path)
    print(f"\n  Dashboard tarayicida aciliyor...")

    return dashboard_path, summary_pdf, individual_paths


def cmd_sonuclar():
    """Forms API'den yanitlari ceker, analiz eder, rapor olusturur."""
    print_section("Google Forms'tan Yanitlar Cekiliyor")
    from src.google_forms.response_fetcher import fetch_responses_from_forms_api

    df = fetch_responses_from_forms_api()
    if df.empty:
        print("\n  Henuz kimse anketi doldurmamis!")
        print("  Anket linkini paylastiginizdan emin olun.")
        print("  Yanitlar geldikten sonra bu komutu tekrar calistirin.")
        return

    df, summary, ml_results, stat_results = cmd_analyze(df)
    cmd_generate_report(df, summary, ml_results, stat_results)


def cmd_demo():
    """Demo veri ile tam pipeline."""
    print_section("Demo Veri Olusturuluyor (30 kisi)")
    from src.google_forms.response_fetcher import generate_demo_data
    df = generate_demo_data(30)
    df, summary, ml_results, stat_results = cmd_analyze(df)
    cmd_generate_report(df, summary, ml_results, stat_results)


def cmd_full_pipeline(spreadsheet_id):
    """Sheets ID ile tam pipeline."""
    print_section("Google Sheets'ten Yanitlar Cekiliyor")
    from src.google_forms.response_fetcher import fetch_responses_from_sheets
    df = fetch_responses_from_sheets(spreadsheet_id)
    if df.empty:
        print("  Veri bulunamadi.")
        return
    df, summary, ml_results, stat_results = cmd_analyze(df)
    cmd_generate_report(df, summary, ml_results, stat_results)


def main():
    parser = argparse.ArgumentParser(
        description="PHQ-9 Depresyon Analiz Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true",
                       help="Demo veri ile tam dongu calistir")
    group.add_argument("--anket-olustur", action="store_true",
                       help="Google Forms'da PHQ-9 anketi olustur")
    group.add_argument("--sonuclar", action="store_true",
                       help="Forms API'den yanitlari cek + analiz + rapor")
    group.add_argument("--full-pipeline", metavar="SHEET_ID",
                       help="Google Sheets ID ile tam pipeline")

    args = parser.parse_args()
    print_banner()
    ensure_directories()

    if args.demo:
        cmd_demo()
    elif args.anket_olustur:
        cmd_anket_olustur()
    elif args.sonuclar:
        cmd_sonuclar()
    elif args.full_pipeline:
        cmd_full_pipeline(args.full_pipeline)


if __name__ == "__main__":
    main()
