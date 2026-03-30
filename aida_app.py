import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# Упрощенный кэш для старых версий сервера
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# Инициализация базы с защитой от ошибок
def init_db():
    conn = sqlite3.connect('aida_final_v5.db') # НОВОЕ ИМЯ БАЗЫ
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO recipes (mark, code, name, components, notes) VALUES ('BMW', '475', 'Black Sapphire', '4003:496,4700:0.2', 'Черный металлик')")
    conn.commit()
    conn.close()

init_db()

st.title("🦾 AIDA SYSTEM")
st.write("Система загружена и готова к работе.")

# Простейшее меню
page = st.selectbox("Меню", ["🧪 Лаборатория", "⚙️ Админ"])

if page == "🧪 Лаборатория":
    search = st.text_input("Поиск по коду:")
    conn = sqlite3.connect('aida_final_v5.db')
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%'", conn)
    conn.close()
    st.dataframe(df)

elif page == "⚙️ Админ":
    st.write("Панель управления доступом")

