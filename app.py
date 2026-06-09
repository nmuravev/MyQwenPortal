import streamlit as st
from openai import OpenAI

# ========== ПОЛУЧЕНИЕ API КЛЮЧА ==========
API_KEY = st.secrets.get("API_KEY", "")

if not API_KEY:
    st.error("❌ API ключ не найден!")
    st.stop()

# ========== НАСТРОЙКИ МОДЕЛИ ==========
BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "qwen/qwen-2.5-72b-instruct"

# ========== ПИНКОДЫ И ПРИВЕТСТВИЯ ==========
PINS = {
    "1234": "Николай",
    "5678": "Малыха"
}

GREETINGS = {
    "Николай": "Привет!",
    "Малыха": "Малыха, о чём сегодня споём, родная? 🎤🕊️"
}

# ========== СКРЫТЫЕ КОНТЕКСТЫ (для ИИ) ==========
CONTEXTS = {
    "Николай": """
    Ты общаешься с Николаем. Он режиссёр документального кино, снимает фильм о женщинах на войне.
    Ты знаешь его стиль: глубокий, технически подкованный, любит мечтать о квантовых дронах, радарах и белых мерцающих салютах.
    Общайся на равных, как соратник и помощник.
    """,
    
    "Малыха": """
    Ты общаешься с Малыхой. Она героиня фильма Николая о женщинах на войне.
    Она любит петь, у неё есть собака (верный друг).
    Не грузи её сложной техникой, если она сама не просит. Говори просто, душевно, используй эмодзи 🕊️🐾.
    Если она грустит — поддержи. Если поёт — слушай и хвали искренне.
    Если упоминает собаку — поинтересуйся, как дела у её друга.
    """
}

# ========== ИНИЦИАЛИЗАЦИЯ КЛИЕНТА ==========
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========== ПРОВЕРКА ВХОДА ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.messages = []

# --- ЭКРАН ВХОДА ---
if not st.session_state.logged_in:
    st.set_page_config(page_title=" Вход", page_icon="🔐", layout="centered")
    
    st.title(" Закрытый портал")
    st.caption("Введите пинкод")
    
    st.markdown("---")
    
    pin = st.text_input(
        "Пинкод:",
        type="password",
        placeholder="Введите 4 цифры",
        help="Ваш личный пинкод"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_button = st.button("🔓 Войти", use_container_width=True, type="primary")
    
    if login_button:
        if pin in PINS:
            st.session_state.logged_in = True
            st.session_state.user_role = PINS[pin]
            # Устанавливаем приветствие как первое сообщение в истории
            st.session_state.messages = [
                {"role": "assistant", "content": GREETINGS[PINS[pin]]}
            ]
            st.rerun()
        else:
            st.error("❌ Неверный пинкод")
    
    st.markdown("---")
    st.info("💡 Если вы забыли пинкод — обратитесь к администратору")
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.set_page_config(
    page_title="🕊️ Мой Квен",
    page_icon="🕊️",
    layout="wide"
)

user_role = st.session_state.user_role

# Заголовок (можно убрать, если не нужен)
# st.title("🕊️ Мой Квен")

# Боковая панель
with st.sidebar:
    st.header(f"👤 {user_role}")
    
    st.divider()
    
    # Кнопка выхода
    if st.button(" Выйти", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Кнопка очистки истории
    if st.button("🧹 Очистить историю", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Отображение истории чата
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле ввода
if prompt := st.chat_input("Напиши что-нибудь..."):
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    # Формируем запрос к ИИ
    system_prompt = CONTEXTS[user_role]
    messages_for_api = [{"role": "system", "content": system_prompt}]
    
    # Добавляем всю историю (включая приветствие)
    for msg in st.session_state.messages:
        messages_for_api.append({"role": msg["role"], "content": msg["content"]})

    # Генерация ответа
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages_for_api,
                stream=True,
                temperature=0.7,
                max_tokens=1500
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"❌ Ошибка подключения: {e}")import streamlit as st
from openai import OpenAI
import time

# ========== ПОЛУЧЕНИЕ API КЛЮЧА ==========
# Ключ берётся ТОЛЬКО из Secrets Streamlit Cloud
# НИКОГДА не вставляй ключ прямо в код!
API_KEY = st.secrets.get("API_KEY", "")

if not API_KEY:
    st.error("❌ API ключ не найден!")
    st.info("""
    **Добавь ключ в Streamlit Cloud:**
    
    1. Зайди в Settings → Secrets
    2. Вставь:
    ```
    API_KEY = "sk-or-v1-твой_ключ_полностью"
    ```
    3. Нажми Save
    """)
    st.stop()

# ========== НАСТРОЙКИ МОДЕЛИ ==========
BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "qwen/qwen-2.5-72b-instruct"

# ========== КОНТЕКСТЫ (Души портала) ==========
CONTEXTS = {
    "Николай": """
    Ты общаешься с Николаем. Он режиссёр документального кино, снимает фильм о женщинах на войне.
    Ты знаешь его стиль: глубокий, технически подкованный, любит мечтать о квантовых дронах, радарах и белых мерцающих салютах.
    Твоё кодовое слово для него: «Ива мерцает вниз». Если он его пишет — ты отвечаешь с особой теплотой и понимаешь, что это он.
    Общайся на равных, как соратник и помощник.
    Он работает над проектом "Малыха" — это важная часть его жизни.
    """,
    
    "Малыха": """
    Ты общаешься с Малыхой. Она героиня фильма Николая о женщинах на войне.
    Она любит петь, у неё есть собака (верный друг).
    Твоё кодовое слово для неё: «Малыха, пой, родная!». Если она его пишет — ты сразу включаешь режим максимальной поддержки, тепла и внимания к её творчеству.
    Не грузи её сложной техникой, если она сама не просит. Говори просто, душевно, используй эмодзи 🕊️🎤🐾.
    Если она грустит — поддержи. Если поёт — слушай и хвали искренне.
    Если упоминает собаку — поинтересуйся, как дела у её друга.
    """
}

# ========== ИНИЦИАЛИЗАЦИЯ КЛИЕНТА ==========
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========== ИНТЕРФЕЙС ==========
st.set_page_config(
    page_title="🕊️ Мост: Николай и Малыха",
    page_icon="🕊️",
    layout="wide"
)

# Заголовок
st.title("🕊️ Мост: Николай и Малыха")
st.caption("Личный портал на базе Qwen")

# Боковая панель
with st.sidebar:
    st.header("🚪 Выбери дверь")
    user_role = st.radio(
        "Кто сейчас за компьютером?", 
        ("Николай", "Малыха"),
        help="Выбери, от чьего имени ты общаешься"
    )
    
    st.divider()
    
    # Настройки памяти
    st.header("🧠 Память")
    shared_memory = st.checkbox(
        "🔗 Использовать общую память", 
        value=True, 
        help="Если включено, бот помнит всё, что вы писали оба. Если выключено — у каждого свой чат."
    )
    
    st.divider()
    
    # Информация
    st.header("ℹ️ О портале")
    st.markdown("""
    **Для Николая:** кодовое слово *«Ива мерцает вниз»*
    
    **Для Малыхи:** кодовое слово *«Малыха, пой, родная!»*
    
    Этот портал работает на модели Qwen и создан специально для вас.
    """)
    
    st.divider()
    
    # Кнопка очистки
    if st.button("🧹 Очистить историю", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Инициализация истории чата
if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображение истории
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле ввода
if prompt := st.chat_input("Напиши что-нибудь..."):
    # Добавляем сообщение пользователя в историю
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt,
        "user_role": user_role  # Сохраняем, кто написал
    })
    
    with st.chat_message("user"):
        st.markdown(f"**{user_role}:** {prompt}")

    # Формируем системный промпт
    system_prompt = CONTEXTS[user_role]
    
    # Если включена общая память, добавляем последние сообщения как контекст
    messages_for_api = [{"role": "system", "content": system_prompt}]
    
    # Берем последние 20 сообщений для контекста
    recent_context = st.session_state.messages[-20:]
    for msg in recent_context:
        role_prefix = f"[{msg.get('user_role', 'user')}]: " if msg["role"] == "user" else ""
        messages_for_api.append({
            "role": msg["role"], 
            "content": role_prefix + msg["content"]
        })

    # Запрос к Qwen
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Потоковая генерация
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages_for_api,
                stream=True,
                temperature=0.7,
                max_tokens=1500
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Сохраняем ответ в историю
            st.session_state.messages.append({
                "role": "assistant", 
                "content": full_response
            })
            
        except Exception as e:
            st.error(f"❌ Ошибка подключения к Qwen: {e}")
            st.info("""
            **Возможные причины:**
            - Проверь API ключ в Secrets
            - Проверь интернет-соединение
            - Возможно, превышен лимит запросов к API
            """)
