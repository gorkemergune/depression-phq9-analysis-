"""
PDF rapor uretici.
fpdf2 ile genel ozet ve bireysel katilimci raporlari.
"""
import sys
import os
from datetime import datetime

from fpdf import FPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import REPORTS_DIR, SEVERITY_LEVELS, PHQ9_QUESTIONS, CRITICAL_QUESTION_INDEX
from src.google_forms.response_fetcher import get_question_columns


class PHQ9Report(FPDF):
    """PHQ-9 rapor PDF sinifi."""

    FONT_NAME = "ArialUnicode"

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        # Turkce karakter destekli Unicode font
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        font_loaded = False
        for fp in font_paths:
            if os.path.exists(fp):
                self.add_font(self.FONT_NAME, "", fp, uni=True)
                self.add_font(self.FONT_NAME, "B", fp, uni=True)
                self.add_font(self.FONT_NAME, "I", fp, uni=True)
                font_loaded = True
                break
        if not font_loaded:
            self.FONT_NAME = "Helvetica"

    def header(self):
        self.set_font(self.FONT_NAME, "B", 14)
        self.cell(0, 10, "PHQ-9 Depresyon Analiz Raporu", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.FONT_NAME, "", 8)
        self.cell(0, 5, f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.FONT_NAME, "I", 8)
        self.cell(0, 10, f"Sayfa {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font(self.FONT_NAME, "B", 12)
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def key_value(self, key, value):
        self.set_font(self.FONT_NAME, "B", 10)
        self.cell(60, 6, f"{key}:", new_x="END")
        self.set_font(self.FONT_NAME, "", 10)
        self.cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")

    def add_severity_color_cell(self, severity, width=40):
        colors = {
            "Minimal": (46, 204, 113),
            "Hafif": (243, 156, 18),
            "Orta": (230, 126, 34),
            "Orta-Siddetli": (231, 76, 60),
            "Siddetli": (192, 57, 43),
        }
        r, g, b = colors.get(severity, (150, 150, 150))
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font(self.FONT_NAME, "B", 10)
        self.cell(width, 7, f" {severity} ", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)


def generate_summary_report(df, summary, ml_results, stat_results, chart_paths=None, output_path=None):
    """Tum katilimcilarin genel ozet raporunu PDF olarak olusturur."""
    if output_path is None:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        output_path = os.path.join(REPORTS_DIR, "genel_ozet_raporu.pdf")

    pdf = PHQ9Report()
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. Genel Ozet
    pdf.section_title("Genel Ozet")
    pdf.key_value("Toplam Katilimci", summary["total_participants"])
    pdf.key_value("Ortalama Skor", summary["mean_score"])
    pdf.key_value("Medyan Skor", summary["median_score"])
    pdf.key_value("Standart Sapma", summary["std_score"])
    pdf.key_value("Soru Sayisi", len(PHQ9_QUESTIONS))
    pdf.key_value("Min / Max Skor", f'{summary["min_score"]} / {summary["max_score"]}')
    pdf.key_value("Ort. Depresyon Orani", f'{summary["mean_depression_pct"]}%')
    pdf.ln(3)

    # 2. Siddet Dagilimi
    pdf.section_title("Depresyon Siddet Dagilimi")
    for level, count in summary["severity_distribution"].items():
        risk = SEVERITY_LEVELS.get(level, {}).get("risk_percent", "N/A")
        pdf.set_font(pdf.FONT_NAME, "", 10)
        pdf.cell(40, 6, f"{level}:", new_x="END")
        pdf.cell(20, 6, str(count), new_x="END")
        pdf.cell(0, 6, f"(Risk: {risk})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 3. Istatistiksel Sonuclar
    if stat_results:
        pdf.section_title("Istatistiksel Analiz")

        ci = stat_results.get("confidence_interval", {})
        if ci:
            pdf.key_value("%95 Guven Araligi", f'[{ci.get("ci_lower", "N/A")}, {ci.get("ci_upper", "N/A")}]')

        norm = stat_results.get("normality_test", {})
        if norm and "interpretation" in norm:
            pdf.key_value("Normallik Testi", norm["interpretation"])

        age_corr = stat_results.get("age_correlation", {})
        if age_corr and "pearson_r" in age_corr:
            pdf.key_value("Yas-Depresyon Korelasyonu", f'r={age_corr["pearson_r"]} (p={age_corr["pearson_p"]})')
            pdf.key_value("Yorum", age_corr.get("interpretation", "N/A"))

        gender = stat_results.get("gender_analysis", {})
        test = gender.get("test_result", {})
        if test:
            pdf.key_value("Cinsiyet Karsilastirmasi", f'{test.get("test", "N/A")}')
            pdf.key_value("Test Istatistigi", f'{test.get("statistic", "N/A")} (p={test.get("p_value", "N/A")})')
            sig = "Anlamli fark VAR" if test.get("significant") else "Anlamli fark YOK"
            pdf.key_value("Sonuc", sig)
        pdf.ln(3)

    # 4. ML Sonuclari
    if ml_results and ml_results.get("comparison") and ml_results["comparison"].get("comparison"):
        pdf.section_title("ML Model Sonuclari")
        comp = ml_results["comparison"]
        pdf.key_value("En Iyi Model", comp["best_model"])
        pdf.key_value("En Iyi CV Skoru", comp["best_cv_score"])
        pdf.ln(2)

        # Model tablosu
        pdf.set_font(pdf.FONT_NAME, "B", 9)
        pdf.cell(50, 7, "Model", border=1, new_x="END")
        pdf.cell(30, 7, "Accuracy", border=1, new_x="END")
        pdf.cell(30, 7, "CV Ort.", border=1, new_x="END")
        pdf.cell(30, 7, "CV Std", border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font(pdf.FONT_NAME, "", 9)
        for name, metrics in comp["comparison"].items():
            pdf.cell(50, 6, name, border=1, new_x="END")
            pdf.cell(30, 6, str(metrics["accuracy"]), border=1, new_x="END")
            pdf.cell(30, 6, str(metrics["cv_mean"]), border=1, new_x="END")
            pdf.cell(30, 6, str(metrics["cv_std"]), border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # 5. Kritik Uyarilar
    if summary.get("q9_warnings"):
        pdf.section_title(f'Kritik Uyarilar - Soru 9 ({summary["q9_warnings_count"]} kisi)')
        for w in summary["q9_warnings"]:
            pdf.set_font(pdf.FONT_NAME, "", 9)
            pdf.set_text_color(192, 57, 43)
            pdf.multi_cell(0, 5, f'[!] {w["message"]}', new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # 6. Grafikleri ekle
    if chart_paths:
        pdf.add_page()
        pdf.section_title("Grafikler")
        for name, path in chart_paths.items():
            if os.path.exists(path):
                try:
                    pdf.image(path, w=170)
                    pdf.ln(5)
                    if pdf.get_y() > 240:
                        pdf.add_page()
                except Exception:
                    pass

    # 7. Katilimci tablosu
    pdf.add_page()
    pdf.section_title("Katilimci Detay Tablosu")
    q_cols = get_question_columns(df)

    # Landscape for wide table with many questions
    pdf.set_font(pdf.FONT_NAME, "B", 6)
    pdf.cell(14, 6, "ID", border=1, new_x="END")
    pdf.cell(12, 6, "Yas", border=1, new_x="END")
    pdf.cell(12, 6, "Cins.", border=1, new_x="END")
    pdf.cell(12, 6, "Skor", border=1, new_x="END")
    pdf.cell(18, 6, "Siddet", border=1, new_x="END")
    pdf.cell(12, 6, "Dep%", border=1, new_x="END")
    for i in range(len(q_cols)):
        pdf.cell(7, 6, f"S{i+1}", border=1, new_x="END")
    pdf.ln()

    pdf.set_font(pdf.FONT_NAME, "", 6)
    for _, row in df.iterrows():
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.section_title("Katilimci Detay Tablosu (devam)")
            pdf.set_font(pdf.FONT_NAME, "B", 6)
            pdf.cell(14, 6, "ID", border=1, new_x="END")
            pdf.cell(12, 6, "Yas", border=1, new_x="END")
            pdf.cell(12, 6, "Cins.", border=1, new_x="END")
            pdf.cell(12, 6, "Skor", border=1, new_x="END")
            pdf.cell(18, 6, "Siddet", border=1, new_x="END")
            pdf.cell(12, 6, "Dep%", border=1, new_x="END")
            for i in range(len(q_cols)):
                pdf.cell(7, 6, f"S{i+1}", border=1, new_x="END")
            pdf.ln()
            pdf.set_font(pdf.FONT_NAME, "", 6)

        pid = str(row.get("participant_id", ""))[:6]
        pdf.cell(14, 5, pid, border=1, new_x="END")
        pdf.cell(12, 5, str(row.get("age_range", ""))[:5], border=1, new_x="END")
        pdf.cell(12, 5, str(row.get("gender", ""))[:3], border=1, new_x="END")
        pdf.cell(12, 5, str(int(row["total_score"])), border=1, new_x="END")
        pdf.cell(18, 5, str(row["severity"])[:8], border=1, new_x="END")
        pdf.cell(12, 5, f'{row["depression_pct"]}', border=1, new_x="END")
        for c in q_cols:
            pdf.cell(7, 5, str(int(row[c])), border=1, new_x="END")
        pdf.ln()

    pdf.output(output_path)
    print(f"Genel ozet raporu olusturuldu: {output_path}")
    return output_path


def generate_individual_reports(df, output_dir=None):
    """Her katilimci icin bireysel PDF rapor olusturur."""
    if output_dir is None:
        output_dir = os.path.join(REPORTS_DIR, "bireysel")
    os.makedirs(output_dir, exist_ok=True)

    q_cols = get_question_columns(df)
    paths = []

    for _, row in df.iterrows():
        pid = row.get("participant_id", f"P{_}")
        pdf = PHQ9Report()
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.section_title(f"Bireysel Rapor: {pid}")
        pdf.key_value("Katilimci ID", pid)
        pdf.key_value("Yas Araligi", row.get("age_range", "N/A"))
        pdf.key_value("Cinsiyet", row.get("gender", "N/A"))
        pdf.key_value("Anket Tarihi", row.get("timestamp", "N/A"))
        pdf.ln(3)

        pdf.section_title("PHQ-9 Sonuclari")
        n_questions = len(PHQ9_QUESTIONS)
        pdf.key_value("Toplam Skor", f'{int(row["total_score"])} / {n_questions * 3}')
        pdf.key_value("Depresyon Yuzdesi", f'{row["depression_pct"]}%')
        pdf.ln(2)
        pdf.set_font(pdf.FONT_NAME, "B", 10)
        pdf.cell(30, 7, "Siddet Seviyesi: ", new_x="END")
        pdf.add_severity_color_cell(row["severity"])
        pdf.ln(2)

        risk = SEVERITY_LEVELS.get(row["severity"], {}).get("risk_percent", "N/A")
        pdf.key_value("Risk Araligi", risk)

        if "ensemble_depression_pct" in row:
            pdf.key_value("Ensemble Dep. %", f'{round(row["ensemble_depression_pct"], 1)}%')
        pdf.ln(3)

        # Soru bazli detay
        pdf.section_title("Soru Bazli Skorlar")
        for i, col in enumerate(q_cols):
            q_text = PHQ9_QUESTIONS[i] if i < len(PHQ9_QUESTIONS) else f"Soru {i+1}"
            score = int(row[col])
            pdf.set_font(pdf.FONT_NAME, "B", 9)
            pdf.cell(12, 5, f"S{i+1}:", new_x="END")
            pdf.set_font(pdf.FONT_NAME, "", 9)
            pdf.cell(15, 5, f"[{score}/3]", new_x="END")
            pdf.cell(0, 5, f"{q_text[:60]}", new_x="LMARGIN", new_y="NEXT")

        # Kritik soru uyarisi
        crit_idx = CRITICAL_QUESTION_INDEX
        if len(q_cols) > crit_idx:
            crit_score = int(row[q_cols[crit_idx]])
            if crit_score >= 1:
                pdf.ln(3)
                pdf.set_text_color(192, 57, 43)
                pdf.set_font(pdf.FONT_NAME, "B", 10)
                pdf.multi_cell(0, 6,
                    f"[!] UYARI: Soru {crit_idx + 1} (kendine zarar verme dusuncesi) skoru {crit_score}/3. "
                    "Profesyonel degerlendirme onerilir.",
                    new_x="LMARGIN", new_y="NEXT",
                )
                pdf.set_text_color(0, 0, 0)

        safe_pid = pid.replace("/", "_").replace("\\", "_")
        path = os.path.join(output_dir, f"rapor_{safe_pid}.pdf")
        pdf.output(path)
        paths.append(path)

    print(f"{len(paths)} bireysel rapor olusturuldu: {output_dir}")
    return paths
