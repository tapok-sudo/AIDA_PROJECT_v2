import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx

# --- 1. СТИЛЬ ТОНИ СТАРКА ---
st.set_page_config(page_title="AIDA PREMIUM", page_icon="🦾", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stHeader { background: #161b22; }
    .color-card { 
        background: #161b22; border: 1px solid #30363d; 
        padding: 20px; border-radius: 10px; margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .color-title { font-size: 24px; font-weight: 800; color: #58a6ff; }
    .recipe-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; }
    .recipe-val { font-weight: 700; color: #79c0ff; font-family: 'Courier New', monospace; font-size: 18px; }
    .stButton>button { width: 100%; border-radius: 6px; background-color: #238636; color: white; border: none; }
</style>
""", unsafe_allow_html=True)

# --- 2. ИНИЦИАЛИЗАЦИЯ БАЗЫ (AIDA V6) ---
def init_db():
    conn = sqlite3.connect('aida_v6_final.db')
    c = conn.cursor()
    # Таблица рецептов
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base_data = [
            ('BMW', '475', 'Black Sapphire', 'Black:496,Silver:2.5,Blue:0.5', 'Классический черный сапфир. Требует темный грунт.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'White:300,Black:150,Yellow:20', 'Популярный серый. Наносить в 2 полных слоя.'),
            ('MAZDA', '46V', 'Soul Red Crystal', 'Base:200,Red_Pearl:50,Clear:100', 'Трехслойный процесс. Важен контроль давления.'),
            ('TOYOTA', '070', 'White Crystal', 'White:400,Pearl:30', 'Белый перламутр. Требует белую подложку.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, components, notes) VALUES (?,?,?,?,?)", base_data)
    conn.commit()
    conn.close()

init_db()

# --- 3. ИНТЕРФЕЙС ---
st.title("🦾 AIDA PREMIUM OS")
st.write(f"Добро пожаловать, **Мой Лорд**.")

tab1, tab2, tab3 = st.tabs(["🧪 ЛАБОРАТОРИЯ", "💬 ЧАТ", "⚙️ АДМИН"])

with tab1:
    search = st.text_input("Введите код или марку (напр. 475 или BMW):")
    
    conn = sqlite3.connect('aida_v6_final.db')
    query = f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'"
    df = pd.read_sql(query, conn)
    conn.close()

    for _, r in df.iterrows():
        st.markdown(f"""
        <div class="color-card">
            <div class="color-title">{r['mark']} — {r['code']}</div>
            <div style="color: #8b949e; margin-bottom: 10px;">{r['name']}</div>
            <div style="background: #0d1117; padding: 10px; border-radius: 5px; border-left: 3px solid #238636;">
                📝 {r['notes']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("⚖️ РАССЧИТАТЬ НАЛИВ"):
            target_weight = st.number_input("Нужный вес (грамм):", 50, 5000, 500, 50, key=f"w_{r['id']}")
            
            # Логика расчета
            comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
            total_parts = sum([float(c[1]) for c in comps])
            
            for c_name, c_val in comps:
                calculated = round(float(c_val) * (target_weight / total_parts), 1)
                st.markdown(f"""
                <div class="recipe-row">
                    <span>{c_name}</span>
                    <span class="recipe-val">{calculated} г</span>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.info("Чат цеха в режиме ожидания. Все мастера онлайн.")
    st.text_area("Сообщение для команды:")
    st.button("ОТПРАВИТЬ")

with tab3:
    st.warning("Доступ только для администратора системы.")
    st.text_input("Ключ доступа", type="password")

