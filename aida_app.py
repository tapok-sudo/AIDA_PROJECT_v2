import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import uuid

# --- 1. ПРЕМИАЛЬНЫЙ СТИЛЬ И НАСТРОЙКИ ---
st.set_page_config(page_title="AIDA OS", page_icon="🦾", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .color-card { background: #1e293b; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .color-title { font-size: 24px; font-weight: 800; color: #60a5fa; }
    .recipe-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; }
    .recipe-val { font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 18px; }
    .stButton>button { width: 100%; border-radius: 6px; background-color: #2563eb; color: white; border: none; font-weight: bold; padding: 10px; }
    .stButton>button:hover { background-color: #1d4ed8; }
    .chat-msg { background: #334155; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #fbbf24; }
    .chat-user { font-weight: bold; color: #fbbf24; font-size: 0.85em; margin-bottom: 5px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- 2. УПРАВЛЕНИЕ СЕССИЕЙ ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'admin': False})

# --- 3. ИНИЦИАЛИЗАЦИЯ БАЗЫ (БЕЗ ОШИБОК) ---
def init_db():
    conn = sqlite3.connect('aida_v7_ultimate.db') # Новое имя гарантирует чистый старт
    c = conn.cursor()
    
    # Таблица доступа
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (license_key TEXT PRIMARY KEY, owner_name TEXT, device_token TEXT, is_admin INTEGER DEFAULT 0)''')
    
    # Резервный Мастер-Ключ для вас
    c.execute("INSERT OR IGNORE INTO keys (license_key, owner_name, device_token, is_admin) VALUES ('MASTER_AIDA_2026', 'ADMIN', 'MASTER_TOKEN', 1)")
    
    # Таблица рецептов
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mark TEXT, code TEXT, name TEXT, type TEXT, years TEXT, components TEXT, notes TEXT)''')
    
    # Таблица чата
    c.execute('''CREATE TABLE IF NOT EXISTS chat 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, message TEXT, timestamp DATETIME)''')

    # Заполнение базы премиум-цветами
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base = [
            ('BMW', '475', 'Black Sapphire', 'Metallic', '2000-2026', '4003:496.4,4700:0.2,4656:0.1', 'Глубокий черный. Использовать темный грунт G5.'),
            ('AUDI', 'LY7C', 'Nardo Grey', 'Solid', '2013-2026', 'White:300.5,Black:150.2,Yellow:20.0', 'Легендарный серый. Наносить в 2.5 слоя.'),
            ('TOYOTA', '070', 'White Crystal', 'Pearl (3-Stage)', '2010-2026', 'Base:400,Pearl:25.5,Clear:100', 'Трехслойное покрытие. Важен контроль давления.'),
            ('MAZDA', '46V', 'Soul Red Crystal', 'Candy Metallic', '2017-2026', 'Red_Base:200,High_Bright:150', 'Сложный цвет. Требует специальной подложки.'),
            ('PORSCHE', 'M7Z', 'GT Silver', 'Metallic', '2004-2026', 'Fine_Silver:400,Black:10,Blue:2', 'Чистое серебро. Избегать «яблок» при распыле.')
        ]
        c.executemany("INSERT INTO recipes (mark, code, name, type, years, components, notes) VALUES (?,?,?,?,?,?,?)", base)
    conn.commit()
    conn.close()

init_db()

# --- 4. ЛОГИКА АВТОРИЗАЦИИ (ЗАЩИТА ОТ ВЗЛОМА) ---
token = cookie_manager.get(cookie="aida_token")

if token and not st.session_state.auth:
    conn = sqlite3.connect('aida_v7_ultimate.db')
    res = conn.cursor().execute("SELECT owner_name, is_admin FROM keys WHERE device_token = ?", (token,)).fetchone()
    conn.close()
    if res:
        st.session_state.update({'auth': True, 'user': res[0], 'admin': bool(res[1])})

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #60a5fa;'>🦾 AIDA TERMINAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8;'>Доступ ограничен. Подтвердите устройство.</p>", unsafe_allow_html=True)
    
    key = st.text_input("ВВЕДИТЕ ЛИЦЕНЗИОННЫЙ КЛЮЧ", type="password")
    if st.button("АВТОРИЗАЦИЯ"):
        conn = sqlite3.connect('aida_v7_ultimate.db')
        c = conn.cursor()
        res = c.execute("SELECT owner_name, device_token FROM keys WHERE license_key = ?", (key,)).fetchone()
        
        if res:
            if not res[1]: # Токена нет, привязываем
                new_token = str(uuid.uuid4())
                c.execute("UPDATE keys SET device_token = ? WHERE license_key = ?", (new_token, key))
                conn.commit()
                cookie_manager.set("aida_token", new_token, expires_at=datetime.now()+timedelta(days=365))
                st.success("Устройство успешно привязано! Нажмите F5 или обновите страницу.")
            else:
                st.error("Отказано. Этот ключ уже активирован на другом устройстве.")
        elif key == "MASTER_AIDA_2026": # Резервный вход для вас
            cookie_manager.set("aida_token", "MASTER_TOKEN", expires_at=datetime.now()+timedelta(days=365))
            st.success("Доступ подтвержден. Нажмите F5 или обновите страницу.")
        else:
            st.error("Неверный ключ доступа.")
        conn.close()
    st.stop()

# --- 5. ГЛАВНЫЙ ИНТЕРФЕЙС ---
st.sidebar.title("🦾 AIDA OS")
st.sidebar.markdown(f"**Пользователь:** <span style='color:#60a5fa;'>{st.session_state.user}</span>", unsafe_allow_html=True)

if st.sidebar.button("Выйти из системы"):
    cookie_manager.delete("aida_token")
    st.session_state.auth = False
    st.rerun()

menu = ["🧪 Лаборатория", "💬 Чат цеха"]
if st.session_state.admin:
    menu.append("⚙️ Панель управления")

page = st.sidebar.radio("Навигация:", menu)

# --- РАЗДЕЛ: ЛАБОРАТОРИЯ ---
if page == "🧪 Лаборатория":
    st.title("База рецептов")
    search = st.text_input("Поиск по коду или марке (например: 475 или AUDI):")
    
    conn = sqlite3.connect('aida_v7_ultimate.db')
    query = f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%'"
    df = pd.read_sql(query, conn)
    conn.close()

    for _, r in df.iterrows():
        st.markdown(f"""
        <div class="color-card">
            <div class="color-title">{r['mark']} {r['code']}</div>
            <div style="color: #94a3b8; font-size: 14px; margin-bottom: 10px;">{r['name']} | {r['type']} | {r['years']}</div>
            <div style="background: #0f172a; padding: 10px; border-radius: 5px; border-left: 3px solid #3b82f6; font-size: 14px;">
                📝 {r['notes']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("⚖️ РАССЧИТАТЬ НАЛИВ (ГРАММЫ)"):
            target = st.number_input("Общий вес (грамм):", min_value=10, max_value=5000, value=500, step=10, key=f"w_{r['id']}")
            comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
            total_parts = sum([float(c[1]) for c in comps])
            
            for c_name, c_val in comps:
                res_w = round(float(c_val) * (target / total_parts), 1)
                st.markdown(f'<div class="recipe-row"><span style="color: #cbd5e1;">{c_name}</span><span class="recipe-val">{res_w} г</span></div>', unsafe_allow_html=True)

# --- РАЗДЕЛ: ЧАТ ---
elif page == "💬 Чат цеха":
    st.title("Связь")
    conn = sqlite3.connect('aida_v7_ultimate.db')
    
    new_msg = st.chat_input("Написать в общий канал...")
    if new_msg:
        conn.cursor().execute("INSERT INTO chat (user, message, timestamp) VALUES (?,?,?)", 
                              (st.session_state.user, new_msg, datetime.now().strftime("%H:%M | %d.%m.%Y")))
        conn.commit()
        st.rerun()
        
    df_chat = pd.read_sql("SELECT * FROM chat ORDER BY id DESC LIMIT 30", conn)
    conn.close()
    
    if df_chat.empty:
        st.info("Сообщений пока нет.")
    else:
        for _, msg in df_chat.iterrows():
            st.markdown(f"""
            <div class="chat-msg">
                <div class="chat-user">{msg['user']} <span style="color: #64748b; font-size: 0.8em; font-weight: normal; margin-left: 10px;">{msg['timestamp']}</span></div>
                <div style="color: #f8fafc; font-size: 15px;">{msg['message']}</div>
            </div>
            """, unsafe_allow_html=True)

# --- РАЗДЕЛ: АДМИН ---
elif page == "⚙️ Панель управления" and st.session_state.admin:
    st.title("Центр управления")
    
    with st.form("new_key_form"):
        st.subheader("Выпуск нового ключа")
        new_k = st.text_input("Придумайте ключ (например: IVAN_2026)")
        new_o = st.text_input("Имя сотрудника")
        is_adm = st.checkbox("Выдать права администратора")
        submitted = st.form_submit_button("Создать доступ")
        
        if submitted and new_k and new_o:
            conn = sqlite3.connect('aida_v7_ultimate.db')
            try:
                conn.cursor().execute("INSERT INTO keys (license_key, owner_name, is_admin) VALUES (?,?,?)", 
                                      (new_k, new_o, 1 if is_adm else 0))
                conn.commit()
                st.success(f"Ключ {new_k} для {new_o} успешно создан!")
            except sqlite3.IntegrityError:
                st.error("Ошибка: Такой ключ уже существует.")
            conn.close()
            
    st.subheader("Активные устройства")
    conn = sqlite3.connect('aida_v7_ultimate.db')
    df_keys = pd.read_sql("SELECT license_key, owner_name, is_admin, CASE WHEN device_token IS NOT NULL THEN 'Да' ELSE 'Нет' END as "Привязан" FROM keys", conn)
    conn.close()
    st.dataframe(df_keys, use_container_width=True)

