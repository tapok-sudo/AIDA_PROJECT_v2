import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import platform
import secrets
import string
from datetime import datetime, timedelta

# --- 1. ТЕХНИЧЕСКИЕ НАСТРОЙКИ И HWID ---
def get_device_id():
    raw_id = f"{platform.node()}-{platform.processor()}-{platform.system()}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:12]

def generate_secure_key():
    chars = string.ascii_uppercase + string.digits
    return f"AIDA-{''.join(secrets.choice(chars) for _ in range(4))}-{''.join(secrets.choice(chars) for _ in range(4))}"

st.set_page_config(page_title="A.I.D.A. Core System", page_icon="🤖", layout="wide")

# --- СТИЛИЗАЦИЯ ИНТЕРФЕЙСА (TECH-STYLE) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #05070a !important; border-right: 1px solid #1f2937; }
    .stButton>button { background-color: #1f6feb; color: white; border-radius: 6px; border: none; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #388bfd; border: none; color: white; }
    .formula-card { background-color: #161b22; border-radius: 10px; padding: 18px; margin-bottom: 12px; border: 1px solid #30363d; }
    .card-header { font-size: 18px; font-weight: bold; color: #58a6ff; margin-bottom: 4px; }
    .component-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #21262d; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
conn = sqlite3.connect('aida_production_v12.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS formulas (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, model TEXT, year TEXT, code TEXT, components TEXT, notes TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS keys (license_key TEXT, owner_name TEXT, hwid TEXT, expiry_date TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS user_history (license_key TEXT, search_query TEXT, timestamp DATETIME)')
c.execute('CREATE TABLE IF NOT EXISTS user_favorites (license_key TEXT, formula_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS global_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, sender_key TEXT, message TEXT, formula_data TEXT, timestamp DATETIME)')
c.execute('CREATE TABLE IF NOT EXISTS message_likes (message_id INTEGER, user_key TEXT, UNIQUE(message_id, user_key))')
conn.commit()

# --- Вспомогательные функции ---
def get_user_status(user_key):
    likes = c.execute("SELECT COUNT(ml.message_id) FROM message_likes ml JOIN global_chat gc ON ml.message_id = gc.id WHERE gc.sender_key = ?", (user_key,)).fetchone()[0]
    if likes >= 50: return "💎 МАСТЕР-ЛЕГЕНДА", "#00d4ff"
    if likes >= 20: return "🔥 ТОП-КОЛОРИСТ", "#ff8c00"
    if likes >= 5: return "🛠 ПРОФИ", "#51cf66"   
    return "👨‍ู่ НОВИЧОК", "#8b949e"

# --- 3. АВТОРИЗАЦИЯ И ПРАВИЛА ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🤖 A.I.D.A. CORE V12.5")
    u_key = st.text_input("Введите ключ доступа:", type="password")
    if st.button("АКТИВИРОВАТЬ ЯДРО"):
        device = get_device_id()
        res = c.execute("SELECT owner_name, hwid, expiry_date FROM keys WHERE license_key = ?", (u_key,)).fetchone()
        if res:
            owner, saved_hwid, exp_str = res
            if datetime.now() > datetime.strptime(exp_str, '%Y-%m-%d'): st.error("Срок истек.")
            elif not saved_hwid or saved_hwid == device:
                c.execute("UPDATE keys SET hwid = ? WHERE license_key = ?", (device, u_key))
                conn.commit()
                st.session_state.auth, st.session_state.user, st.session_state.auth_key = True, owner, u_key
                st.rerun()
            else: st.error("Заблокировано: другое устройство.")
        else: st.error("Ключ не найден.")
    st.stop()

# --- 4. ОСНОВНОЙ ИНТЕРФЕЙС ---
u_key = st.session_state.auth_key
menu = st.sidebar.radio("МЕНЮ", ["🔍 Поиск", "💬 ОБЩИЙ ЧАТ", "🛒 Подписка", "➕ Добавить", "🔐 Админ-панель"])

# --- РАЗДЕЛ: ПОИСК ---
if menu == "🔍 Поиск":
    st.header("База рецептур DynaCoat (AkzoNobel)")
    
    with st.sidebar:
        st.write("---")
        t_hist, t_fav = st.tabs(["🕒 История", "⭐ Избранное"])
        with t_hist:
            h_df = pd.read_sql("SELECT search_query FROM user_history WHERE license_key=? ORDER BY timestamp DESC LIMIT 150", conn, params=(u_key,))
            for h in h_df['search_query']: 
                if st.button(f"🔍 {h}", key=f"h_{h}"): st.session_state.cur_s = h; st.rerun()
        with t_fav:
            f_df = pd.read_sql("SELECT f.* FROM formulas f JOIN user_favorites uf ON f.id = uf.formula_id WHERE uf.license_key=?", conn, params=(u_key,))
            for _, f_r in f_df.iterrows():
                if st.button(f"⭐ {f_r['mark']} {f_r['code']}", key=f"f_{f_r['id']}"): st.session_state.cur_s = f_r['code']; st.rerun()

    search_query = st.text_input("Поиск (марка, код, цвет):", value=st.session_state.get('cur_s', ""))
    if search_query:
        c.execute("DELETE FROM user_history WHERE license_key=? AND search_query=?", (u_key, search_query))
        c.execute("INSERT INTO user_history VALUES (?, ?, ?)", (u_key, search_query, datetime.now()))
        conn.commit()

    df = pd.read_sql("SELECT * FROM formulas", conn)
    if search_query:
        df = df[df['mark'].str.contains(search_query, case=False, na=False) | df['code'].str.contains(search_query, case=False, na=False) | df['notes'].str.contains(search_query, case=False, na=False)]
    
    for _, r in df.iterrows():
        is_fav = c.execute("SELECT 1 FROM user_favorites WHERE license_key=? AND formula_id=?", (u_key, r['id'])).fetchone()
        col_c, col_btns = st.columns([0.8, 0.2])
        with col_btns:
            if st.button("⭐" if is_fav else "☆", key=f"fav_{r['id']}"):
                if is_fav: c.execute("DELETE FROM user_favorites WHERE license_key=? AND formula_id=?", (u_key, r['id']))
                else: c.execute("INSERT INTO user_favorites VALUES (?,?)", (u_key, r['id']))
                conn.commit(); st.rerun()
            if st.button("🔗", key=f"sh_{r['id']}"):
                f_data = f"🎨 {r['mark']} {r['code']} ({r['notes']})"
                c.execute("INSERT INTO global_chat (sender, sender_key, message, formula_data, timestamp) VALUES (?,?,?,?,?)", (st.session_state.user, u_key, "Поделился формулой", f_data, datetime.now()))
                conn.commit(); st.toast("Отправлено в чат!")
with col_c:
     # Безопасный разбор компонентов    
     comps = []
     for c_i in r['components'].split(","):
         if ":" in c_i:
            p = c_i.split(":")
            comps.append(f'<div class="component-row"><span style="color:#58a6ff">{p[0]}</span> <span>{p[1]} г</span></div>')
comp_html = "".join(comps)
st.markdown(f'<div class="formula-card"><div class="card-header">{r["mark"]} {r["model"]} | {r["code"]}</div><div style="color:gray">{r["notes"]}</div>{comp_html}</div>', unsafe_allow_html=True)

# --- РАЗДЕЛ: ЧАТ ---
elif menu == "💬 ОБЩИЙ ЧАТ":
    st.header("Сообщество AIDA Dynamics")
    m_in = st.chat_input("Напишите коллегам...")
    if m_in:
        c.execute("INSERT INTO global_chat (sender, sender_key, message, timestamp) VALUES (?,?,?,?)", (st.session_state.user, u_key, m_in, datetime.now()))
        conn.commit()
        st.rerun()

    c_data = pd.read_sql("SELECT * FROM global_chat ORDER BY timestamp DESC LIMIT 50", conn)
    
    for _, m in c_data.iterrows():
        # --- ВОТ ТУТ МЫ ОПРЕДЕЛЯЕМ ИМЯ И ПРИПИСКУ ---
        display_name = m['sender']
        if m['sender'] in ["Tony Stark", "Админ", "тапок"]:
            display_name = f"👑 <span style='color:#ff4b4b; font-weight:bold;'>[ADMIN]</span> {m['sender']}"
        else:
            display_name = f"👤 {m['sender']}"
            
        with st.chat_message("user"):
            st.markdown(f"{display_name}", unsafe_allow_html=True)
            st.write(m['message'])
            
            # Кнопка удаления для админа (строка 144 вашего кода)
            if st.session_state.get('is_admin', False):
                if st.button("🗑️", key=f"del_{m['id']}"):
                    c.execute("DELETE FROM global_chat WHERE id = ?", (m['id'],))
                    conn.commit()
                    st.rerun()

# --- РАЗДЕЛ: АДМИНКА ---
elif menu == "🔐 Админ-панель":
    if st.text_input("Пароль владельца:", type="password") == "AIDA_ADMIN_2026_PRO":
        st.subheader("🏆 ЗАЛ СЛАВЫ")
        lead_df = pd.read_sql("SELECT gc.sender as Мастер, COUNT(ml.user_key) as Лайки FROM global_chat gc LEFT JOIN message_likes ml ON gc.id = ml.message_id GROUP BY gc.sender ORDER BY Лайки DESC LIMIT 5", conn)
        st.table(lead_df)
        
        st.subheader("Выпуск ключей")
        with st.form("new_key"):
            nk, no, nd = generate_secure_key(), st.text_input("Имя"), st.number_input("Дней", 1, 365, 30)
            if st.form_submit_button("Создать"):
                exp = (datetime.now() + timedelta(days=nd)).strftime('%Y-%m-%d')
                c.execute("INSERT INTO keys (license_key, owner_name, expiry_date) VALUES (?,?,?)", (nk, no, exp))
                conn.commit(); st.success(f"Ключ: {nk}")
        
        st.subheader("Управление базой")
        st.dataframe(pd.read_sql("SELECT * FROM keys", conn))
        dk = st.text_input("Ключ для удаления:")
        if st.button("Удалить"): c.execute("DELETE FROM keys WHERE license_key=?", (dk,)); conn.commit(); st.rerun()

# --- РАЗДЕЛ: ДОБАВЛЕНИЕ ---
elif menu == "➕ Добавить":
    with st.form("add_f"):
        ma, mo, co, cm, nt = st.text_input("Марка"), st.text_input("Модель"), st.text_input("Код"), st.text_area("Тонеры (400:150, 480:10)"), st.text_input("Заметки")
        if st.form_submit_button("Сохранить в базу"):
            c.execute("INSERT INTO formulas (mark, model, code, components, notes) VALUES (?,?,?,?,?)", (ma, mo, co, cm, nt))
            conn.commit(); st.success("Формула добавлена.")

# --- РАЗДЕЛ: МАГАЗИН ---
elif menu == "🛒 Подписка":
    st.header("Магазин лицензий")
    st.info(f"ID вашего устройства: {get_device_id()}")
    st.write("Цена: 7777 ₽ / 30 дней")
    st.markdown("[💳 ОПЛАТИТЬ ЧЕРЕЗ СБП](https://qr.nspk.ru/ВАШ_КОД)")
    if st.button("ПОЛУЧИТЬ КЛЮЧ ПОСЛЕ ОПЛАТЫ"):
        nk = generate_secure_key()
        exp = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        c.execute("INSERT INTO keys (license_key, owner_name, expiry_date) VALUES (?, 'Клиент_Сайта', ?)", (nk, exp))
        conn.commit(); st.success(f"Ваш ключ: {nk}")
        
# Выводим в чат с использованием unsafe_allow_html=True для работы стилей
st.markdown(f"{display_name}: {msg['text']}", unsafe_allow_html=True)
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# --- ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРА КУКИ ---
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# Проверяем, есть ли уже сохраненный ключ в браузере
saved_key = cookie_manager.get(cookie="aida_access_token")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Если нашли куку и еще не авторизованы — авторизуем автоматически
if saved_key and not st.session_state['authenticated']:
    # Тут можно добавить проверку saved_key в базе данных для безопасности
    st.session_state['authenticated'] = True
    st.session_state['user_name'] = "Tony Stark" # Или имя владельца ключа
    st.session_state['is_admin'] = True # Если это ваш ключ

# --- ОКНО ВХОДА (если куки нет или она неверна) ---
if not st.session_state['authenticated']:
    st.title("A.I.D.A. CORE: Авторизация")
    key_input = st.text_input("Введите протокол доступа:", type="password")
    
    if st.button("АКТИВИРОВАТЬ"):
        # ПРОВЕРКА КЛЮЧА В БАЗЕ (замените логику на вашу из БД)
        if key_input == "AIDA-8KCV-NP4X": 
            st.session_state['authenticated'] = True
            st.session_state['user_name'] = "Tony Stark"
            st.session_state['is_admin'] = True
            
            # СОХРАНЯЕМ КУКУ НА 30 ДНЕЙ
            cookie_manager.set("aida_access_token", key_input, expires_at=datetime.now() + timedelta(days=30))
            st.rerun()
        else:
            st.error("Доступ отклонен. Ключ не распознан.")
    st.stop()

# --- ВЕСЬ ОСТАЛЬНОЙ ИНТЕРФЕЙС НИЖЕ ---
st.success(f"Система активна. Приветствую, {st.session_state['user_name']}!")
# Убедитесь, что этот код идет СРАЗУ ПОСЛЕ строки: for msg in messages:
for msg in messages:
    # Теперь переменная 'msg' существует, и ошибки не будет
    display_name = msg['user']
    
    if msg['user'] in ["Tony Stark", "Админ", "тапок"]:
        display_name = f"👑 <span style='color:#ff4b4b; font-weight:bold;'>[ADMIN]</span> {msg['user']}"
    else:
        display_name = f"👤 {msg['user']}"
    
    # Вывод сообщения
    st.markdown(f"{display_name}: {msg['text']}", unsafe_allow_html=True)
