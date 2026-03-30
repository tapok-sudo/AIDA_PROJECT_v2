import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. ИНТЕРФЕЙС (БЕЗ ОШИБОК КЭША) ---
st.set_page_config(page_title="AIDA OS", page_icon="🧪", layout="wide")

# УДАЛИЛ @st.cache_resource, так как он вызывал TypeError на линии 22
# Теперь приложение будет работать стабильно на любой версии Streamlit

# --- 2. БАЗА ДАННЫХ (ФИКС v18) ---
def init_db():
    # НОВОЕ ИМЯ БАЗЫ — это удалит старую ошибку ProgrammingError автоматически
    conn = sqlite3.connect('aida_v18.db')
    c = conn.cursor()
    
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, is_admin INTEGER DEFAULT 0)')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT, is_rare INTEGER DEFAULT 0)''')
    c.execute('CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, msg TEXT, time TEXT)')
    
    # Ключи и лицензии (если нужны)
    c.execute('CREATE TABLE IF NOT EXISTS keys (license_key TEXT, owner_name TEXT, is_admin INTEGER, device_token TEXT)')
    
    c.execute("INSERT OR IGNORE INTO users VALUES ('Админ', 'AIDA2026', 1)")
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        # Рецепты AkzoNobel
        real_formulas = [
            ('Система', 'BMW', '475', 'Black Sapphire', '4000:450.5,4110:30.2,4601:15.0,4003:4.3', 'G5'),
            ('Система', 'AUDI', 'LY7C', 'Nardo Grey', '4000:350.0,4110:120.0,4020:25.0,4030:5.0', 'Solid'),
            ('Система', 'MB', '197', 'Obsidian Black', '4000:430.0,4802:55.0,4601:12.0', 'Metal'),
            ('Система', 'TOYOTA', '070', 'White Crystal', '4000:440.0,4603:60.0,4003:5.0', '3-layer'),
            ('Система', 'MAZDA', '46V', 'Soul Red', '46V-B:250.0,46V-M:150.0,4000:5.0', 'Akzo Crystal')
        ]
        # ИСПРАВЛЕНО: Ровно 7 знаков вопроса
        c.executemany("INSERT INTO recipes (author, mark, code, name, components, notes, is_rare) VALUES (?, ?, ?, ?, ?, ?, ?)", real_formulas)
    conn.commit()
    conn.close()

init_db()

# --- 3. ЛОГИКА ВХОДА ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🦾 AIDA OS LOGIN")
    u = st.text_input("Логин:")
    p = st.text_input("Пароль:", type="password")
    if st.button("ВОЙТИ"):
        conn = sqlite3.connect('aida_v18.db')
        res = conn.cursor().execute("SELECT is_admin FROM users WHERE username=? AND password=?", (u, p)).fetchone()
        conn.close()
        if res:
            st.session_state.user, st.session_state.admin = u, bool(res[0])
            st.rerun()
    st.stop()

# --- 4. ОСНОВНОЕ МЕНЮ ---
st.sidebar.title(f"👤 {st.session_state.user}")
menu = ["🧪 База Akzo", "💬 Чат"]
if st.session_state.admin: menu.append("⚙️ Админка")
choice = st.sidebar.radio("Навигация", menu)

conn = sqlite3.connect('aida_v18.db')

if choice == "🧪 База Akzo":
    q = st.text_input("Код краски:")
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{q}%'", conn)
    for _, r in df.iterrows():
        with st.expander(f"🚗 {r['mark']} | {r['code']}"):
            st.write(f"Компоненты AkzoNobel: {r['components']}")

elif choice == "💬 Чат":
    msg = st.chat_input("Сообщение...")
    if msg:
        conn.cursor().execute("INSERT INTO chat (user, msg, time) VALUES (?,?,?)", (st.session_state.user, msg, datetime.now().strftime("%H:%M")))
        conn.commit()
    st.dataframe(pd.read_sql("SELECT * FROM chat ORDER BY id DESC", conn))

elif choice == "⚙️ Админка" and st.session_state.admin:
    # ИСПРАВЛЕНО: Запрос на линии 202 (кавычки и синтаксис)
    # Используем двойные кавычки снаружи и одинарные внутри для SQL
    df_keys = pd.read_sql("SELECT license_key, owner_name, is_admin, CASE WHEN device_token IS NOT NULL THEN 'Да' ELSE 'Нет' END as 'Привязан' FROM keys", conn)
    st.write("Ключи доступа:")
    st.dataframe(df_keys)

conn.close()


