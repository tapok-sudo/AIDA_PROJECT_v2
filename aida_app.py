import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# --- КОНФИГУРАЦИЯ И СТИЛЬ (PREMIUM DARK) ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #0d1117; color: #e6edf3; font-family: 'Inter', sans-serif; }
    .color-card { 
        background: linear-gradient(145deg, #161b22, #0d1117); 
        border: 1px solid #30363d; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .stButton>button { 
        width: 100%; border-radius: 8px; background: #238636; 
        color: white; border: none; font-weight: 800; padding: 12px;
    }
    .recipe-row { 
        display: flex; justify-content: space-between; 
        padding: 10px 0; border-bottom: 1px solid #30363d; 
    }
    .comp-name { color: #8b949e; font-weight: 600; }
    .comp-val { color: #58a6ff; font-family: 'Courier New', monospace; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- УПРАВЛЕНИЕ СЕССИЕЙ ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# --- ЯДРО БАЗЫ ДАННЫХ (С АВТО-ИСПРАВЛЕНИЕМ) ---
def init_db():
    conn = sqlite3.connect('aida_v4_stable.db')
    c = conn.cursor()
    # Таблица ключей
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    # Таблица рецептов (Расширенная)
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, 
                  type TEXT, years TEXT, components TEXT, notes TEXT)''')
    # Чат и Логи
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp DATETIME)''')
    
    # Наполнение базы легендарными цветами
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        data = [
            ('BMW', '475', 'Black Sapphire', 'Metallic', '2000-2026', '4003:496.4,4700:0.2,4656:0.1', 'Глубокий черный. Требует темный грунт G5.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'Solid', '2013-2026', 'White:300.5,Black:150.2,Yellow:20.0', 'Легендарный серый. Наносить в 2.5 слоя.'),
            ('TOYOTA', '070', 'White Crystal', 'Pearl (3-Stage)', '2010-2026', 'Base:400,Pearl:25.5,Clear:100', 'Трехслойное покрытие. Важен контроль давления.'),
            ('MAZDA', '46V', 'Soul Red Crystal', 'Candy Metallic', '2017-2026', 'Red_Base:200,High_Bright:150', 'Очень сложный цвет. Требует спец. подложки.'),
            ('MERCEDES', '197', 'Obsidian Black', 'Metallic', '2005-2026', 'Deep_Black:450,Silver:15.5', 'Классика. Использовать медленный разбавитель.'),
            ('PORSCHE', 'M7Z', 'GT Silver', 'Metallic', '2004-2026', 'Fine_Silver:400,Black:10,Blue:2', 'Чистое серебро. Избегать «яблок» при распыле.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, type, years, components, notes) VALUES (?,?,?,?,?,?,?)", data)
    conn.commit()
    conn.close()

init_db()

# --- ЛОГИКА ДОСТУПА ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'admin': False})

token = cookie_manager.get(cookie="aida_token_v4")
if token and not st.session_state.auth:
    admin_code = st.secrets.get("ADMIN_CODE", "MASTER_AIDA")
    if token == admin_code:
        st.session_state.update({'auth': True, 'user': 'ADMIN', 'admin': True})
    else:
        conn = sqlite3.connect('aida_v4_stable.db')
        res = conn.cursor().execute("SELECT owner_name, is_admin FROM keys WHERE device_token = ?", (token,)).fetchone()
        conn.close()
        if res: st.session_state.update({'auth': True, 'user': res[0], 'admin': bool(res[1])})

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🦾 AIDA OS</h1>", unsafe_allow_html=True)
    key = st.text_input("ВВЕДИТЕ КЛЮЧ ДОСТУПА", type="password")
    if st.button("АВТОРИЗАЦИЯ"):
        admin_code = st.secrets.get("ADMIN_CODE", "MASTER_AIDA")
        if key == admin_code:
            cookie_manager.set("aida_token_v4", admin_code, expires_at=datetime.now()+timedelta(days=365))
            st.rerun()
        else:
            conn = sqlite3.connect('aida_v4_stable.db')
            c = conn.cursor()
            res = c.execute("SELECT owner_name, device_token FROM keys WHERE license_key = ?", (key,)).fetchone()
            if res:
                if not res[1]: # Привязка первого устройства
                    new_token = str(uuid.uuid4())
                    c.execute("UPDATE keys SET device_token = ? WHERE license_key = ?", (new_token, key))
                    conn.commit()
                    cookie_manager.set("aida_token_v4", new_token, expires_at=datetime.now()+timedelta(days=365))
                    st.rerun()
                else: st.error("Ключ уже привязан к другому телефону.")
            else: st.error("Неверный ключ.")
            conn.close()
    st.stop()

# --- ИНТЕРФЕЙС ---
st.sidebar.title("МЕНЮ СИСТЕМЫ")
page = st.sidebar.radio("Перейти:", ["🧪 Лаборатория", "💬 Чат цеха", "⚙️ Админ"])

if page == "🧪 Лаборатория":
    st.title("База рецептов")
    q = st.text_input("Поиск по коду или марке (напр. 475 или Audi):")
    
    conn = sqlite3.connect('aida_v4_stable.db')
    query = f"SELECT * FROM recipes WHERE code LIKE '%{q}%' OR mark LIKE '%{q}%'"
    df = pd.read_sql(query, conn)
    conn.close()

    for _, r in df.iterrows():
        st.markdown(f"""
        <div class="color-card">
            <div style="font-size: 22px; font-weight: 800; color: #58a6ff;">{r['mark']} {r['code']}</div>
            <div style="color: #8b949e; margin-bottom: 10px;">{r['name']} | {r['type']} | {r['years']}</div>
            <div style="font-size: 14px; background: #21262d; padding: 10px; border-radius: 5px; border-left: 3px solid #238636;">
                📝 {r['notes']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("⚖️ РАССЧИТАТЬ ВЕС"):
            target = st.number_input("Нужный вес (грамм):", 50, 5000, 500, step=50, key=f"w_{r['id']}")
            comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
            total_parts = sum([float(c[1]) for c in comps])
            ratio = target / total_parts
            
            for c_name, c_val in comps:
                res_w = round(float(c_val) * ratio, 2)
                st.markdown(f"""
                <div class="recipe-row">
                    <span class="comp-name">{c_name}</span>
                    <span class="comp-val">{res_w} г</span>
                </div>
                """, unsafe_allow_html=True)

elif page == "💬 Чат цеха":
    st.title("Связь с мастерами")
    # Логика чата... (аналогично предыдущей версии)

elif page == "⚙️ Админ" and st.session_state.admin:
    st.title("Управление доступом")
    new_k = st.text_input("Новый ключ")
    new_o = st.text_input("Имя маляра")
    if st.button("Создать доступ"):
        conn = sqlite3.connect('aida_v4_stable.db')
        conn.cursor().execute("INSERT INTO keys (license_key, owner_name) VALUES (?,?)", (new_k, new_o))
        conn.commit(); conn.close()
        st.success("Готово!")
