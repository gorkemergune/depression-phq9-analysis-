"""
Google Forms'da PHQ-9 depresyon anketi olusturma modulu.
Form ID ve soru mapping'ini config/form_config.json'a kaydeder.
"""
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import (
    CREDENTIALS_FILE, TOKEN_FILE, SCOPES, FORM_CONFIG_FILE,
    PHQ9_QUESTIONS, PHQ9_OPTIONS, AGE_RANGES, GENDER_OPTIONS,
)


def get_google_credentials():
    """Google API icin OAuth2 kimlik bilgilerini al veya yenile."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"credentials.json bulunamadi: {CREDENTIALS_FILE}\n"
                    "Lutfen GOOGLE_API_SETUP.md rehberini takip edin."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def create_phq9_form():
    """
    Google Forms'da PHQ-9 anketi olusturur.
    Form ID, URL ve soru mapping'ini form_config.json'a kaydeder.
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials()
    service = build("forms", "v1", credentials=creds)

    # 1. Formu olustur
    form = {"info": {"title": "PHQ-9 Depresyon Tarama Anketi"}}
    result = service.forms().create(body=form).execute()
    form_id = result["formId"]

    # 2. Sorulari ekle
    requests = []

    # Form aciklamasi
    requests.append({
        "updateFormInfo": {
            "info": {
                "description": (
                    "Bu anket, son 2 hafta içinde aşağıdaki durumlardan ne sıklıkla "
                    "etkilendiğini değerlendirmektedir.\n\n"
                    "15 soru içermektedir. Lütfen her soru için en uygun seçeneği işaretleyin.\n"
                    "Yanıtlar GitHub üzerinden paylaşılacaktır. Bu yüzden kişisel ismini yazmak istemeyenler takma isim kullanabilirler."
                ),
            },
            "updateMask": "description",
        }
    })

    # Isim / Takma isim
    requests.append({
        "createItem": {
            "item": {
                "title": "Adınız veya Takma Adınız",
                "description": "Sonuçlarınızı size iletebilmemiz icin bir isim girin.",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False},
                    }
                },
            },
            "location": {"index": 0},
        }
    })

    # Yas
    requests.append({
        "createItem": {
            "item": {
                "title": "Yaş Aralığıınız",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [{"value": age} for age in AGE_RANGES],
                        },
                    }
                },
            },
            "location": {"index": 1},
        }
    })

    # Cinsiyet
    requests.append({
        "createItem": {
            "item": {
                "title": "Cinsiyetiniz",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [{"value": g} for g in GENDER_OPTIONS],
                        },
                    }
                },
            },
            "location": {"index": 2},
        }
    })

    # PHQ-9 sorulari (9 adet)
    for i, question_text in enumerate(PHQ9_QUESTIONS):
        requests.append({
            "createItem": {
                "item": {
                    "title": f"Soru {i + 1}: {question_text}",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in PHQ9_OPTIONS],
                            },
                        }
                    },
                },
                "location": {"index": i + 3},
            }
        })

    # Batch update
    service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests},
    ).execute()

    # 3. Form yapisini cek ve soru ID mapping olustur
    form_data = service.forms().get(formId=form_id).execute()
    question_mapping = _build_question_mapping(form_data)

    # 4. Config dosyasina kaydet
    form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    config = {
        "form_id": form_id,
        "form_url": form_url,
        "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
        "question_mapping": question_mapping,
    }
    with open(FORM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 55)
    print("  PHQ-9 ANKETI BASARIYLA OLUSTURULDU!")
    print("=" * 55)
    print()
    print(f"  Anket Linki (bunu paylasin):")
    print(f"  {form_url}")
    print()
    print(f"  Form ID: {form_id}")
    print(f"  Config kaydedildi: {FORM_CONFIG_FILE}")
    print()
    print("  Simdi bu linki katilimcilara gonderin.")
    print("  Herkes doldurduktan sonra su komutu calistirin:")
    print()
    print("  python3 main.py --sonuclar")
    print("=" * 55)

    return form_id, form_url


def _build_question_mapping(form_data):
    """Form yapisindan questionId -> sutun adi eslesmesi olusturur."""
    mapping = {}
    for item in form_data.get("items", []):
        title = item.get("title", "")
        question = item.get("questionItem", {}).get("question", {})
        qid = question.get("questionId")
        if not qid:
            continue

        title_lower = title.lower()
        if "adiniz" in title_lower or "takma" in title_lower or "isim" in title_lower:
            mapping[qid] = {"column": "participant_name", "title": title}
        elif "yas" in title_lower:
            mapping[qid] = {"column": "age_range", "title": title}
        elif "cinsiyet" in title_lower:
            mapping[qid] = {"column": "gender", "title": title}
        else:
            match = re.search(r"soru\s*(\d+)", title_lower)
            if match:
                q_num = int(match.group(1))
                mapping[qid] = {"column": f"q{q_num}", "title": title}

    return mapping


def load_form_config():
    """Kaydedilmis form config'ini yukler."""
    if not os.path.exists(FORM_CONFIG_FILE):
        return None
    with open(FORM_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    create_phq9_form()
