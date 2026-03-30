import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# --- 1. ПРЕМИАЛЬНЫЙ ДИЗАЙН И НАСТРОЙКИ ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    .stApp { background-color: #0b0f19; color: #e2e8f0; font-family: 'Roboto', sans-serif; }
    
    /* Стилизация карточек цветов */
    .color-card { background: #1e293b; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .color-title { font-size: 20px; font-weight: 700; color: #60a5fa; margin-bottom: 5px; }
    .color-badge { background: #334155; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-right: 5px; color: #cbd5e1; }
    .color-notes { font-size: 13px; color: #94a3b8; margin-top: 10px; font-style: italic; }
    
    /* Мобильные элементы */
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2563eb; border: none; color: white; font-weight: bold; padding: 12px; transition: 0.2s; }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 0 10px rgba(37, 99, 235, 0.5); }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #0f172a; color: white; border: 1px solid #334155; border-radius: 6px; padding: 10px; }
    
    /* Разделители и заголовки */
    h1, h2, h3 { color: #f8fafc; font-weight: 700; }
    hr { border-color: #334155; }
    
    /* Компоненты рецепта */
    .recipe-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; }
    .recipe-name { font-weight: 500; color: #cbd5e1; }
    .recipe-weight { font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# --- 2. МЕНЕДЖЕР СЕССИЙ (БЕЗ ВЫЛЕТОВ) ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()
cookie_manager = get_cookie_manager()

# --- 3. РАСШИРЕННАЯ БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_premium.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp DATETIME)''')
    
    # Новая структура базы рецептов (добавлены: Название, Тип, Годы, Примечания)
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, color_type TEXT, years TEXT, components TEXT, notes TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base_recipes = [
            ('BMW', '475', 'Black Sapphire', 'Металлик', '2000-2026', '4003:496.4,4700:0.2,4656:0.1', 'Двухслойный металлик. Идеально для ремонта G-серий. Требует черного грунта.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'Солид', '2013-2026', 'White:300,Black:150,Yellow:20', 'Фирменный цвет RS-серии. Глубокий глянец, наносить в 2 полных слоя.'),
            ('TOYOTA', '070', 'White Crystal', 'Перламутр (3 слоя)', '2007-2026', 'White_Base:400,Pearl_Mica:25.5,Clear:100', 'Сложная трехслойка. Внимательно следите за давлением на слое перламутра.'),
            ('MERCEDES', '197', 'Obsidian Black', 'Металлик', '1998-2026', 'Black_Deep:380,Silver_Fine:20.5,Blue:5', 'Классический черный обсидиан. Использовать стандартный разбавитель.'),
            ('LADA', '240', 'Белое Облако', 'Акриол/Солид', '2004-2026', 'White:500,Blue_Tinter:1.5', 'Базовый белый цвет. Укрывает отлично, подложка не требуется.'),
            ('MAZDA', '46G', 'Machine Grey', 'Сложный Металлик', '2016-2026', 'Black_Base:200,Liquid_Silver:150,Clear:50', 'Особая технология нанесения. Черная база, затем полупрозрачный слой серебра.'),
            ('KIA/HYUNDAI', 'PGU', 'White Crystal', 'Солид', '2010-2026', 'White:450,Yellow:2,Black:1', 'Популярный белый цвет. Возможны сильные отличия по тону в зависимости от завода (Питер/Корея).')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, color_type, years, components, notes) VALUES (?,?,?,?,?,?,?)", base_recipes)
    conn.commit()
    conn.close()

def write_log(user, action):
    try:
        conn = sqlite3.connect('aida_premium.db')
        conn.cursor().execute("INSERT INTO logs (user, action, timestamp) VALUES (?, ?, ?)", (user, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    except: pass

init_db()

# --- 4. НАДЕЖНАЯ АВТОРИЗАЦИЯ ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'admin': False})

saved_token = cookie_manager.get(cookie="aida_pro_token")
if saved_token and not st.session_state['auth']:
    if saved_token == st.secrets.get("ADMIN_CODE", "ROOT_777"): 
        st.session_state.update({'auth': True, 'user': 'АДМИНИСТРАТОР', 'admin': True})
    else:
        conn = sqlite3.connect('aida_premium.db')
        res = conn.cursor().execute("SELECT owner_name, is_admin FROM keys WHERE device_token = ?", (saved_token,)).fetchone()
        conn.close()
        if res: st.session_state.update({'auth': True, 'user': res[0], 'admin': bool(res[1])})

if not st.session_state['auth']:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>AIDA OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8;'>Профессиональная система подбора автоэмалей</p>", unsafe_allow_html=True)
    
    input_key = st.text_input("🔑 ВВЕДИТЕ КЛЮЧ АКТИВАЦИИ", type="password")
    
    if st.button("ВОЙТИ В СИСТЕМУ"):
        admin_code = st.secrets.get("ADMIN_CODE", "ROOT_777")
        if input_key == admin_code:
            cookie_manager.set("aida_pro_token", admin_code, expires_at=datetime.now() + timedelta(days=3650))
            st.rerun()
        else:
            conn = sqlite3.connect('aida_premium.db')
            c = conn.cursor()
            res = c.execute("SELECT owner_name, device_token FROM keys WHERE license_key = ?", (input_key,)).fetchone()
            if res:
                owner, token = res
                if not token:
                    new_token = str(uuid.uuid4())
                    c.execute("UPDATE keys SET device_token = ? WHERE license_key = ?", (new_token, input_key))
                    conn.commit()
                    cookie_manager.set("aida_pro_token", new_token, expires_at=datetime.now() + timedelta(days=3650))
                    st.rerun()
                else: st.error("❌ Ошибка: Ключ уже привязан к другому устройству маляра.")
            else: st.error("❌ Ошибка: Ключ не существует.")
            conn.close()
    st.stop()

# --- 5. ГЛАВНОЕ МЕНЮ И ИНТЕРФЕЙС ---
c1, c2 = st.columns([3, 1])
c1.markdown(f"👤 **Мастер:** <span style='color:#3b82f6;'>{st.session_state['user']}</span>", unsafe_allow_html=True)
if c2.button("Выход"):
    cookie_manager.delete("aida_pro_token")
    st.session_state.clear()
    st.rerun()

menu_tabs = ["🧪 Лаборатория", "💬 Чат цеха"]
if st.session_state['admin']: menu_tabs.append("⚙️ Управление")
active_tab = st.selectbox("Раздел:", menu_tabs)
st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# --- БЛОК 1: ЛАБОРАТОРИЯ (РАСШИРЕННЫЙ) ---
if active_tab == "🧪 Лаборатория":
    st.markdown("### 🔍 Поиск рецепта")
    search = st.text_input("Введите марку или код краски (например: 475 или BMW):", placeholder="Поиск...")
    
    if search:
        conn = sqlite3.connect('aida_premium.db')
        df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'", conn)
        conn.close()
        
        if df.empty:
            st.info("Формула не найдена в базе.")
        else:
            for _, r in df.iterrows():
                # Красивая карточка с информацией
                st.markdown(f"""
                <div class="color-card">
                    <div class="color-title">{r['mark']} {r['code']} — {r['name']}</div>
                    <div>
                        <span class="color-badge">🎨 {r['color_type']}</span>
                        <span class="color-badge">📅 {r['years']}</span>
                    </div>
                    <div class="color-notes">💡 {r['notes']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Калькулятор налива внутри расширителя (Expander)
                with st.expander("⚖️ Открыть калькулятор налива"):
                    target_w = st.number_input("Сколько грамм готовим?", min_value=10, max_value=5000, value=500, step=50, key=f"w_{r['id']}")
                    comps = [i.split(":") for i in r['components'].split(",") if ":" in i]
                    ratio = target_w / sum([float(i[1]) for i in comps])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    for name, val in comps:
                        calc_val = round(float(val) * ratio, 1)
                        st.markdown(f"""
                        <div class="recipe-row">
                            <span class="recipe-name">{name}</span>
                            <span class="recipe-weight">{calc_val} г</span>
                        </div>
                        """, unsafe_allow_html=True)

# --- БЛОК 2: ЧАТ ---
elif active_tab == "💬 Чат цеха":
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("Написать сообщение...")
        if st.form_submit_button("Отправить") and msg:
            conn = sqlite3.connect('aida_premium.db')
            conn.cursor().execute("INSERT INTO chat (user, message, timestamp) VALUES (?,?,?)", (st.session_state['user'], msg, datetime.now()))
            conn.commit(); conn.close()
            st.rerun()
            
    conn = sqlite3.connect('aida_premium.db')
    chat_df = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC LIMIT 40", conn)
    conn.close()
    
    for _, m in chat_df.iterrows():
        # Форматирование времени
        time_str = m['timestamp'][11:16]
        st.markdown(f"""
        <div style='background:#1e293b; padding:12px; border-radius:8px; margin-bottom:8px; border: 1px solid #334155;'>
            <div style='font-size:12px; color:#94a3b8; margin-bottom:4px;'><b>{m['user']}</b> • {time_str}</div>
            <div style='color:#e2e8f0; font-size:15px;'>{m['message']}</div>
        </div>
        """, unsafe_allow_html=True)

# --- БЛОК 3: УПРАВЛЕНИЕ (АДМИН) ---
elif active_tab == "⚙️ Управление" and st.session_state['admin']:
    t1, t2 = st.tabs(["🔑 Выдача доступов", "🗑️ Модерация чата"])
    
    with t1:
        st.markdown("### Генерация нового ключа")
        new_k = st.text_input("Придумайте ключ (например: SERVICE-01)")
        new_o = st.text_input("Кому выдаем? (Имя или название СТО)")
        if st.button("Создать и сохранить"):
            if new_k and new_o:
                try:
                    conn = sqlite3.connect('aida_premium.db')
                    conn.cursor().execute("INSERT INTO keys (license_key, owner_name) VALUES (?,?)", (new_k, new_o))
                    conn.commit(); conn.close()
                    write_log("АДМИН", f"Выдан ключ {new_k} для {new_o}")
                    st.success(f"Ключ {new_k} успешно создан! Отправьте его клиенту.")
                except: st.error("Этот ключ уже существует в базе.")
                
    with t2:
        st.markdown("### Удаление сообщений")
        conn = sqlite3.connect('aida_premium.db')
        mod_df = pd.read_sql("SELECT * FROM chat ORDER BY timestamp DESC LIMIT 30", conn)
        conn.close()
        for _, msg in mod_df.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"<span style='color:#94a3b8;'>{msg['user']}:</span> {msg['message']}", unsafe_allow_html=True)
            if c2.button("Удалить", key=f"del_{msg['id']}"):
                conn = sqlite3.connect('aida_premium.db')
                conn.cursor().execute("DELETE FROM chat WHERE id = ?", (msg['id'],))
                conn.commit(); conn.close()
                st.rerun()
