"""
Gorsellestime modulu.
Plotly ile interaktif ve Matplotlib ile statik grafikler.
"""
import sys
import os
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import SEVERITY_LEVELS, PHQ9_QUESTIONS, DASHBOARD_DIR
from src.google_forms.response_fetcher import get_question_columns


def severity_pie_chart(df):
    """Depresyon siddet dagilimi pasta grafigi (Plotly)."""
    dist = df["severity"].value_counts().to_dict()
    labels = list(SEVERITY_LEVELS.keys())
    values = [dist.get(l, 0) for l in labels]
    colors = [SEVERITY_LEVELS[l]["color"] for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        hole=0.4,
        textinfo="label+percent+value",
    )])
    fig.update_layout(title="Depresyon Siddet Dagilimi", height=400)
    return fig


def participant_score_bar(df):
    """Katilimci bazli skor bar chart (Plotly)."""
    df_sorted = df.sort_values("total_score", ascending=True)
    colors = [SEVERITY_LEVELS.get(s, {}).get("color", "#95a5a6") for s in df_sorted["severity"]]

    fig = go.Figure(data=[go.Bar(
        x=df_sorted["total_score"],
        y=df_sorted["participant_id"],
        orientation="h",
        marker_color=colors,
        text=df_sorted["total_score"],
        textposition="outside",
    )])
    fig.update_layout(
        title="Katilimci Bazli PHQ-9 Skorlari",
        xaxis_title="Toplam Skor",
        yaxis_title="Katilimci",
        height=max(400, len(df) * 25),
    )
    return fig


def question_radar_chart(df):
    """Soru bazli ortalama skorlar radar chart (Plotly)."""
    q_cols = get_question_columns(df)
    means = [df[col].astype(float).mean() for col in q_cols]
    # Kisa etiketler
    labels = [f"S{i+1}" for i in range(len(q_cols))]

    fig = go.Figure(data=go.Scatterpolar(
        r=means + [means[0]],  # Kapali poligon
        theta=labels + [labels[0]],
        fill="toself",
        name="Ortalama Skor",
        line_color="#3498db",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
        title="Soru Bazli Ortalama Skorlar (Radar)",
        height=450,
    )
    return fig


def age_scatter_plot(df):
    """Yas vs depresyon scatter plot (Plotly)."""
    age_mapping = {
        "18-24": 21, "25-34": 29.5, "35-44": 39.5,
        "45-54": 49.5, "55-64": 59.5, "65+": 70,
    }
    df_plot = df.copy()
    df_plot["age_numeric"] = df_plot["age_range"].map(age_mapping)
    colors = [SEVERITY_LEVELS.get(s, {}).get("color", "#95a5a6") for s in df_plot["severity"]]

    fig = go.Figure(data=go.Scatter(
        x=df_plot["age_numeric"],
        y=df_plot["total_score"],
        mode="markers",
        marker=dict(size=10, color=colors, opacity=0.7, line=dict(width=1, color="white")),
        text=df_plot["participant_id"],
        hovertemplate="Katilimci: %{text}<br>Yas: %{x}<br>Skor: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title="Yas vs Depresyon Skoru",
        xaxis_title="Yas (tahmini)",
        yaxis_title="PHQ-9 Toplam Skor",
        height=400,
    )
    return fig


def cluster_scatter_plot(kmeans_result, df):
    """K-Means cluster gorsellestirmesi 2D PCA (Plotly)."""
    pca_data = kmeans_result["pca_components"]
    clusters = kmeans_result["clusters"]

    fig = go.Figure()
    for c in range(kmeans_result["n_clusters"]):
        mask = clusters == c
        fig.add_trace(go.Scatter(
            x=pca_data[mask, 0],
            y=pca_data[mask, 1],
            mode="markers",
            name=f"Grup {c+1}",
            marker=dict(size=10, opacity=0.7),
            text=df.loc[mask, "participant_id"] if "participant_id" in df.columns else None,
            hovertemplate="Katilimci: %{text}<br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<extra></extra>",
        ))
    fig.update_layout(
        title="K-Means Cluster Analizi (PCA 2D)",
        xaxis_title="Birinci Bilesen (PC1)",
        yaxis_title="Ikinci Bilesen (PC2)",
        height=450,
    )
    return fig


def feature_importance_bar(rf_result):
    """Feature importance bar chart (Plotly)."""
    fi = rf_result["feature_importance"]
    q_labels = {f"q{i+1}": f"S{i+1}: {PHQ9_QUESTIONS[i][:30]}..." for i in range(len(PHQ9_QUESTIONS))}

    labels = [q_labels.get(k, k) for k in fi.keys()]
    values = list(fi.values())

    fig = go.Figure(data=[go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color="#3498db",
    )])
    fig.update_layout(
        title="Random Forest - Soru Onem Sirasi",
        xaxis_title="Onem Skoru",
        height=400,
    )
    return fig


def model_comparison_chart(comparison_result):
    """Model karsilastirma accuracy chart (Plotly)."""
    comp = comparison_result["comparison"]
    models = list(comp.keys())
    accuracies = [comp[m]["accuracy"] for m in models]
    cv_means = [comp[m]["cv_mean"] for m in models]

    fig = go.Figure(data=[
        go.Bar(name="Test Accuracy", x=models, y=accuracies, marker_color="#3498db"),
        go.Bar(name="CV Ortalama", x=models, y=cv_means, marker_color="#e74c3c"),
    ])
    fig.update_layout(
        barmode="group",
        title="ML Model Performans Karsilastirmasi",
        yaxis_title="Accuracy",
        height=400,
    )
    return fig


def gender_box_plot(df):
    """Cinsiyet bazli box plot (Plotly)."""
    fig = go.Figure()
    for gender in df["gender"].unique():
        scores = df[df["gender"] == gender]["total_score"]
        fig.add_trace(go.Box(y=scores, name=gender, boxmean=True))
    fig.update_layout(
        title="Cinsiyet Bazli Depresyon Skor Dagilimi",
        yaxis_title="PHQ-9 Toplam Skor",
        height=400,
    )
    return fig


def correlation_heatmap(corr_matrix):
    """Soru korelasyon heatmap (Plotly)."""
    labels = [f"S{i+1}" for i in range(len(corr_matrix))]

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=labels,
        y=labels,
        colorscale="RdBu_r",
        zmin=-1,
        zmax=1,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}",
    ))
    fig.update_layout(
        title="Soru Korelasyon Matrisi",
        height=450,
        width=500,
    )
    return fig


def timeline_chart(df):
    """Anket tarihi bazli trend (Plotly)."""
    if "timestamp" not in df.columns:
        return None

    df_time = df.copy()
    df_time["date"] = pd.to_datetime(df_time["timestamp"]).dt.date
    daily = df_time.groupby("date")["total_score"].mean().reset_index()
    daily.columns = ["date", "mean_score"]
    daily = daily.sort_values("date")

    fig = go.Figure(data=go.Scatter(
        x=daily["date"],
        y=daily["mean_score"],
        mode="lines+markers",
        line=dict(color="#3498db", width=2),
        marker=dict(size=8),
    ))
    fig.update_layout(
        title="Zamana Gore Ortalama Depresyon Skoru",
        xaxis_title="Tarih",
        yaxis_title="Ortalama PHQ-9 Skor",
        height=350,
    )
    return fig


def save_static_charts(df, ml_results, stat_results, output_dir):
    """Matplotlib ile statik grafikleri PNG olarak kaydeder (PDF rapor icin)."""
    os.makedirs(output_dir, exist_ok=True)
    saved = {}

    # 1. Severity pie
    fig, ax = plt.subplots(figsize=(8, 6))
    dist = df["severity"].value_counts()
    labels = list(SEVERITY_LEVELS.keys())
    sizes = [dist.get(l, 0) for l in labels]
    colors = [SEVERITY_LEVELS[l]["color"] for l in labels]
    non_zero = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if non_zero:
        ax.pie(
            [x[1] for x in non_zero],
            labels=[x[0] for x in non_zero],
            colors=[x[2] for x in non_zero],
            autopct="%1.1f%%",
            startangle=90,
        )
    ax.set_title("Depresyon Siddet Dagilimi")
    path = os.path.join(output_dir, "severity_pie.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved["severity_pie"] = path

    # 2. Score distribution histogram
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df["total_score"], bins=14, range=(0, 27), color="#3498db", edgecolor="white", alpha=0.8)
    ax.set_title("PHQ-9 Skor Dagilimi")
    ax.set_xlabel("Toplam Skor")
    ax.set_ylabel("Katilimci Sayisi")
    ax.axvline(df["total_score"].mean(), color="red", linestyle="--", label=f'Ort: {df["total_score"].mean():.1f}')
    ax.legend()
    path = os.path.join(output_dir, "score_histogram.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved["score_histogram"] = path

    # 3. Question means bar
    q_cols = get_question_columns(df)
    fig, ax = plt.subplots(figsize=(10, 5))
    means = [df[col].astype(float).mean() for col in q_cols]
    q_labels = [f"S{i+1}" for i in range(len(q_cols))]
    bars = ax.bar(q_labels, means, color="#3498db", edgecolor="white")
    ax.set_title("Soru Bazli Ortalama Skorlar")
    ax.set_xlabel("Soru")
    ax.set_ylabel("Ortalama Skor (0-3)")
    ax.set_ylim(0, 3)
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f"{val:.2f}",
                ha="center", va="bottom", fontsize=9)
    path = os.path.join(output_dir, "question_means.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved["question_means"] = path

    # 4. Gender boxplot
    fig, ax = plt.subplots(figsize=(8, 5))
    gender_groups = [df[df["gender"] == g]["total_score"].values for g in df["gender"].unique()]
    gender_labels = list(df["gender"].unique())
    ax.boxplot(gender_groups, labels=gender_labels)
    ax.set_title("Cinsiyet Bazli Skor Dagilimi")
    ax.set_ylabel("PHQ-9 Toplam Skor")
    path = os.path.join(output_dir, "gender_boxplot.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved["gender_boxplot"] = path

    # 5. Model comparison
    if ml_results and ml_results.get("comparison") and ml_results["comparison"].get("comparison"):
        comp = ml_results["comparison"]["comparison"]
        fig, ax = plt.subplots(figsize=(10, 5))
        models = list(comp.keys())
        accs = [comp[m]["accuracy"] for m in models]
        cvs = [comp[m]["cv_mean"] for m in models]
        x = np.arange(len(models))
        w = 0.35
        ax.bar(x - w/2, accs, w, label="Test Accuracy", color="#3498db")
        ax.bar(x + w/2, cvs, w, label="CV Ortalama", color="#e74c3c")
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=15, ha="right")
        ax.set_ylabel("Accuracy")
        ax.set_title("ML Model Performans Karsilastirmasi")
        ax.legend()
        ax.set_ylim(0, 1.1)
        path = os.path.join(output_dir, "model_comparison.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved["model_comparison"] = path

    # 6. Correlation heatmap
    if stat_results and "correlation_matrix" in stat_results:
        corr = stat_results["correlation_matrix"]
        fig, ax = plt.subplots(figsize=(8, 7))
        q_labels_short = [f"S{i+1}" for i in range(len(corr))]
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r",
                    xticklabels=q_labels_short, yticklabels=q_labels_short,
                    vmin=-1, vmax=1, ax=ax)
        ax.set_title("Soru Korelasyon Matrisi")
        path = os.path.join(output_dir, "correlation_heatmap.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved["correlation_heatmap"] = path

    return saved


def fig_to_html(fig):
    """Plotly figuru HTML stringine donusturur."""
    return fig.to_html(full_html=False, include_plotlyjs=False)
