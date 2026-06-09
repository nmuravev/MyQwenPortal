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
    "Малыха": "Малыха, о чём сегодня споём, родная? 🎤️"
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

def save_message_to_db(role, content, author, has_image=False, has_video=False, has_audio=False, image_base64=None, audio_transcription=None):
    doc = {
        "role": role,
        "content": content,
        "author": author,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "has_image": has_image,
        "has_video": has_video,
        "has_audio": has_audio,
    }
    
    if image_base64:
        doc["image_base64"] = image_base64
    if audio_transcription:
        doc["audio_transcription"] = audio_transcription
    
    db.collection("messages").add(doc)

def get_messages_from_db(limit=50):
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

# ========== ЭКРАН ВХОДА (БЕЗ КАРТИНКИ) ==========
if not st.session_state.logged_in:
    st.set_page_config(page_title="Вход", page_icon="🔐", layout="centered")
    
    st.title("🔐 Чат для друзей")
    st.caption("Введите пинкод для входа")
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

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
st.set_page_config(page_title="Чат для друзей", page_icon="💬", layout="wide")
user_role = st.session_state.user_role
is_admin = (user_role == "Николай")

# Боковая панель
with st.sidebar:
    st.header(f"👤 {user_role}")
    if is_admin:
        st.markdown("🔑 **Администратор**")
    
    st.divider()
    
    st.markdown("### 📤 Загрузка медиа")
    st.info("🖼️ Фото, 🎥 Видео, 🎤 Аудио")
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
        # Показываем изображения если есть
        if msg.get("has_image") and msg.get("image_base64"):
            try:
                img_data = base64.b64decode(msg["image_base64"])
                st.image(img_data, width='stretch')
            except:
                st.caption("🖼️ Изображение")
        
        # Показываем видео если есть
        if msg.get("has_video"):
            st.caption("🎥 Видео загружено")
        
        # Показываем аудио если есть
        if msg.get("has_audio"):
            st.caption("🎤 Аудио загружено")
            if msg.get("audio_transcription"):
                st.caption(f" {msg['audio_transcription']}")
        
        # Показываем текст
        if msg.get("content"):
            if msg["role"] == "user":
                st.caption(f"✍️ {msg['author']}")
            st.markdown(msg["content"])

# Поле ввода
text_input = st.chat_input("Напиши что-нибудь...")

# Загрузка файлов
uploaded_files = st.sidebar.file_uploader(
    "📎 Прикрепить файлы",
    type=['jpg', 'jpeg', 'png', 'mp4', 'mov', 'mp3', 'wav', 'm4a'],
    accept_multiple_files=True
)

# Обработка отправки
def process_and_respond(user_text, has_image=False, has_video=False, has_audio=False, image_base64=None, audio_transcription=None):
    save_message_to_db("user", user_text, user_role, has_image, has_video, has_audio, image_base64, audio_transcription)
    
    system_prompt = CONTEXTS[user_role]
    recent_msgs = get_messages_from_db(limit=15)
    messages_for_api = [{"role": "system", "content": system_prompt}]
    
    for m in recent_msgs:
        content = m.get("content", "")
        
        if m.get("has_image"):
            content += " [Пользователь загрузил изображение]"
        if m.get("has_video"):
            content += " [Пользователь загрузил видео]"
        if m.get("has_audio") and m.get("audio_transcription"):
            content += f" [Аудио: {m.get('audio_transcription', '')}]"
        
        messages_for_api.append({"role": m["role"], "content": content})

    model_to_use = VISION_MODEL if has_image else TEXT_MODEL
    
    try:
        stream = client_qwen.chat.completions.create(
            model=model_to_use, messages=messages_for_api, stream=True, temperature=0.7, max_tokens=2000
        )
        full_response = ""
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        
        save_message_to_db("assistant", full_response, "ИИ")
        
    except Exception as e:
        save_message_to_db("assistant", f"❌ Ошибка ИИ: {e}", "ИИ")

# Если загружены файлы
if uploaded_files:
    full_text = ""
    has_image = False
    has_video = False
    has_audio = False
    image_b64 = None
    audio_trans = None
    
    for uploaded_file in uploaded_files:
        file_type = uploaded_file.type.split('/')[0]
        file_ext = Path(uploaded_file.name).suffix.lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        if file_type == 'image':
            image_b64 = encode_image(tmp_path)
            full_text += f"[Фото: {uploaded_file.name}] "
            has_image = True
        elif file_type == 'video':
            full_text += f"[Видео: {uploaded_file.name}] "
            has_video = True
        elif file_type == 'audio':
            with st.spinner(" Расшифровываю аудио..."):
                audio_trans = transcribe_audio(uploaded_file)
            full_text += f"[Аудио: {uploaded_file.name}]\n{audio_trans} "
            has_audio = True
        
        os.unlink(tmp_path)
    
    process_and_respond(full_text.strip(), has_image, has_video, has_audio, image_b64, audio_trans)
    st.rerun()

# Если введен текст
if text_input:
    process_and_respond(text_input)
    st.rerun()

# Автообновление для "живого" чата
time.sleep(5)
st.rerun()
