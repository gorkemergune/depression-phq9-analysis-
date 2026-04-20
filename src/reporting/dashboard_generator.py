"""
HTML interaktif dashboard uretici.
Plotly grafikleri ve Jinja2 template ile tek dosya self-contained dashboard.
"""
import sys
import os
import json
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import DASHBOARD_DIR, TEMPLATES_DIR, PHQ9_QUESTIONS
from src.google_forms.response_fetcher import get_question_columns
from src.reporting.visualizations import (
    severity_pie_chart, participant_score_bar, question_radar_chart,
    age_scatter_plot, cluster_scatter_plot, feature_importance_bar,
    model_comparison_chart, gender_box_plot, correlation_heatmap,
    timeline_chart,
)


def _fig_to_json(fig):
    """Plotly figuru JSON data/layout olarak dondurur."""
    return {
        "data": json.loads(fig.to_json())["data"],
        "layout": json.loads(fig.to_json())["layout"],
    }


def _build_chart_scripts(charts):
    """Tum chart'lar icin Plotly.newPlot JavaScript kodlarini uretir."""
    scripts = []
    for div_id, fig in charts.items():
        if fig is None:
            continue
        fig_json = _fig_to_json(fig)
        # Dark layout merge
        script = (
            f"Plotly.newPlot('{div_id}', "
            f"{json.dumps(fig_json['data'])}, "
            f"Object.assign({{}}, darkLayout, {json.dumps(fig_json['layout'])}), config);"
        )
        scripts.append(script)
    return "\n".join(scripts)


def generate_dashboard(df, summary, ml_results, stat_results, output_path=None):
    """Interaktif HTML dashboard olusturur."""
    if output_path is None:
        os.makedirs(DASHBOARD_DIR, exist_ok=True)
        output_path = os.path.join(DASHBOARD_DIR, "dashboard.html")

    q_cols = get_question_columns(df)

    # Grafikleri olustur
    charts = {
        "chart-severity-pie": severity_pie_chart(df),
        "chart-radar": question_radar_chart(df),
        "chart-age-scatter": age_scatter_plot(df),
        "chart-gender-box": gender_box_plot(df),
        "chart-participant-bar": participant_score_bar(df),
    }

    # ML grafikleri (None degilse)
    if ml_results:
        if ml_results.get("kmeans"):
            charts["chart-cluster"] = cluster_scatter_plot(ml_results["kmeans"], df)
        if ml_results.get("random_forest"):
            charts["chart-feature-importance"] = feature_importance_bar(ml_results["random_forest"])
        if ml_results.get("comparison") and ml_results["comparison"].get("comparison"):
            charts["chart-model-comparison"] = model_comparison_chart(ml_results["comparison"])

    # Korelasyon heatmap
    if stat_results and "correlation_matrix" in stat_results:
        charts["chart-heatmap"] = correlation_heatmap(stat_results["correlation_matrix"])

    # Timeline
    tl = timeline_chart(df)
    charts["chart-timeline"] = tl

    # Chart scripts
    chart_scripts = _build_chart_scripts(charts)

    # Katilimci verileri
    participants = []
    ensemble_col = "ensemble_depression_pct" if "ensemble_depression_pct" in df.columns else None
    for _, row in df.iterrows():
        q_scores = [str(int(row[c])) for c in q_cols]
        participants.append({
            "participant_id": row.get("participant_id", "N/A"),
            "age_range": row.get("age_range", "N/A"),
            "gender": row.get("gender", "N/A"),
            "total_score": int(row["total_score"]),
            "severity": row["severity"],
            "depression_pct": row["depression_pct"],
            "ensemble_depression_pct": round(row[ensemble_col], 1) if ensemble_col else row["depression_pct"],
            "question_scores": " | ".join(q_scores),
        })

    # Template render
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("dashboard_template.html")

    html = template.render(
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        summary=summary,
        stats=stat_results,
        ml_comparison=ml_results["comparison"] if ml_results else {},
        participants=participants,
        chart_scripts=chart_scripts,
        timeline_chart_html=tl is not None,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard olusturuldu: {output_path}")
    return output_path
