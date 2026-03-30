import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. ПРЯМАЯ НАСТРОЙКА ИНТЕРФЕЙСА ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b121d; color: #e2e8f0; }
    .color-card { background: #1a2234; border-left: 5px solid #3b82f6; padding: 15px; border-radius: 8px; margin-bottom: 12px; }
    .color-title { font-size: 20px; font-weight: 800; color: #60a5fa; margin-bottom: 5px; }
    .recipe-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #2d3748; }
    .recipe-val { font-weight: bold; color: #38bdf8; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. ГЕНЕРАЦИЯ РАСШИРЕННОЙ БАЗЫ (100+ ЦВЕТОВ) ---
def init_db():
    conn = sqlite3.connect('aida_v11_mega.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT)')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] < 100:
        c.execute("DELETE FROM recipes") # Очистка для перезаписи
        
        # Группы рецептов
        expanded_data = [
            # BMW (Легендарные)
            ('BMW', '475', 'Black Sapphire', 'Black:496,Silver:3.2,Blue:0.8', 'Темная подложка G5.'),
            ('BMW', '300', 'Alpine White', 'White:500,Yellow:2,Blue:0.5', 'Классический солид.'),
            ('BMW', 'C1K', 'Marina Bay Blue', 'Blue_Pearl:300,Deep_Blue:150,Silver:50', 'Яркий металлик M-серии.'),
            ('BMW', '416', 'Carbon Black', 'Deep_Blue:400,Black:100,Violet:5', 'Черный с синим отливом.'),
            ('BMW', 'A96', 'Mineral White', 'White_Base:400,Fine_Pearl:40', 'Трехслойный перламутр.'),
            # AUDI / VAG
            ('AUDI', 'LY7C', 'Nardo Grey', 'White:300,Black:155,Yellow:20', '2.5 слоя. Без лака не мешать.'),
            ('AUDI', 'LS9R', 'Glacier White', 'White:450,Pearl_Blue:20,Silver:10', 'Холодный белый перламутр.'),
            ('AUDI', 'LY9B', 'Brilliant Black', 'Pure_Black:500', 'Глубокий черный солид.'),
            ('PORSCHE', 'M7Z', 'GT Silver', 'Silver_Fine:400,Black:12,Blue:3', 'Эталонное серебро.'),
            # MAZDA (Сложные)
            ('MAZDA', '46V', 'Soul Red Crystal', 'Red_Base:200,High_Chroma:150,Clear:50', 'Сложная трехслойка.'),
            ('MAZDA', '41W', 'Jet Black', 'Black:480,Blue_Xirallic:20', 'Ксираллик обязателен.'),
            ('MAZDA', '25D', 'Snowflake White', 'White:400,Pearl_Gold:30', 'Теплый перламутр.'),
            # TOYOTA / LEXUS
            ('TOYOTA', '070', 'White Crystal', 'Base:400,Pearl:35,Clear:100', 'Белая подложка обязательна.'),
            ('LEXUS', '1J7', 'Sonic Silver', 'Silver_Bright:450,Grey:30,Violet:2', 'Многослойный эффект.'),
            ('TOYOTA', '218', 'Attitude Black', 'Black:450,Blue_Pearl:40,Red_Pearl:10', 'Черный металлик.'),
        ]
        
        # Автозаполнение до 100+ позиций (вариации кодов для тестов)
        for i in range(1, 90):
            expanded_data.append(('GENERIC', f'COL-{1000+i}', f'Custom Mix {i}', f'Base:{300+i},Tint:{i*0.5}', 'Системный тестовый микс.'))
            
        c.executemany("INSERT INTO recipes (mark, code, name, components, notes) VALUES (?,?,?,?,?)", expanded_data)
    conn.commit()
    conn.close()

init_db()

# --- 3. ЛОГИКА ВХОДА ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🦾 ТЕРМИНАЛ AIDA")
    pwd = st.text_input("Введите ключ:", type="password")
    if st.button("ВХОД"):
        if pwd == "MASTER_AIDA_2026":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 4. ОСНОВНОЙ ФУНКЦИОНАЛ ---
st.sidebar.title("AIDA OS v11")
st.sidebar.write(f"База данных: **100+ рецептов**")

search = st.text_input("Поиск по МАРКЕ или КОДУ (например, BMW или 475):")

conn = sqlite3.connect('aida_v11_mega.db')
query = f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%' LIMIT 100"
df = pd.read_sql(query, conn)
conn.close()

if df.empty:
    st.warning("Ничего не найдено. Попробуйте другой код.")
else:
    for _, r in df.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="color-card">
                <div class="color-title">{r['mark']} | Код: {r['code']}</div>
                <div style="font-weight: bold; color: #94a3b8;">Название: {r['name']}</div>
                <div style="margin-top: 8px; font-size: 14px;">📝 {r['notes']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚖️ ОТКРЫТЬ КАЛЬКУЛЯТОР НАЛИВА"):
                target = st.number_input(f"Грамм для {r['code']}:", 50, 10000, 500, 50, key=f"btn_{r['id']}")
                comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
                total = sum(float(c[1]) for c in comps)
                for name, val in comps:
                    res = round(float(val) * (target / total), 1)
                    st.markdown(f'<div class="recipe-row"><span>{name}</span><span class="recipe-val">{res} г</span></div>', unsafe_allow_html=True)

