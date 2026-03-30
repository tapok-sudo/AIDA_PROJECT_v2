import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid

# --- 1. ПРЯМАЯ НАСТРОЙКА ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .color-card { background: #1e293b; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .color-title { font-size: 22px; font-weight: bold; color: #60a5fa; }
    .recipe-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; }
    .recipe-val { font-weight: bold; color: #38bdf8; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. БАЗА ДАННЫХ (V9 - КРИТИЧЕСКАЯ СТАБИЛЬНОСТЬ) ---
def init_db():
    conn = sqlite3.connect('aida_v9_stable.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS keys (license_key TEXT PRIMARY KEY, owner_name TEXT, is_admin INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT)')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        data = [
            ('BMW', '475', 'Black Sapphire', 'Black:496,Silver:3,Blue:1', 'Использовать темный грунт.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'White:300,Black:150,Yellow:20', 'Классический серый.'),
            ('TOYOTA', '070', 'White Crystal', 'Base:400,Pearl:35', 'Трехслойный перламутр.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, components, notes) VALUES (?,?,?,?,?)", data)
        c.execute("INSERT OR IGNORE INTO keys VALUES ('MASTER_AIDA_2026', 'ADMIN', 1)")
    conn.commit()
    conn.close()

init_db()

# --- 3. УПРОЩЕННЫЙ ВХОД ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🦾 СИСТЕМА AIDA")
    key = st.text_input("ВВЕДИТЕ ВАШ КЛЮЧ:", type="password")
    if st.button("ПОДТВЕРДИТЬ"):
        if key == "MASTER_AIDA_2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Ключ не найден.")
    st.stop()

# --- 4. ОСНОВНОЙ МОДУЛЬ ---
st.title("🦾 AIDA OS: ONLINE")
tab1, tab2 = st.tabs(["🧪 ЛАБОРАТОРИЯ", "💬 ЧАТ"])

with tab1:
    search = st.text_input("Поиск по коду (например: 475):")
    conn = sqlite3.connect('aida_v9_stable.db')
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%'", conn)
    conn.close()
    
    for _, r in df.iterrows():
        st.markdown(f'<div class="color-card"><div class="color-title">{r["mark"]} {r["code"]}</div><div>{r["name"]}</div></div>', unsafe_allow_html=True)
        with st.expander("⚖️ Рассчитать вес"):
            weight = st.number_input("Нужный вес (г):", 50, 5000, 500, 50, key=r['id'])
            comps = [c.split(":") for c in r['components'].split(",")]
            total = sum(float(c[1]) for c in comps)
            for n, v in comps:
                res = round(float(v) * (weight / total), 1)
                st.markdown(f'<div class="recipe-row"><span>{n}</span><span class="recipe-val">{res} г</span></div>', unsafe_allow_html=True)

with tab2:
    st.info("Чат активен. Сообщения сохраняются локально.")
    st.text_input("Написать...")
    st.button("Отправить")

