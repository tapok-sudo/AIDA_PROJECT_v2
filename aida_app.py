import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# --- 1. СТИЛЬ И КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .color-card { background: #1e293b; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .color-title { font-size: 24px; font-weight: 800; color: #60a5fa; }
    .recipe-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; }
    .recipe-val { font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 18px; }
    .chat-msg { background: #334155; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #fbbf24; }
</style>
""", unsafe_allow_html=True)

# --- 2. СЕССИЯ И КУКИ ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'admin': False})

# --- 3. БАЗА ДАННЫХ (НОВАЯ ВЕРСИЯ V8) ---
def init_db():
    conn = sqlite3.connect('aida_v8_fixed.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        recipes = [
            ('BMW', '475', 'Black Sapphire', 'Black:496,Silver:2.5,Blue:0.5', 'Черный сапфир. Глубокий блеск.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'White:300,Black:150,Yellow:20', 'Солид. Популярный серый.'),
            ('TOYOTA', '070', 'White Crystal', 'Base:400,Pearl:30', 'Трехслойный перламутр.'),
            ('MAZDA', '46V', 'Soul Red', 'Base:200,Red_Pearl:50', 'Сложный красный кристалл.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, components, notes) VALUES (?,?,?,?,?)", recipes)
    conn.commit()
    conn.close()

init_db()

# --- 4. АВТОРИЗАЦИЯ ---
token = cookie_manager.get(cookie="aida_token")
if token and not st.session_state.auth:
    conn = sqlite3.connect('aida_v8_fixed.db')
    res = conn.cursor().execute("SELECT owner_name, is_admin FROM keys WHERE device_token = ?", (token,)).fetchone()
    conn.close()
    if res:
        st.session_state.update({'auth': True, 'user': res[0], 'admin': bool(res[1])})

if not st.session_state.auth:
    st.title("🦾 AIDA: ВХОД")
    key_input = st.text_input("Введите ваш ключ доступа:", type="password")
    if st.button("ВОЙТИ"):
        if key_input == "MASTER_AIDA_2026":
            cookie_manager.set("aida_token", "MASTER_TOKEN", expires_at=datetime.now()+timedelta(days=365))
            st.success("Доступ разрешен. Обновите страницу (F5).")
        else:
            conn = sqlite3.connect('aida_v8_fixed.db')
            c = conn.cursor()
            res = c.execute("SELECT owner_name, device_token FROM keys WHERE license_key = ?", (key_input,)).fetchone()
            if res and not res[1]:
                new_token = str(uuid.uuid4())
                c.execute("UPDATE keys SET device_token = ? WHERE license_key = ?", (new_token, key_input))
                conn.commit()
                cookie_manager.set("aida_token", new_token, expires_at=datetime.now()+timedelta(days=365))
                st.success("Устройство привязано. Обновите страницу.")
            else:
                st.error("Ошибка ключа или он уже используется.")
            conn.close()
    st.stop()

# --- 5. ОСНОВНОЙ КОНТЕНТ ---
st.sidebar.title(f"Мастер: {st.session_state.user}")
menu = ["🧪 Лаборатория", "💬 Чат"]
if st.session_state.admin: menu.append("⚙️ Админ")
choice = st.sidebar.radio("Навигация", menu)

if choice == "🧪 Лаборатория":
    st.header("Поиск рецептов")
    search = st.text_input("Код краски:")
    conn = sqlite3.connect('aida_v8_fixed.db')
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%'", conn)
    conn.close()
    
    for _, r in df.iterrows():
        st.markdown(f'<div class="color-card"><div class="color-title">{r["mark"]} {r["code"]}</div><div>{r["name"]}</div></div>', unsafe_allow_html=True)
        with st.expander("⚖️ Рассчитать вес"):
            target = st.number_input("Грамм:", 50, 5000, 500, 50, key=r['id'])
            comps = [c.split(":") for c in r['components'].split(",")]
            total = sum(float(c[1]) for c in comps)
            for n, v in comps:
                st.markdown(f'<div class="recipe-row"><span>{n}</span><span class="recipe-val">{round(float(v)*(target/total),1)} г</span></div>', unsafe_allow_html=True)

elif choice == "💬 Чат":
    st.header("Чат мастеров")
    msg = st.chat_input("Ваше сообщение...")
    conn = sqlite3.connect('aida_v8_fixed.db')
    if msg:
        conn.cursor().execute("INSERT INTO chat (user, message, timestamp) VALUES (?,?,?)", (st.session_state.user, msg, datetime.now().strftime("%H:%M")))
        conn.commit()
    df_c = pd.read_sql("SELECT * FROM chat ORDER BY id DESC LIMIT 20", conn)
    conn.close()
    for _, m in df_c.iterrows():
        st.markdown(f'<div class="chat-msg"><b>{m["user"]}</b> ({m["timestamp"]}):<br>{m["message"]}</div>', unsafe_allow_html=True)

elif choice == "⚙️ Админ" and st.session_state.admin:
    st.header("Управление ключами")
    # Исправленный блок запроса (проблема была здесь)
    conn = sqlite3.connect('aida_v8_fixed.db')
    df_keys = pd.read_sql("SELECT license_key, owner_name, is_admin FROM keys", conn)
    conn.close()
    st.dataframe(df_keys)

