import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
from datetime import datetime, timedelta

# --- 1. CONFIG & MOBILE OPTIMIZATION ---
st.set_page_config(
    page_title="AIDA OS", 
    page_icon="🦾", 
    layout="centered", # Центрированный лейаут лучше для узких экранов телефонов
    initial_sidebar_state="collapsed"
)

# Ультра-легкий CSS для скорости загрузки
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap');
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Roboto Mono', monospace; }
    .stButton>button { width: 100%; border-radius: 2px; background-color: #21262d; border: 1px solid #30363d; color: #58a6ff; font-weight: bold;}
    .formula-card { background: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 4px; margin-bottom: 10px; }
    .stInput>div>div>input { background-color: #0d1117; border: 1px solid #30363d; color: #c9d1d9; }
</style>
""", unsafe_allow_html=True)

# --- 2. FAST DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('aida_fast_v1.db')
    c = conn.cursor()
    # Таблица ключей
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (key TEXT PRIMARY KEY, owner TEXT, is_admin INTEGER DEFAULT 0)''')
    # Таблица рецептов
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, components TEXT)''')
    
    # Наполнение если пусто
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        data = [
            ('BMW', '475', 'Black:350,Silver:50'),
            ('TOYOTA', '070', 'White:400,Pearl:25'),
            ('MAZDA', '41V', 'Red Base:300,Deep Red:100')
        ]
        c.executemany("INSERT INTO recipes (mark, code, components) VALUES (?,?,?)", data)
    
    # Дефолтный админ ключ (замените на свой)
    c.execute("INSERT OR IGNORE INTO keys (key, owner, is_admin) VALUES ('ROOT_KEY', 'AIDA_OWNER', 1)")
    
    conn.commit()
    conn.close()

init_db()

# --- 3. MOBILE AUTH (SIMPLE & FAST) ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #58a6ff;'>AIDA SYSTEM</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 12px;'>INDUSTRIAL ACCESS</p>", unsafe_allow_html=True)
    
    # Простой ввод ключа для телефона
    user_key = st.text_input("ACCESS KEY", type="password", placeholder="Введите ваш ключ")
    
    if st.button("AUTHORIZE"):
        if user_key:
            conn = sqlite3.connect('aida_fast_v1.db')
            c = conn.cursor()
            c.execute("SELECT owner, is_admin FROM keys WHERE key = ?", (user_key,))
            res = c.fetchone()
            conn.close()
            
            if res:
                st.session_state.update({"auth": True, "name": res[0], "admin": bool(res[1])})
                st.rerun()
            else:
                st.error("INVALID KEY")
    st.stop()

# --- 4. MAIN INTERFACE (MOBILE FIRST) ---
# Кнопка выхода в углу
col_u, col_o = st.columns([4, 1])
col_u.write(f"OP: {st.session_state.name}")
if col_o.button("EXIT"):
    st.session_state.clear()
    st.rerun()

st.markdown("---")

# Меню на телефоне лучше делать через Selectbox вверху
mode = st.selectbox("SECTION:", ["SEARCH DATABASE", "ADMIN"] if st.session_state.admin else ["SEARCH DATABASE"])

if mode == "SEARCH DATABASE":
    st.subheader("FIND FORMULA")
    # Поиск по коду или марке
    search = st.text_input("Enter Code or Mark:", placeholder="Example: 41V")
    
    if search:
        conn = sqlite3.connect('aida_fast_v1.db')
        df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%' LIMIT 10", conn)
        conn.close()
        
        if df.empty:
            st.warning("Formula not found.")
        else:
            for _, r in df.iterrows():
                # Карточка рецепта в мобильном стиле
                with st.container():
                    st.markdown(f"""
                    <div class="formula-card">
                        <span style="color: #58a6ff; font-weight: bold; font-size: 18px;">{r['mark']} {r['code']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Разбор компонентов
                    comps = [i.split(":") for i in r['components'].split(",") if ":" in i]
                    
                    # Ввод веса (удобно для пальца)
                    target_w = st.number_input(f"Required Weight (g):", 10, 5000, 500, step=10, key=f"inp_{r['id']}")
                    
                    # Расчет
                    total_parts = sum([float(i[1]) for i in comps])
                    ratio = target_w / total_parts
                    
                    # Таблица налива
                    for c_name, c_val in comps:
                        st.markdown(f"**{c_name}**: `{round(float(c_val)*ratio, 1)} g`")
                    st.markdown("---")

elif mode == "ADMIN" and st.session_state.admin:
    st.subheader("ROOT PANEL")
    new_k = st.text_input("NEW KEY STRING")
    new_o = st.text_input("CLIENT NAME")
    if st.button("GENERATE KEY"):
        if new_k and new_o:
            conn = sqlite3.connect('aida_fast_v1.db')
            try:
                conn.cursor().execute("INSERT INTO keys (key, owner) VALUES (?,?)", (new_k, new_o))
                conn.commit()
                st.success("New key created successfully.")
            except:
                st.error("Key already exists.")
            conn.close()
