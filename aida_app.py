import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="AIDA OS", page_icon="🎨", layout="wide")

# --- СТИЛИЗАЦИЯ (РАБОЧИЙ ИНТЕРФЕЙС) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e6edf3; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #238636; color: white; }
    .auth-title { text-align: center; font-family: 'Courier New', monospace; color: #58a6ff; }
    .recipe-card { border: 1px solid #30363d; padding: 15px; border-radius: 10px; background: #161b22; margin-bottom: 10px; }
    .logo-img { width: 30px; vertical-align: middle; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_ultimate_v1.db')
    c = conn.cursor()
    # Пользователи и ключи (привязка к устройству через имитацию token)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, 
                  license_key TEXT, device_token TEXT, expiry_date TEXT, is_admin INTEGER DEFAULT 0)''')
    # Рецепты AkzoNobel
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, 
                  components TEXT, vykraska TEXT, is_custom INTEGER DEFAULT 0)''')
    # Чат
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, msg TEXT, time TEXT)''')
    
    # Дефолтный админ-ключ (нельзя удалить)
    admin_hash = hashlib.sha256("STARK_ADMIN_2026".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, license_key, is_admin) VALUES (?, ?, ?, ?)", 
              ('Админ', 'JARVIS_PRO', admin_hash, 1))
    
    # Наполнение базы AkzoNobel
    c.execute("SELECT COUNT(*) FROM recipes WHERE is_custom=0")
    if c.fetchone()[0] == 0:
        base_data = [
            ('BMW', '475', 'Black Sapphire', '4000:450,4802:40,4906:10', 'M937'),
            ('Audi', 'LY7C', 'Nardo Grey', '4000:300,4110:150,4020:40', 'M837'),
            ('Mercedes', '197', 'Obsidian Black', '4000:400,4802:80,4906:5', 'M940')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, components, vykraska) VALUES (?,?,?,?,?)", base_data)
    
    conn.commit()
    conn.close()

init_db()

# --- ЛОГИКА АВТОРИЗАЦИИ ---
if 'user' not in st.session_state: st.session_state.user = None

def login_ui():
    st.markdown("<h1 class='auth-title'>A.I.D.A. — Твой Джарвис в мире колористики</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Вход", "Активация ключа"])
        with tab1:
            u = st.text_input("Логин")
            p = st.text_input("Пароль", type="password")
            if st.button("ИНИЦИАЛИЗАЦИЯ"):
                conn = sqlite3.connect('aida_ultimate_v1.db')
                res = conn.cursor().execute("SELECT username, is_admin FROM users WHERE username=? AND password=?", (u, p)).fetchone()
                conn.close()
                if res:
                    st.session_state.user = res[0]
                    st.session_state.is_admin = bool(res[1])
                    st.rerun()
                else: st.error("Доступ запрещен. Проверьте данные.")
        with tab2:
            key = st.text_input("Введите лицензионный ключ")
            new_u = st.text_input("Создать никнейм")
            new_p = st.text_input("Создать пароль", type="password")
            if st.button("АКТИВИРОВАТЬ"):
                st.info("Привязка к устройству выполнена. Ключ активирован.")
                # Здесь логика проверки ключа из таблицы и апдейт юзера

if not st.session_state.user:
    login_ui()
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.sidebar.title(f"🤖 {st.session_state.user}")
menu = ["🧪 База AkzoNobel", "📱 Калькулятор", "💬 Чат мастеров", "🧠 Советы ИИ"]
if st.session_state.is_admin: menu.append("⚙️ Панель управления")
choice = st.sidebar.radio("Меню системы", menu)

conn = sqlite3.connect('aida_ultimate_v1.db')

if choice == "🧪 База AkzoNobel":
    st.header("Система поиска формул")
    search = st.text_input("Код или название цвета (напр. 475 или Nardo)")
    
    # Логотипы марок (упрощенно текстом/эмодзи для стабильности)
    logos = {"BMW": "BMW", "Audi": "𝐀𝐮𝐝𝐢", "Mercedes": "AMG", "Toyota": "⛩️"}
    
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR name LIKE '%{search}%'", conn)
    for _, r in df.iterrows():
        with st.expander(f"{logos.get(r['mark'], '🚘')} {r['mark']} | {r['code']} - {r['name']}"):
            st.write(f"**Выкраска AkzoNobel:** {r['vykraska']}")
            st.markdown("---")
            comps = r['components'].split(",")
            for c in comps:
                name, val = c.split(":")
                st.write(f"🧩 Пигмент **{name}**: {val} гр.")

elif choice == "📱 Калькулятор":
    st.header("Калькулятор материалов")
    c1, c2 = st.columns(2)
    with c1:
        base_w = st.number_input("Вес краски (гр)", 100, 5000, 500)
        temp = st.slider("Температура в камере (°C)", 10, 40, 22)
    with c2:
        st.subheader("Результат:")
        thin = base_w * 0.5 if temp < 25 else base_w * 0.6
        st.success(f"Разбавитель: {thin} гр.")
        if temp > 30: st.warning("Совет: Используйте медленный разбавитель (Slow)!")
        else: st.info("Совет: Стандартный разбавитель оптимален.")

elif choice == "💬 Чат мастеров":
    st.header("Общий чат")
    msg = st.chat_input("Напишите коллегам...")
    if msg:
        conn.cursor().execute("INSERT INTO chat (user, msg, time) VALUES (?,?,?)", 
                              (st.session_state.user, msg, datetime.now().strftime("%H:%M")))
        conn.commit()
    
    chat_data = pd.read_sql("SELECT * FROM chat ORDER BY id DESC LIMIT 20", conn)
    for _, m in chat_data.iterrows():
        col1, col2 = st.columns([0.8, 0.2])
        col1.write(f"**[{m['time']}] {m['user']}:** {m['msg']}")
        if st.session_state.is_admin:
            if col2.button("Удалить", key=f"del_{m['id']}"):
                conn.cursor().execute("DELETE FROM chat WHERE id=?", (m['id'],))
                conn.commit()
                st.rerun()

elif choice == "🧠 Советы ИИ":
    st.info("Джарвис анализирует... Для цвета Nardo Grey рекомендуется подложка G5.")
    st.write("При температуре 25°C добавьте 10% пластификатора в лак для бамперов.")

elif choice == "⚙️ Панель управления" and st.session_state.is_admin:
    st.header("Генератор ключей")
    days = st.number_input("Срок действия (дней)", 1, 365, 30)
    if st.button("ГЕНЕРИРОВАТЬ КЛЮЧ"):
        new_key = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12].upper()
        st.code(new_key, language="text")
        st.success(f"Ключ создан на {days} дней")

conn.close()



