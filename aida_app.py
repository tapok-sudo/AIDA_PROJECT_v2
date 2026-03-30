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

# --- 1. CONFIGURATION & PWA METADATA ---
st.set_page_config(page_title="AIDA SYSTEM", page_icon="🦾", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Roboto', sans-serif; }
    .formula-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .stButton>button { width: 100%; height: 45px; border-radius: 4px; background-color: #21262d; color: #58a6ff; border: 1px solid #30363d; }
    .admin-badge { color: #f85149; border: 1px solid #f85149; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .ai-panel { background: #0d1117; border-left: 4px solid #238636; padding: 15px; border-radius: 4px; }
    .metric-box { text-align: center; border-right: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & LOGGING ENGINE ---
def init_db():
    conn = sqlite3.connect('aida_production_v12.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (license_key TEXT PRIMARY KEY, owner_name TEXT, hwid TEXT, is_admin INTEGER DEFAULT 0, expires_at DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, model TEXT, code TEXT, components TEXT, notes TEXT)''')
    
    # Наполнение базы (35+ машин) если пусто
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        data = [
            ('BMW', 'X5', '475', 'Black:350.5,Silver:45.2', 'Black Sapphire Met.'),
            ('TOYOTA', 'Camry', '070', 'White:400,Pearl:25.5,Clear:100', 'White Crystal (3-Layer)'),
            ('MAZDA', 'CX-5', '41V', 'Red Base:300,Deep Red:100', 'Soul Red'),
            ('LADA', 'Vesta', '240', 'White:500', 'Белое облако'),
            # ... (здесь весь список из 35 машин, который я давал выше)
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

init_db()

# --- 3. SECURITY ---
def get_device_id():
    raw_id = f"{platform.node()}-{platform.processor()}-{platform.system()}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:12]

try:
    SPECIAL_ADMIN_CODE = st.secrets["ADMIN_CODE"]
except:
    SPECIAL_ADMIN_CODE = "DEV_MODE_ACTIVE"

cookie_manager = stx.CookieManager()

def secure_login(key, name_input):
    dev_id = get_device_id()
    if key == SPECIAL_ADMIN_CODE:
        write_log("ROOT", "ADMIN_ACCESS_GRANTED")
        return "STARK_SYSTEM_ADMIN", True
        
    conn = sqlite3.connect('aida_production_v12.db')
    c = conn.cursor()
    c.execute("SELECT owner_name, hwid, is_admin, expires_at FROM keys WHERE license_key = ?", (key,))
    res = c.fetchone()
    if res:
        owner, saved_hwid, is_admin, expires_at = res
        # Проверка срока действия
        if expires_at and datetime.strptime(expires_at, '%Y-%m-%d').date() < datetime.now().date():
            conn.close(); return "EXPIRED", False
            
        if not owner or owner == "" or owner == "RE_AUTH_PROC":
            c.execute("UPDATE keys SET owner_name = ?, hwid = ? WHERE license_key = ?", (name_input, dev_id, key))
            conn.commit(); conn.close(); write_log(name_input, "NEW_DEVICE_LINKED"); return name_input, bool(is_admin)
        elif saved_hwid == dev_id:
            conn.close(); write_log(owner, "SESSION_START"); return owner, bool(is_admin)
    conn.close(); return None, False

# --- 4. AUTH LOGIC ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    _, log_col, _ = st.columns([1, 1.5, 1])
    with log_col:
        st.subheader("AIDA INDUSTRIAL ACCESS")
        u_name = st.text_input("OPERATOR_ID")
        u_key = st.text_input("ACCESS_KEY", type="password")
        if st.button("AUTHORIZE"):
            name, admin = secure_login(u_key, u_name)
            if name == "EXPIRED": st.error("LICENSE EXPIRED")
            elif name:
                st.session_state.update({"authenticated": True, "user_name": name, "is_admin": admin})
                cookie_manager.set("aida_token", u_key, expires_at=datetime.now()+timedelta(days=30))
                st.rerun()
            else: st.error("INVALID_KEY")
    st.stop()

# --- 5. INTERFACE ---
st.sidebar.markdown(f"**OP:** {st.session_state.user_name}")
if st.session_state.is_admin: st.sidebar.markdown('<span class="admin-badge">ROOT</span>', unsafe_allow_html=True)

role = st.sidebar.selectbox("STATION:", ["LAB (COLORIST)", "BOOTH (PAINTER)"])
menu = st.sidebar.radio("MENU:", ["DATABASE", "SETTINGS", "ADMIN" if st.session_state.is_admin else ""])

if role == "LAB (COLORIST)":
    if menu == "DATABASE":
        st.header("COLOR REPRO DATABASE")
        search = st.text_input("SEARCH CODE:")
        if search:
            conn = sqlite3.connect('aida_production_v12.db')
            df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'", conn)
            conn.close()
            for _, r in df.iterrows():
                with st.expander(f"{r['mark']} {r['code']}"):
                    target_w = st.number_input("TARGET (g):", 10, 5000, 500, key=f"l_{r['id']}")
                    items = [i.split(":") for i in r['components'].split(",") if ":" in i]
                    ratio = target_w / sum([float(i[1]) for i in items])
                    for name, val in items:
                        st.write(f"**{name}**: {round(float(val)*ratio, 2)} g")

else: # PAINTER MODE
    if menu == "DATABASE":
        st.header("APPLICATION CONTROL")
        st.markdown('<div class="ai-panel"><strong>ENVIRONMENTAL SENSORS</strong></div>', unsafe_allow_html=True)
        temp = st.slider("TEMP (°C)", 10, 45, 23)
        press = 2.0 if temp < 26 else 2.3
        st.metric("AIR PRESSURE", f"{press} BAR")
        
        st.markdown("---")
        p_w = st.number_input("PAINT WEIGHT (g):", 50, 5000, 250)
        t_r = st.selectbox("THINNER %:", [10, 20, 50, 80], index=3)
        st.info(f"REQUIRED THINNER: {(p_w * t_r) / 100} g")

if menu == "ADMIN" and st.session_state.is_admin:
    st.header("ROOT CONTROL")
    t1, t2 = st.tabs(["LICENSES", "LOGS"])
    with t1:
        new_k = st.text_input("NEW KEY")
        new_o = st.text_input("CLIENT")
        if st.button("CREATE"):
            conn = sqlite3.connect('aida_production_v12.db')
            conn.cursor().execute("INSERT INTO keys (license_key, owner_name, expires_at) VALUES (?,?,?)", 
                                  (new_k, new_o, (datetime.now()+timedelta(days=30)).date()))
            conn.commit(); conn.close(); st.success("KEY GENERATED")
    with t2:
        conn = sqlite3.connect('aida_production_v12.db')
        st.table(pd.read_sql("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 20", conn))
        conn.close()
