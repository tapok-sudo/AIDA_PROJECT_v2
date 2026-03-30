import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# --- 1. ПРЕМИАЛЬНЫЙ СТИЛЬ ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .color-card { background: #1e293b; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .color-title { font-size: 24px; font-weight: 800; color: #60a5fa; }
    .recipe-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; }
    .recipe-val { font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ЯДРО БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_ultra_v6.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, type TEXT, years TEXT, components TEXT, notes TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base = [
            ('BMW', '475', 'Black Sapphire', 'Metallic', '2000-2026', '4003:496.4,4700:0.2,4656:0.1', 'Глубокий черный. Использовать темный грунт.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'Solid', '2013-2026', 'White:300,Black:150,Yellow:20', 'Фирменный RS-цвет. Наносить в 2 слоя.'),
            ('TOYOTA', '070', 'White Crystal', 'Pearl', '2007-2026', 'Base:400,Pearl:25,Clear:100', 'Трехслойка. Внимательно с межслойкой.'),
            ('MAZDA', '46G', 'Machine Grey', 'Metallic', '2016-2026', 'Black:200,Silver:150', 'Сложный цвет. Требует спец. подложки.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, type, years, components, notes) VALUES (?,?,?,?,?,?,?)", base)
    conn.commit()
    conn.close()

init_db()

# --- 3. ИНТЕРФЕЙС ---
st.title("🦾 AIDA PREMIUM OS")

tab1, tab2 = st.tabs(["🧪 Лаборатория", "💬 Чат"])

with tab1:
    search = st.text_input("Введите марку или код (напр. 475):")
    if search:
        conn = sqlite3.connect('aida_ultra_v6.db')
        df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'", conn)
        conn.close()
        
        for _, r in df.iterrows():
            st.markdown(f"""
            <div class="color-card">
                <div class="color-title">{r['mark']} {r['code']}</div>
                <div style="color: #94a3b8;">{r['name']} • {r['type']} • {r['years']}</div>
                <div style="margin-top: 10px; font-style: italic;">💡 {r['notes']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚖️ КАЛЬКУЛЯТОР НАЛИВА"):
                target = st.number_input("Сколько грамм?", 50, 5000, 500, 50, key=f"w_{r['id']}")
                comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
                total = sum([float(c[1]) for c in comps])
                
                for n, v in comps:
                    calc = round(float(v) * (target / total), 1)
                    st.markdown(f'<div class="recipe-row"><span>{n}</span><span class="recipe-val">{calc} г</span></div>', unsafe_allow_html=True)

with tab2:
    st.info("Чат активен. Все мастера онлайн.")
    st.text_input("Ваше сообщение...")
    st.button("Отправить")

