import streamlit as st
import sqlite3
import pandas as pd
import platform
import hashlib
import time
import os
from datetime import datetime, timedelta
import extra_streamlit_components as stx
from PIL import Image

# --- 1. ТЕХНИЧЕСКАЯ КОНФИГУРАЦИЯ & СТИЛЬ ---
st.set_page_config(page_title="AIDA SYSTEM", page_icon="🦾", layout="wide", initial_sidebar_state="collapsed")

# Современный рабочий интерфейс (Dark Mode High-Contrast)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { background-color: #0d1117; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
    
    /* Стилизация карточек и панелей */
    .st-emotion-cache-12w0qpk { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 4px !important; }
    
    /* Кастомные элементы интерфейса */
    .status-bar { padding: 10px; background: #010409; border-bottom: 1px solid #30363d; margin-bottom: 20px; font-size: 12px; display: flex; justify-content: space-between; }
    .industrial-header { border-left: 4px solid #58a6ff; padding-left: 15px; margin: 20px 0; color: #58a6ff; text-transform: uppercase; letter-spacing: 2px; }
    .chat-msg { background: #161b22; padding: 10px; border-radius: 4px; border-left: 2px solid #30363d; margin-bottom: 8px; }
    .admin-tag { background: #f85149; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
    
    /* Кнопки */
    .stButton>button { width: 100%; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; font-weight: 600; transition: 0.2s; }
    .stButton>button:hover { border-color: #8b949e; background-color: #30363d; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- 2. ЯДРО БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_production_v12.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (license_key TEXT PRIMARY KEY, owner_name TEXT, hwid TEXT, is_admin INTEGER DEFAULT 0, expires_at DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, model TEXT, code TEXT, components TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp DATETIME)''')
    
    # Наполнение если база пуста
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        data = [
            ('BMW', 'X5', '475', 'Black:350.5,Silver:45.2,Blue:12.8', 'Black Sapphire Met.'),
            ('TOYOTA', 'Camry', '070', 'White:400,Pearl:25.5,Clear:100', 'White Crystal (3-слойка)'),
            ('MAZDA', 'CX-5', '41V', 'Red Base:300,Deep Red:100,Clear:50', 'Soul Red'),
            ('LADA', 'Vesta', '240', 'White:500', 'Белое облако'),
            ('MERCEDES', 'S-Class', '197', 'Obsidian:380,Silver:20.5', 'Obsidian Black'),
            # ... (здесь будет ваш расширенный список из 35 машин)
        ]
        c.executemany("INSERT INTO recipes (mark, model, code, components, notes) VALUES (?,?,?,?,?)", data)
    conn.commit()
    conn.close()

def write_log(user, action):
    try:
        conn = sqlite3.connect('aida_production_v12.db')
        c = conn.cursor()
        c.execute("INSERT INTO logs (user, action, timestamp) VALUES (?, ?, ?)", 
                  (user, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

def cleanup_old_logs():
    try:
        conn = sqlite3.connect('aida_production_v12.db')
        c = conn.cursor()
        limit_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("DELETE FROM logs WHERE timestamp < ?", (limit_date,))
        conn.commit(); c.execute("VACUUM"); conn.close()
    except: pass

init_db()

# --- 3. БЕЗОПАСНОСТЬ (10 ЛЕТ + HWID LOCK) ---
def get_device_id():
    raw_id = f"{platform.node()}-{platform.processor()}-{platform.system()}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:12]

cookie_manager = stx.CookieManager()

def secure_login(key, name_input):
    # ПРОВЕРКА АДМИНА
    try:
        if key == st.secrets["ADMIN_CODE"]: return "ROOT_ADMIN", True
    except: pass

    # ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ
    dev_id = get_device_id()
    conn = sqlite3.connect('aida_production_v12.db')
    c = conn.cursor()
    c.execute("SELECT owner_name, hwid, is_admin FROM keys WHERE license_key = ?", (key,))
    res = c.fetchone()
    
    if res:
        owner, saved_hwid, is_admin = res
        if not saved_hwid or saved_hwid == "" or saved_hwid == "NEW":
            c.execute("UPDATE keys SET owner_name = ?, hwid = ? WHERE license_key = ?", (name_input, dev_id, key))
            conn.commit(); conn.close(); return name_input, bool(is_admin)
        elif saved_hwid == dev_id:
            conn.close(); return owner, bool(is_admin)
        else:
            conn.close(); return "WRONG_DEVICE", False
    conn.close(); return None, False

# --- 4. ЛОГИКА АВТОРИЗАЦИИ ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False

# Пытаемся восстановить сессию из кук (на 10 лет)
saved_token = cookie_manager.get(cookie="aida_eternal_token")
if saved_token and not st.session_state['authenticated']:
    name, admin = secure_login(saved_token, "AUTO_RELOAD")
    if name and name != "WRONG_DEVICE":
        st.session_state.update({"authenticated": True, "user_name": name, "is_admin": admin})

if not st.session_state['authenticated']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, log_col, _ = st.columns([1, 1.2, 1])
    with log_col:
        st.markdown("<h2 style='text-align:center;'>AIDA SYSTEM</h2>", unsafe_allow_html=True)
        u_name = st.text_input("OPERATOR_ID")
        u_key = st.text_input("ACCESS_KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            name, admin = secure_login(u_key, u_name)
            if name == "WRONG_DEVICE": st.error("LOCKED: Ключ привязан к другому устройству")
            elif name:
                st.session_state.update({"authenticated": True, "user_name": name, "is_admin": admin})
                cookie_manager.set("aida_eternal_token", u_key, expires_at=datetime.now()+timedelta(days=3650))
                st.rerun()
            else: st.error("ACCESS DENIED: INVALID KEY")
    st.stop()

# --- 5. ОСНОВНОЙ ИНТЕРФЕЙС ---
# Status Bar
st.markdown(f"""
<div class="status-bar">
    <span>SYSTEM: ONLINE</span>
    <span>OPERATOR: {st.session_state.user_name}</span>
    <span>STATION: {platform.node()}</span>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("NAVIGATIONAL MENU:", ["LABORATORY", "CHAMBER", "MESSAGES", "ADMIN PANEL" if st.session_state.is_admin else ""])

if menu == "LABORATORY":
    st.markdown('<div class="industrial-header">Formula Database Search</div>', unsafe_allow_html=True)
    query = st.text_input("ENTER CODE OR BRAND:")
    if query:
        conn = sqlite3.connect('aida_production_v12.db')
        df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{query}%' OR mark LIKE '%{query}%'", conn)
        conn.close()
        for _, r in df.iterrows():
            with st.expander(f"REPRO: {r['mark']} | {r['code']}"):
                target = st.number_input("TOTAL WT (g):", 10, 5000, 500, key=f"r_{r['id']}")
                comps = [i.split(":") for i in r['components'].split(",") if ":" in i]
                ratio = target / sum([float(i[1]) for i in comps])
                st.markdown("---")
                for name, val in comps:
                    st.write(f"**{name}**: `{round(float(val)*ratio, 2)} g`")

elif menu == "MESSAGES":
    st.markdown('<div class="industrial-header">Production Chat</div>', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        m_txt = st.text_input("MESSAGE:")
        if st.form_submit_button("SEND"):
            conn = sqlite3.connect('aida_production_v12.db')
            conn.cursor().execute("INSERT INTO chat (user, message, timestamp) VALUES (?,?,?)", 
                                  (st.session_state.user_name, m_txt, datetime.now()))
            conn.commit(); conn.close(); st.rerun()
    
    conn = sqlite3.connect('aida_production_v12.db')
    chat_data = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC LIMIT 30", conn)
    conn.close()
    for _, m in chat_data.iterrows():
        st.markdown(f'<div class="chat-msg"><b>{m["user"]}</b>: {m["message"]} <br><small>{m["timestamp"][11:16]}</small></div>', unsafe_allow_html=True)

elif menu == "ADMIN PANEL" and st.session_state.is_admin:
    cleanup_old_logs()
    st.markdown('<div class="industrial-header">Root Administration</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["KEY CONTROL", "30-DAY LOGS", "CHAT MODERATION"])
    
    with t1:
        new_k = st.text_input("NEW LICENSE KEY")
        new_o = st.text_input("CLIENT NAME")
        if st.button("ISSUE LICENSE"):
            conn = sqlite3.connect('aida_production_v12.db')
            conn.cursor().execute("INSERT INTO keys (license_key, owner_name, hwid) VALUES (?,?,?)", (new_k, new_o, "NEW"))
            conn.commit(); conn.close(); st.success("KEY ISSUED")
            
    with t2:
        conn = sqlite3.connect('aida_production_v12.db')
        st.dataframe(pd.read_sql("SELECT * FROM logs ORDER BY timestamp DESC", conn), use_container_width=True)
        conn.close()
        
    with t3:
        conn = sqlite3.connect('aida_production_v12.db')
        mod_chat = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC", conn)
        conn.close()
        for _, msg in mod_chat.iterrows():
            c1, c2 = st.columns([5, 1])
            c1.write(f"[{msg['user']}]: {msg['message']}")
            if c2.button("DELETE", key=f"del_{msg['id']}"):
                conn = sqlite3.connect('aida_production_v12.db')
                conn.cursor().execute("DELETE FROM chat WHERE id = ?", (msg['id'],))
                conn.commit(); conn.close(); st.rerun()
