"""
Proje ayarlari ve PHQ-9 sabitleri.
"""
import os

# Proje dizinleri
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
DASHBOARD_DIR = os.path.join(OUTPUT_DIR, "dashboard")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

# Google API ayarlari
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token.json")
FORM_CONFIG_FILE = os.path.join(CONFIG_DIR, "form_config.json")
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Anket Soru metinleri (15 soru - genisletilmis depresyon taramasi)
PHQ9_QUESTIONS = [
    "Bir şeyler yapmaya karşı ilgi, heyecan veya motivasyon kaybı yaşama, bir anda vazgeçme",
    "Kendini çökmüş, karamsar veya umutsuz hissetme",
    "Uykuya dalmada zorluk, gece sık sık uyanma veya aşırı uyuma",
    "Sürekli yorgunluk, enerjisizlik veya tükenmişlik hissi",
    "İştahsızlık, aşırı yeme veya duygusal açlıkla beslenme",
    "Kendini değersiz, başarısız veya yetersiz hissetme",
    "Ders, iş veya günlük işlerde odaklanmada ciddi zorluk yaşama ve erteleme",
    "Sosyal medyada başkalarıyla kendini kıyaslayıp kötü hissetme",
    "Arkadaşlarla görüşmekten, dışarı çıkıp sosyalleşmekten veya aileyle vakit geçirmekten kaçınma",
    "Gelecekle ilgili belirsizlik, kaygı veya 'ne olacak' korkusu yaşama",
    "Kendini yalnız hissetme veya kimsenin seni anlamadığını düşünme",
    "Açıklanamayan bas ağrıları, aniden mide bulantıları, nefes sıkışması gibi fiziksel belirtiler",
    "Daha once zevk alınan hobilerden, aktivitelerden veya ilgi alanlarından soğuma veya uzaklaşma",
    "Keşke yaşamasam, hayat bitse de kurtulsam düşüncesi veya kendine zarar verme düşünceleri",
    "Yaşadığın duyguları başkalarıyla paylaşamamak veya içine kapanma",
]

# PHQ-9 Yanit secenekleri
PHQ9_OPTIONS = [
    "Son iki haftadır hiç (0)",
    "Son iki haftadır bir kaç gün (1-4)",
    "Son iki haftadır çoğu gün (5-9)",
    "Son iki haftadır hemen hemen her gün (9-14)",
]

# Depresyon siddet seviyeleri (15 soru, max skor 45)
SEVERITY_LEVELS = {
    "Minimal": {"range": (0, 7), "risk_percent": "0-15%", "color": "#2ecc71"},
    "Hafif": {"range": (8, 15), "risk_percent": "20-40%", "color": "#f39c12"},
    "Orta": {"range": (16, 23), "risk_percent": "40-60%", "color": "#e67e22"},
    "Orta-Siddetli": {"range": (24, 33), "risk_percent": "60-80%", "color": "#e74c3c"},
    "Siddetli": {"range": (34, 45), "risk_percent": "80-100%", "color": "#c0392b"},
}

# Maksimum skor (15 soru x 3 puan)
MAX_SCORE = 45

# Kritik soru indeksi (0-based) - kendine zarar verme sorusu
CRITICAL_QUESTION_INDEX = 13

# Demografik bilgiler
AGE_RANGES = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
GENDER_OPTIONS = ["Erkek", "Kadin", "Belirtmek istemiyorum"]

# ML ayarlari
RANDOM_STATE = 42
N_CLUSTERS_DEFAULT = 3
CV_FOLDS = 5
TEST_SIZE = 0.3

# Demo veri ayarlari
DEMO_SAMPLE_SIZE = 30
