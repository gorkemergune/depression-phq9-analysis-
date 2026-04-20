"""
Google Forms API ile anket yanitlarini cekme ve demo veri uretme modulu.
"""
import sys
import os
import re
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import (
    AGE_RANGES, GENDER_OPTIONS, PHQ9_QUESTIONS, DEMO_SAMPLE_SIZE, RANDOM_STATE,
    CRITICAL_QUESTION_INDEX,
)


def fetch_responses_from_forms_api(form_id=None):
    """
    Google Forms API uzerinden yanitlari ceker.
    form_id verilmezse form_config.json'dan okur.
    """
    from googleapiclient.discovery import build
    from src.google_forms.form_creator import get_google_credentials, load_form_config

    # Form config'i yukle
    config = load_form_config()
    if form_id is None:
        if config is None:
            raise FileNotFoundError(
                "Form config bulunamadi. Once anket olusturun:\n"
                "  python3 main.py --anket-olustur"
            )
        form_id = config["form_id"]

    question_mapping = config.get("question_mapping", {}) if config else {}

    creds = get_google_credentials()
    service = build("forms", "v1", credentials=creds)

    # Yanitlari cek
    result = service.forms().responses().list(formId=form_id).execute()
    responses = result.get("responses", [])

    if not responses:
        print("  Henuz yanit bulunamadi.")
        return pd.DataFrame()

    print(f"  {len(responses)} yanit bulundu.")

    # DataFrame'e donustur
    rows = []
    for i, resp in enumerate(responses):
        row = {
            "participant_id": f"P{str(i+1).zfill(3)}",
            "timestamp": resp.get("createTime", ""),
            "participant_name": "",
            "age_range": "",
            "gender": "",
        }
        n_questions = len(PHQ9_QUESTIONS)
        for q in range(1, n_questions + 1):
            row[f"q{q}"] = 0

        answers = resp.get("answers", {})
        for qid, answer_data in answers.items():
            text_answers = answer_data.get("textAnswers", {}).get("answers", [])
            if not text_answers:
                continue
            value = text_answers[0].get("value", "")

            if qid in question_mapping:
                col = question_mapping[qid]["column"]
                if col.startswith("q") and col[1:].isdigit():
                    row[col] = _extract_score_from_option(value)
                else:
                    row[col] = value
            else:
                row = _guess_column(row, value)

        # Katilimci adi varsa participant_id olarak kullan
        if row.get("participant_name"):
            row["participant_id"] = row["participant_name"]

        rows.append(row)

    df = pd.DataFrame(rows)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    print(f"  Veri DataFrame'e donusturuldu ({len(df)} satir).")
    return df


def _guess_column(row, value):
    """Mapping olmadigi durumda degeri tahmin ederek dogru sutuna yazar."""
    value_str = str(value).strip()
    n_questions = len(PHQ9_QUESTIONS)
    if value_str in AGE_RANGES:
        row["age_range"] = value_str
    elif value_str in GENDER_OPTIONS:
        row["gender"] = value_str
    elif re.search(r"\(\d\)", value_str):
        score = _extract_score_from_option(value_str)
        for q in range(1, n_questions + 1):
            if row[f"q{q}"] == 0:
                row[f"q{q}"] = score
                break
    else:
        if not row.get("participant_name") and len(value_str) > 0:
            row["participant_name"] = value_str
            row["participant_id"] = value_str
    return row


def fetch_responses_from_sheets(spreadsheet_id):
    """Google Sheets'ten anket yanitlarini ceker (alternatif yontem)."""
    from googleapiclient.discovery import build
    from src.google_forms.form_creator import get_google_credentials

    creds = get_google_credentials()
    service = build("sheets", "v4", credentials=creds)

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range="A:M")
        .execute()
    )
    values = result.get("values", [])

    if not values:
        print("Henuz yanit bulunamadi.")
        return pd.DataFrame()

    headers = values[0]
    data = values[1:]
    df = pd.DataFrame(data, columns=headers)
    df = _clean_sheet_data(df)
    return df


def _clean_sheet_data(df):
    """Sheets'ten gelen ham veriyi temizler."""
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if "zaman" in col_lower or "timestamp" in col_lower:
            column_mapping[col] = "timestamp"
        elif "yas" in col_lower or "age" in col_lower:
            column_mapping[col] = "age_range"
        elif "cinsiyet" in col_lower or "gender" in col_lower:
            column_mapping[col] = "gender"
        elif "adiniz" in col_lower or "isim" in col_lower or "takma" in col_lower:
            column_mapping[col] = "participant_name"

    df = df.rename(columns=column_mapping)
    phq_cols = [col for col in df.columns if col.lower().startswith("soru")]
    for col in phq_cols:
        df[col] = df[col].apply(_extract_score_from_option)
    return df


def _extract_score_from_option(value):
    """Yanit metninden sayisal skoru cikarir. Sik metnini PHQ9_OPTIONS listesindeki siraya gore esler."""
    from config.settings import PHQ9_OPTIONS

    if pd.isna(value):
        return 0
    value = str(value).strip()
    if value.isdigit():
        return int(value)

    # Once tam metin eslesmesi dene (sik metni = PHQ9_OPTIONS'daki sira = puan)
    value_lower = value.lower()
    for i, opt in enumerate(PHQ9_OPTIONS):
        if value_lower == opt.lower() or value_lower in opt.lower() or opt.lower() in value_lower:
            return i

    # Tek rakamli parantez formatini dene: (0), (1), (2), (3)
    match = re.search(r"\((\d)\)", value)
    if match:
        return int(match.group(1))

    # Anahtar kelime eslesmesi (fallback)
    mapping = {"hic": 0, "hiç": 0, "birkac": 1, "bir kaç": 1, "birkaç": 1,
               "cogu": 2, "çoğu": 2, "yarisi": 2, "yarısı": 2,
               "hemen": 3, "her gun": 3, "her gün": 3}
    for key, score in mapping.items():
        if key in value_lower:
            return score
    return 0


def generate_demo_data(n_samples=DEMO_SAMPLE_SIZE):
    """Test amacli sentetik PHQ-9 yanit verisi uretir."""
    np.random.seed(RANDOM_STATE)
    random.seed(RANDOM_STATE)

    isimler = [
        "Ahmet", "Mehmet", "Ayse", "Fatma", "Ali", "Zeynep", "Mustafa", "Elif",
        "Hasan", "Merve", "Emre", "Selin", "Burak", "Esra", "Caner", "Derya",
        "Fikret", "Gamze", "Halil", "Irem", "Kemal", "Leyla", "Murat", "Nur",
        "Ozan", "Pinar", "Recep", "Seda", "Tolga", "Ulas",
    ]

    data = {
        "participant_id": isimler[:n_samples],
        "participant_name": isimler[:n_samples],
        "timestamp": [
            (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S")
            for _ in range(n_samples)
        ],
        "age_range": [random.choice(AGE_RANGES) for _ in range(n_samples)],
        "gender": random.choices(
            GENDER_OPTIONS[:2],
            weights=[0.45, 0.55],
            k=n_samples,
        ),
    }

    profiles = np.random.choice(
        ["minimal", "hafif", "orta", "siddetli"],
        size=n_samples,
        p=[0.40, 0.30, 0.20, 0.10],
    )

    score_ranges = {
        "minimal": (0, 1), "hafif": (0, 2),
        "orta": (1, 3), "siddetli": (2, 3),
    }

    n_questions = len(PHQ9_QUESTIONS)
    for q_idx in range(n_questions):
        col_name = f"q{q_idx + 1}"
        scores = []
        for profile in profiles:
            low, high = score_ranges[profile]
            score = np.random.randint(low, high + 1)
            if q_idx == CRITICAL_QUESTION_INDEX:
                score = max(0, score - 1)
            scores.append(score)
        data[col_name] = scores

    df = pd.DataFrame(data)

    age_multiplier = {
        "18-24": 1.0, "25-34": 1.0, "35-44": 1.1,
        "45-54": 1.15, "55-64": 1.2, "65+": 1.1,
    }
    for idx, row in df.iterrows():
        mult = age_multiplier.get(row["age_range"], 1.0)
        if mult > 1.0:
            for q in range(1, n_questions + 1):
                col = f"q{q}"
                new_val = min(3, int(row[col] * mult))
                df.at[idx, col] = new_val

    print(f"  {n_samples} kisilik demo veri seti olusturuldu.")
    return df


def get_question_columns(df):
    """DataFrame'deki PHQ-9 soru sutunlarini dondurur."""
    q_cols = [col for col in df.columns if col.startswith("q") and col[1:].isdigit()]
    if not q_cols:
        q_cols = [col for col in df.columns if col.lower().startswith("soru")]
    return sorted(q_cols, key=lambda x: int(re.search(r"\d+", x).group()))


if __name__ == "__main__":
    df = generate_demo_data()
    print(df.head(10))
