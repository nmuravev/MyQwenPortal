import streamlit as st
from openai import OpenAI
import base64
import tempfile
import os
from pathlib import Path
import json
import firebase_admin
from firebase_admin import credentials, firestore
import time

# ========== ИНИЦИАЛИЗАЦИЯ FIREBASE ==========
@st.cache_resource
def init_firebase():
    cred_dict = json.loads(st.secrets.get("FIREBASE_CREDENTIALS", "{}"))
    if not cred_dict:
        st.error("❌ Ошибка: FIREBASE_CREDENTIALS не найдены в Secrets!")
        st.stop()
    cred = credentials.Certificate(cred_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ========== ПОЛУЧЕНИЕ API КЛЮЧЕЙ ==========
API_KEY = st.secrets.get("API_KEY", "")
WHISPER_API_KEY = st.secrets.get("WHISPER_API_KEY", API_KEY)

if not API_KEY:
    st.error("❌ API ключ OpenRouter не найден!")
    st.stop()

# ========== НАСТРОЙКИ МОДЕЛЕЙ ==========
BASE_URL = "https://openrouter.ai/api/v1"
VISION_MODEL = "qwen/qwen-2.5-vl-72b-instruct"
TEXT_MODEL = "qwen/qwen-2.5-72b-instruct"
WHISPER_MODEL = "whisper-1"

# ========== ПИНКОДЫ И ПРИВЕТСТВИЯ ==========
PINS = json.loads(st.secrets.get("PINS", "{}"))

GREETINGS = {
    "Николай": "Привет! На связи.",
    "Малыха": "Малыха, о чём сегодня споём, родная? 🎤🕊️"
}

# ========== СКРЫТЫЕ КОНТЕКСТЫ ==========
CONTEXTS = {
    "Николай": """
    Ты общаешься с Николаем и Малыхой в общем чате. 
    Николай — режиссёр документального кино, снимает фильм о женщинах на войне.
    Малыха — героиня фильма, любит петь, у неё есть собака.
    Отвечай тепло, поддерживай обоих. Если Малыха поёт — хвали. Если Николай говорит о технике — отвечай по делу.
    """,
    "Малыха": """
    Ты общаешься с Николаем и Малыхой в общем чате.
    Малыха любит петь, у неё есть собака. Николай — режиссёр.
    Говори просто, душевно, используй эмодзи 🕊️🎤🐾.
    """
}

# ========== КЛИЕНТЫ ==========
client_qwen = OpenAI(api_key=API_KEY, base_url=BASE_URL)
client_whisper = OpenAI(api_key=WHISPER_API_KEY)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def transcribe_audio(audio_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_file.read())
            tmp_path = tmp_file.name
        with open(tmp_path, "rb") as audio_fd:
            transcription = client_whisper.audio.transcriptions.create(model=WHISPER_MODEL, file=audio_fd, language="ru")
        os.unlink(tmp_path)
        return transcription.text
    except Exception as e:
        return f"❌ Ошибка расшифровки: {str(e)}"

def save_message_to_db(role, content, author, attachments=None):
    """Сохраняет сообщение в Firestore"""
    doc = {
        "role": role,
        "content": content,
        "author": author,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "attachments": attachments or []
    }
    db.collection("messages").add(doc)

def get_messages_from_db(limit=50):
    """Читает последние сообщения из Firestore"""
    docs = db.collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
    messages = []
    for doc in docs:
        data = doc.to_dict()
        messages.append(data)
    return list(reversed(messages))

# ========== ПРОВЕРКА ВХОДА ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# --- ЭКРАН ВХОДА ---
if not st.session_state.logged_in:
    st.set_page_config(page_title="Вход", page_icon="🔐", layout="centered")
    st.image("https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80", use_container_width=True)
    st.title("Чат для друзей")
    st.caption("Введите пинкод")
    st.markdown("---")
    
    pin = st.text_input("Пинкод:", type="password", placeholder="Введите 4 цифры")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_button = st.button("🔓 Войти", use_container_width=True, type="primary")
    
    if login_button:
        if pin in PINS:
            st.session_state.logged_in = True
            st.session_state.user_role = PINS[pin]
            st.rerun()
        else:
            st.error("❌ Неверный пинкод")
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.set_page_config(page_title="Чат для друзей", page_icon="💬", layout="wide")
user_role = st.session_state.user_role
is_admin = (user_role == "Николай")

# Боковая панель
with st.sidebar:
    st.header(f"👤 {user_role}")
    if is_admin: st.markdown("🔑 **Администратор**")
    st.image("https://cdn-icons-png.flaticon.com/512/2645/2645827.png", width=100)
    st.divider()
    st.markdown("### 📤 Загрузка медиа")
    st.info("🖼️ Фото, 🎥 Видео,  Аудио")
    st.divider()
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()
    st.divider()
    if is_admin and st.button("🧹 Очистить всю историю", use_container_width=True):
        docs = db.collection("messages").stream()
        for doc in docs:
            doc.reference.delete()
        st.rerun()

# Чтение сообщений из базы данных
messages = get_messages_from_db()

# Отображение истории
for msg in messages:
    with st.chat_message(msg["role"]):
        if msg.get("attachments"):
            for att in msg["attachments"]:
                if att["type"] == "image": st.image(att["data"], use_container_width=True)
                elif att["type"] == "video": st.video(att["data"])
                elif att["type"] == "audio": 
                    st.audio(att["data"])
                    if "transcription" in att: st.caption(f"🎤 {att['transcription']}")
        
        if msg.get("content"):
            if msg["role"] == "user":
                st.caption(f"
