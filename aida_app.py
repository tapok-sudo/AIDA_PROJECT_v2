import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# --- 1. НАСТРОЙКИ И МОБИЛЬНЫЙ СТИЛЬ ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Roboto Mono', monospace; }
    /* Мобильные кнопки */
    .stButton>button { width: 100%; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #58a6ff; font-weight: bold; padding: 10px; }
    .stButton>button:active { background-color: #30363d; }
    /* Карточки и поля */
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #0d1117; color: white; border: 1px solid #30363d; border-radius: 4px; }
    div[data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 2. УПРАВЛЕНИЕ COOKIES (СЕССИЯ НА 10 ЛЕТ) ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# --- 3. ЯДРО БАЗЫ ДАННЫХ И ЛОГОВ ---
def init_db():
    conn = sqlite3.connect('aida_stable.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, components TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp DATETIME)''')
    
    # Наполнение базовыми рецептами (если пусто)
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base_recipes = [
            ('BMW', '475', '4003:496.4,4700:0.2,4656:0.1'),
            ('TOYOTA', '070', 'White:400,Pearl:25.5,Clear:100'),
            ('MAZDA', '41V', 'Red Base:300,Deep Red:100')
        ]
        c.executemany("INSERT INTO recipes (mark, code, components) VALUES (?,?,?)", base_recipes)
    conn.commit()
    conn.close()

def write_log(user, action):
    try:
        conn = sqlite3.connect('aida_stable.db')
        conn.cursor().execute("INSERT INTO logs (user, action, timestamp) VALUES (?, ?, ?)", (user, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def cleanup_logs():
    try:
        conn = sqlite3.connect('aida_stable.db')
        limit_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn.cursor().execute("DELETE FROM logs WHERE timestamp < ?", (limit_date,))
        conn.commit(); conn.execute("VACUUM"); conn.close()
    except: pass

init_db()

# --- 4. ЛОГИКА АВТОРИЗАЦИИ (БРОНЯ) ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'admin': False})

# Проверка куки при старте
saved_token = cookie_manager.get(cookie="aida_token")
if saved_token and not st.session_state['auth']:
    if saved_token == st.secrets.get("ADMIN_CODE", "ROOT_777"): # В fallback можно поставить свой код
        st.session_state.update({'auth': True, 'user': 'ROOT', 'admin': True})
    else:
        conn = sqlite3.connect('aida_stable.db')
        res = conn.cursor().execute("SELECT owner_name, is_admin FROM keys WHERE device_token = ?", (saved_token,)).fetchone()
        conn.close()
        if res:
            st.session_state.update({'auth': True, 'user': res[0], 'admin': bool(res[1])})

# Экран входа
if not st.session_state['auth']:
    st.markdown("<br><br><h2 style='text-align: center; color: #58a6ff;'>AIDA SYSTEM</h2>", unsafe_allow_html=True)
    input_key = st.text_input("КЛЮЧ ДОСТУПА", type="password", placeholder="Введите ключ")
    
    if st.button("АКТИВИРОВАТЬ"):
        admin_code = st.secrets.get("ADMIN_CODE", "ROOT_777")
        if input_key == admin_code:
            cookie_manager.set("aida_token", admin_code, expires_at=datetime.now() + timedelta(days=3650))
            st.success("ДОСТУП РАЗРЕШЕН (ROOT)")
            st.rerun()
        else:
            conn = sqlite3.connect('aida_stable.db')
            c = conn.cursor()
            res = c.execute("SELECT owner_name, device_token FROM keys WHERE license_key = ?", (input_key,)).fetchone()
            
            if res:
                owner, saved_token = res
                if not saved_token:
                    # Привязка нового устройства
                    new_device_token = str(uuid.uuid4())
                    c.execute("UPDATE keys SET device_token = ? WHERE license_key = ?", (new_device_token, input_key))
                    conn.commit()
                    cookie_manager.set("aida_token", new_device_token, expires_at=datetime.now() + timedelta(days=3650))
                    st.rerun()
                else:
                    st.error("ОШИБКА: Ключ уже привязан к другому устройству.")
            else:
                st.error("НЕДЕЙСТВИТЕЛЬНЫЙ КЛЮЧ")
            conn.close()
    st.stop()

# --- 5. ГЛАВНОЕ МЕНЮ (ДЛЯ ТЕЛЕФОНА) ---
col1, col2 = st.columns([3, 1])
col1.markdown(f"**OP:** `{st.session_state['user']}`")
if col2.button("ВЫХОД"):
    cookie_manager.delete("aida_token")
    st.session_state.clear()
    st.rerun()

menu_options = ["🧪 ЛАБОРАТОРИЯ", "💬 ЧАТ"]
if st.session_state['admin']: menu_options.append("⚙️ АДМИН-ПАНЕЛЬ")
menu = st.selectbox("НАВИГАЦИЯ:", menu_options)

st.markdown("---")

# --- РАЗДЕЛ: ЛАБОРАТОРИЯ ---
if menu == "🧪 ЛАБОРАТОРИЯ":
    search = st.text_input("ПОИСК ФОРМУЛЫ (Код или Марка):")
    if search:
        conn = sqlite3.connect('aida_stable.db')
        df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'", conn)
        conn.close()
        
        if df.empty:
            st.warning("Формула не найдена.")
        else:
            for _, r in df.iterrows():
                with st.expander(f"🔴 {r['mark']} | Код: {r['code']}"):
                    comps = [i.split(":") for i in r['components'].split(",") if ":" in i]
                    target_w = st.number_input("Общий вес (г):", 10, 5000, 500, key=f"w_{r['id']}")
                    ratio = target_w / sum([float(i[1]) for i in comps])
                    
                    for name, val in comps:
                        st.markdown(f"**{name}**: `{round(float(val)*ratio, 1)} g`")

# --- РАЗДЕЛ: ЧАТ ---
elif menu == "💬 ЧАТ":
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("Сообщение:")
        if st.form_submit_button("ОТПРАВИТЬ") and msg:
            conn = sqlite3.connect('aida_stable.db')
            conn.cursor().execute("INSERT INTO chat (user, message, timestamp) VALUES (?,?,?)", (st.session_state['user'], msg, datetime.now()))
            conn.commit(); conn.close()
            st.rerun()
            
    conn = sqlite3.connect('aida_stable.db')
    chat_df = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC LIMIT 30", conn)
    conn.close()
    
    for _, m in chat_df.iterrows():
        st.markdown(f"<div style='background:#161b22; padding:10px; border-radius:5px; margin-bottom:5px;'><b>{m['user']}</b>: {m['message']}</div>", unsafe_allow_html=True)

# --- РАЗДЕЛ: АДМИН-ПАНЕЛЬ ---
elif menu == "⚙️ АДМИН-ПАНЕЛЬ" and st.session_state['admin']:
    cleanup_logs() # Автоочистка логов старше 30 дней
    t1, t2, t3 = st.tabs(["КЛЮЧИ", "ЧАТ (МОДЕРАЦИЯ)", "ЛОГИ"])
    
    with t1:
        new_k = st.text_input("НОВЫЙ КЛЮЧ (Напр. AIDA-001)")
        new_o = st.text_input("ИМЯ КЛИЕНТА")
        if st.button("СОЗДАТЬ КЛЮЧ"):
            if new_k and new_o:
                conn = sqlite3.connect('aida_stable.db')
                try:
                    conn.cursor().execute("INSERT INTO keys (license_key, owner_name) VALUES (?,?)", (new_k, new_o))
                    conn.commit(); write_log("ROOT", f"Создан ключ {new_k}")
                    st.success("Ключ успешно создан!")
                except: st.error("Ключ уже существует.")
                conn.close()
                
    with t2:
        conn = sqlite3.connect('aida_stable.db')
        mod_df = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        for _, msg in mod_df.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{msg['user']}**: {msg['message']}")
            if c2.button("УДАЛИТЬ", key=f"del_{msg['id']}"):
                conn = sqlite3.connect('aida_stable.db')
                conn.cursor().execute("DELETE FROM chat WHERE id = ?", (msg['id'],))
                conn.commit(); conn.close()
                st.rerun()
                
    with t3:
        conn = sqlite3.connect('aida_stable.db')
        st.dataframe(pd.read_sql("SELECT * FROM logs ORDER BY timestamp DESC", conn), use_container_width=True)
        conn.close()
