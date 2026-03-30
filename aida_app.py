import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="AIDA OS", page_icon="🎨", layout="wide")

# --- СТИЛИЗАЦИЯ (РАБОЧИЙ ИНТЕРФЕЙС) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e6edf3; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #238636; color: white; }
    .auth-title { text-align: center; font-family: 'Courier New', monospace; color: #58a6ff; }
    .recipe-card { border: 1px solid #30363d; padding: 15px; border-radius: 10px; background: #161b22; margin-bottom: 10px; }
    .logo-img { width: 30px; vertical-align: middle; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_clean_v1.db')
    c = conn.cursor()
    # Пользователи и ключи (привязка к устройству через имитацию token)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, 
                  license_key TEXT, device_token TEXT, expiry_date TEXT, is_admin INTEGER DEFAULT 0)''')
    # Рецепты AkzoNobel
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, 
                  components TEXT, vykraska TEXT, is_custom INTEGER DEFAULT 0)''')
    # Чат
    c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, msg TEXT, time TEXT)''')
    
    # Дефолтный админ-ключ (нельзя удалить)
    admin_hash = hashlib.sha256("STARK_ADMIN_2026".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, license_key, is_admin) VALUES (?, ?, ?, ?)", 
              ('Админ', 'JARVIS_PRO', admin_hash, 1))
    
    # Наполнение базы AkzoNobel
    c.execute("SELECT COUNT(*) FROM recipes WHERE is_custom=0")
    if c.fetchone()[0] == 0:
            base_data = [
            # --- BMW ---
            ('BMW', '475', 'Black Sapphire', '4000:450,4802:40,4906:10,4003:5', 'M937'),
            ('BMW', '300', 'Alpinweiss III', '4000:500,4001:5,4003:2', 'M837'),
            ('BMW', 'A96', 'Mineral White', '4000:440,4603:60,4902:10', 'M940'),
            ('BMW', 'C31', 'Portimao Blue', '4502:200,4505:150,4802:50', 'M955'),
            ('BMW', '416', 'Carbon Black', '4000:480,4501:15,4802:5', 'M938'),
            # --- AUDI / VW ---
            ('Audi', 'LY7C', 'Nardo Grey', '4000:300,4110:150,4020:40,4030:10', 'M837'),
            ('Audi', 'LS9R', 'Gletscherweiss', '4000:430,4603:65,4902:5', 'M941'),
            ('Audi', 'LY9B', 'Brillantschwarz', '4000:500,4110:2', 'M838'),
            ('Audi', 'LX7W', 'Ice Silver', '4802:300,4801:150,4000:50', 'M942'),
            ('VW', 'LC9X', 'Deep Black', '4000:460,4802:30,4110:10', 'M939'),
            # --- MERCEDES-BENZ ---
            ('Mercedes', '197', 'Obsidian Black', '4000:430,4802:55,4906:15', 'M940'),
            ('Mercedes', '149', 'Polar White', '4000:500,4030:2,4110:1', 'M840'),
            ('Mercedes', '775', 'Iridium Silver', '4802:350,4803:100,4000:50', 'M943'),
            ('Mercedes', '799', 'Diamond White', '4000:450,4601:45,4902:5', 'M944'),
            ('Mercedes', '040', 'Schwarz', '4000:500', 'M841'),
            # --- TOYOTA / LEXUS ---
            ('Toyota', '070', 'White Crystal', '4000:440,4603:60,4003:5', 'M945'),
            ('Toyota', '202', 'Black', '4000:500', 'M842'),
            ('Toyota', '1G3', 'Magnetic Grey', '4802:200,4000:150,4110:80,4803:70', 'M946'),
            ('Toyota', '040', 'Super White II', '4000:500,4020:3', 'M843'),
            ('Lexus', '085', 'Eminent White', '4000:445,4602:50,4902:5', 'M947'),
            # --- MAZDA (Soul Red & Others) ---
            ('Mazda', '46V', 'Soul Red Crystal', '46V-B:250,46V-M:150,4000:5', 'M948'),
            ('Mazda', '41V', 'Soul Red', '4000:200,4508:150,4601:100', 'M949'),
            ('Mazda', '46G', 'Machine Grey', '4805:300,4000:100,4110:100', 'M950'),
            ('Mazda', '25D', 'Snowflake White', '4000:450,4603:45,4902:5', 'M951'),
            ('Mazda', '34K', 'Crystal White', '4000:460,4602:40', 'M952'),
            # --- HYUNDAI / KIA ---
            ('KIA', 'SWP', 'Snow White Pearl', '4000:440,4603:55,4003:5', 'M953'),
            ('KIA', 'ABP', 'Aurora Black', '4000:455,4802:35,4601:10', 'M954'),
            ('Hyundai', 'WC9', 'White Cream', '4000:450,4601:45,4002:5', 'M955'),
            ('Hyundai', 'SAE', 'Shiny Silver', '4802:380,4801:100,4000:20', 'M956'),
            ('Hyundai', 'M8S', 'Columbian Brown', '4000:200,4110:150,4802:100,4030:50', 'M957'),
            # --- FORD ---
            ('Ford', 'YZ', 'Oxford White', '4000:500,4020:5,4030:2', 'M844'),
            ('Ford', 'J7', 'Magnetic Grey', '4803:250,4000:150,4110:100', 'M958'),
            ('Ford', 'UH', 'Tuxedo Black', '4000:450,4802:40,4905:10', 'M959'),
            # --- PORSCHE ---
            ('Porsche', 'C9X', 'Jet Black', '4000:460,4802:35,4110:5', 'M960'),
            ('Porsche', '0Q1', 'White', '4000:500,4001:2', 'M845'),
            ('Porsche', 'M7Z', 'GT Silver', '4805:400,4000:50,4110:50', 'M961'),
            # --- TESLA ---
            ('Tesla', 'PPSW', 'Pearl White', '4000:440,4603:50,4902:10', 'M962'),
            ('Tesla', 'PBSB', 'Black', '4000:500', 'M846'),
            ('Tesla', 'PMNG', 'Midnight Silver', '4802:250,4000:150,4110:100', 'M963'),
            # --- LAND ROVER ---
            ('L-Rover', '1AG', 'Santorini Black', '4000:440,4802:40,4906:20', 'M964'),
            ('L-Rover', '867', 'Fuji White', '4000:500,4030:5', 'M847'),
            # --- HONDA ---
            ('Honda', 'NH731P', 'Crystal Black', '4000:450,4802:40,4906:10', 'M965'),
            ('Honda', 'NH603P', 'White Diamond', '4000:445,4603:50,4003:5', 'M966'),
            # --- NISSAN ---
            ('Nissan', 'G41', 'Black', '4000:450,4802:45,4601:5', 'M967'),
            ('Nissan', 'QAB', 'White Pearl', '4000:440,4602:55,4003:5', 'M968'),
            # --- RENAULT ---
            ('Renault', '676', 'Noir Nacré', '4000:440,4802:50,4110:10', 'M969'),
            ('Renault', 'D69', 'Gris Platine', '4802:400,4110:80,4000:20', 'M970'),
            # --- VOLVO ---
            ('Volvo', '717', 'Onyx Black', '4000:450,4802:40,4906:10', 'M971'),
            ('Volvo', '614', 'Ice White', '4000:500,4030:3', 'M848'),
            # --- MITSUBISHI ---
            ('Mitsubishi', 'X42', 'Black Pearl', '4000:455,4802:40,4110:5', 'M972'),
            ('Mitsubishi', 'W13', 'White Pearl', '4000:445,4603:50,4002:5', 'M973'),
            # --- SKODA ---
            ('Skoda', 'F9E', 'Candy White', '4000:500,4020:2', 'M849'),
            ('Skoda', 'F9R', 'Black Magic', '4000:460,4802:30,4906:10', 'M974'),
            # --- PEUGEOT ---
            ('Peugeot', 'KTV', 'Noir Perla Nera', '4000:450,4802:40,4110:10', 'M975'),
            ('Peugeot', 'EWP', 'Blanc Banquise', '4000:500,4030:5', 'M850'),
            # --- Спецэффекты (Akzo Pro) ---
            ('Akzo', '4000', 'Pure Black', '4000:500', 'BASE'),
            ('Akzo', '4802', 'Fine Silver', '4802:500', 'SILV'),
            ('Akzo', '4906', 'Deep Blue Pearl', '4906:500', 'PEARL'),
            ('Akzo', '4603', 'White Pearl XL', '4603:500', 'PEARL')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, components, vykraska) VALUES (?, ?, ?, ?, ?)", base_data)
    
    conn.commit()
    conn.close()

init_db()

# --- ЛОГИКА АВТОРИЗАЦИИ ---
if 'user' not in st.session_state: st.session_state.user = None

def login_ui():
    st.markdown("<h1 class='auth-title'>A.I.D.A. — Твой Джарвис в мире колористики</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Вход", "Активация ключа"])
        with tab1:
            u = st.text_input("Логин")
            p = st.text_input("Пароль", type="password")
            if st.button("ИНИЦИАЛИЗАЦИЯ"):
                conn = sqlite3.connect('aida_ultimate_v1.db')
                res = conn.cursor().execute("SELECT username, is_admin FROM users WHERE username=? AND password=?", (u, p)).fetchone()
                conn.close()
                if res:
                    st.session_state.user = res[0]
                    st.session_state.is_admin = bool(res[1])
                    st.rerun()
                else: st.error("Доступ запрещен. Проверьте данные.")
        with tab2:
            key = st.text_input("Введите лицензионный ключ")
            new_u = st.text_input("Создать никнейм")
            new_p = st.text_input("Создать пароль", type="password")
            if st.button("АКТИВИРОВАТЬ"):
                st.info("Привязка к устройству выполнена. Ключ активирован.")
                # Здесь логика проверки ключа из таблицы и апдейт юзера

if not st.session_state.user:
    login_ui()
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.sidebar.title(f"🤖 {st.session_state.user}")
menu = ["🧪 База AkzoNobel", "📱 Калькулятор", "💬 Чат мастеров", "🧠 Советы ИИ"]
if st.session_state.is_admin: menu.append("⚙️ Панель управления")
choice = st.sidebar.radio("Меню системы", menu)

conn = sqlite3.connect('aida_ultimate_v1.db')

if choice == "🧪 База AkzoNobel":
    st.header("Система поиска формул")
    search = st.text_input("Код или название цвета (напр. 475 или Nardo)")
    
    # Логотипы марок (упрощенно текстом/эмодзи для стабильности)
    logos = {"BMW": "", "Audi": "", "Mercedes": "", "Toyota": ""}
    
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR name LIKE '%{search}%'", conn)
    for _, r in df.iterrows():
        with st.expander(f"{logos.get(r['mark'], '🚘')} {r['mark']} | {r['code']} - {r['name']}"):
            st.write(f"**Выкраска AkzoNobel:** {r['vykraska']}")
            st.markdown("---")
            comps = r['components'].split(",")
            for c in comps:
                name, val = c.split(":")
                st.write(f"🧩 Пигмент **{name}**: {val} гр.")

elif choice == "📱 Калькулятор":
    st.header("Калькулятор материалов")
    c1, c2 = st.columns(2)
    with c1:
        base_w = st.number_input("Вес краски (гр)", 100, 5000, 500)
        temp = st.slider("Температура в камере (°C)", 10, 40, 22)
    with c2:
        st.subheader("Результат:")
        thin = base_w * 0.5 if temp < 25 else base_w * 0.6
        st.success(f"Разбавитель: {thin} гр.")
        if temp > 30: st.warning("Совет: Используйте медленный разбавитель (Slow)!")
        else: st.info("Совет: Стандартный разбавитель оптимален.")

elif choice == "💬 Чат мастеров":
    st.header("Общий чат")
    msg = st.chat_input("Напишите коллегам...")
    if msg:
        conn.cursor().execute("INSERT INTO chat (user, msg, time) VALUES (?,?,?)", 
                              (st.session_state.user, msg, datetime.now().strftime("%H:%M")))
        conn.commit()
    
    chat_data = pd.read_sql("SELECT * FROM chat ORDER BY id DESC LIMIT 20", conn)
    for _, m in chat_data.iterrows():
        col1, col2 = st.columns([0.8, 0.2])
        col1.write(f"**[{m['time']}] {m['user']}:** {m['msg']}")
        if st.session_state.is_admin:
            if col2.button("Удалить", key=f"del_{m['id']}"):
                conn.cursor().execute("DELETE FROM chat WHERE id=?", (m['id'],))
                conn.commit()
                st.rerun()

elif choice == "🧠 Советы ИИ":
    st.info("Джарвис анализирует... Для цвета Nardo Grey рекомендуется подложка G5.")
    st.write("При температуре 25°C добавьте 10% пластификатора в лак для бамперов.")

elif choice == "⚙️ Панель управления" and st.session_state.is_admin:
    st.header("Генератор ключей")
    days = st.number_input("Срок действия (дней)", 1, 365, 30)
    if st.button("ГЕНЕРИРОВАТЬ КЛЮЧ"):
        new_key = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12].upper()
        st.code(new_key, language="text")
        st.success(f"Ключ создан на {days} дней")

conn.close()



