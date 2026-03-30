import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. ПРЕМЬЕР-ИНТЕРФЕЙС ---
st.set_page_config(page_title="AIDA OS | Network", page_icon="🦾", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .card { background: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .admin-badge { background: #cf222e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
    .user-msg { background: #0d1117; border-left: 3px solid #238636; padding: 8px; margin: 5px 0; font-size: 14px; }
    .recipe-val { color: #58a6ff; font-weight: bold; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- 2. ЯДРО БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('aida_v13_net.db')
    c = conn.cursor()
    # Таблица пользователей (имя уникально)
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, is_admin INTEGER DEFAULT 0)')
    # Таблица рецептов (включая кастомные)
    c.execute('''CREATE TABLE IF NOT EXISTS recipes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, mark TEXT, code TEXT, name TEXT, components TEXT, notes TEXT, is_rare INTEGER DEFAULT 0)''')
    # Общий чат
    c.execute('CREATE TABLE IF NOT EXISTS global_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, msg TEXT, time TEXT)')
    
    # Создаем админа по умолчанию
    c.execute("INSERT OR IGNORE INTO users VALUES ('тапок', 'AIDA2026', 1)")
    
    # Первичные рецепты AkzoNobel
    c.execute("SELECT COUNT(*) FROM recipes")
    if c.fetchone()[0] == 0:
        base = [
            ('Система', 'BMW', '475', 'Black Sapphire', 'Mix100:450,Mix110:30,Mix120:20', 'Akzo Standart', 0),
            ('Система', 'MAZDA', '46V', 'Soul Red Crystal', 'Base:250,Mid:150,Clear:100', 'Сложный трехслой', 1)
        ]
        c.executemany("INSERT INTO recipes (author, mark, code, name, components, notes, is_rare) VALUES (?,?,?,?,?,?,?)", base)
    conn.commit()
    conn.close()

init_db()

# --- 3. СИСТЕМА АККАУНТОВ ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def login_ui():
    st.title("🦾 ВХОД В ТЕРМИНАЛ")
    tab_log, tab_reg = st.tabs(["Вход", "Регистрация"])
    
    with tab_log:
        u = st.text_input("Имя пользователя:")
        p = st.text_input("Пароль:", type="password")
        if st.button("ВОЙТИ"):
            conn = sqlite3.connect('aida_v13_net.db')
            res = conn.cursor().execute("SELECT is_admin FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            conn.close()
            if res:
                st.session_state.user = u
                st.session_state.is_admin = bool(res[0])
                st.rerun()
            else: st.error("Неверные данные")

    with tab_reg:
        new_u = st.text_input("Придумайте имя (уникальное):")
        new_p = st.text_input("Придумайте пароль:", type="password", key="reg_p")
        if st.button("СОЗДАТЬ АККАУНТ"):
            try:
                conn = sqlite3.connect('aida_v13_net.db')
                conn.cursor().execute("INSERT INTO users (username, password) VALUES (?,?)", (new_u, new_p))
                conn.commit()
                conn.close()
                st.success("Аккаунт создан! Теперь войдите.")
            except: st.error("Это имя уже занято. Выберите другое.")

if not st.session_state.user:
    login_ui()
    st.stop()

# --- 4. ГЛАВНОЕ МЕНЮ ---
st.sidebar.title(f"👤 {st.session_state.user}")
if st.session_state.is_admin: st.sidebar.markdown('<span class="admin-badge">ADMIN ACCESS</span>', unsafe_allow_html=True)

menu = ["🧪 Лаборатория", "🛠 Добавить рецепт", "💬 Общий чат"]
if st.session_state.is_admin: menu.append("⚙️ Админ-панель")
choice = st.sidebar.radio("Меню", menu)

if st.sidebar.button("Выход"):
    st.session_state.user = None
    st.rerun()

# --- 5. ФУНКЦИОНАЛ ---
conn = sqlite3.connect('aida_v13_net.db')

if choice == "🧪 Лаборатория":
    st.subheader("Поиск по базе AkzoNobel и кастомным ТС")
    search = st.text_input("Код, марка или название:")
    df = pd.read_sql(f"SELECT * FROM recipes WHERE code LIKE '%{search}%' OR mark LIKE '%{search}%' OR name LIKE '%{search}%'", conn)
    
    for _, r in df.iterrows():
        with st.expander(f"[{r['mark']}] {r['code']} - {r['name']} {'⭐ (РЕДКОЕ)' if r['is_rare'] else ''}"):
            st.write(f"Автор: {r['author']} | Заметка: {r['notes']}")
            target = st.number_input("Вес (г):", 10, 5000, 500, 50, key=f"w_{r['id']}")
            comps = [c.split(":") for c in r['components'].split(",") if ":" in c]
            total = sum(float(c[1]) for c in comps)
            for name, val in comps:
                calc = round(float(val) * (target / total), 1)
                st.markdown(f"**{name}**: <span class='recipe-val'>{calc} г</span>", unsafe_allow_html=True)

elif choice == "🛠 Добавить рецепт":
    st.subheader("Добавление редкого ТС без кода")
    with st.form("add_form"):
        m = st.text_input("Марка ТС:")
        c = st.text_input("Код (если нет, пишем 'CUSTOM'):")
        n = st.text_input("Название (напр. 'Темная вишня металлик'):")
        comp_str = st.text_area("Компоненты через запятую (напр. Mix100:200,Mix110:50):")
        note = st.text_input("Советы по напылу:")
        rare = st.checkbox("Это редкое ТС / эксклюзив")
        if st.form_submit_button("СОХРАНИТЬ В БАЗУ"):
            conn.cursor().execute("INSERT INTO recipes (author, mark, code, name, components, notes, is_rare) VALUES (?,?,?,?,?,?,?)",
                                  (st.session_state.user, m, c, n, comp_str, note, 1 if rare else 0))
            conn.commit()
            st.success("Рецепт добавлен в общую базу!")

elif choice == "💬 Общий чат":
    st.subheader("Чат мастеров AIDA")
    msg = st.chat_input("Напишите коллегам...")
    if msg:
        conn.cursor().execute("INSERT INTO global_chat (user, msg, time) VALUES (?,?,?)",
                              (st.session_state.user, msg, datetime.now().strftime("%H:%M")))
        conn.commit()
    
    chat_df = pd.read_sql("SELECT * FROM global_chat ORDER BY id DESC LIMIT 30", conn)
    for _, m in chat_df.iterrows():
        st.markdown(f"<div class='user-msg'><b>{m['user']}</b> ({m['time']}): {m['msg']}</div>", unsafe_allow_html=True)

elif choice == "⚙️ Админ-панель" and st.session_state.is_admin:
    st.subheader("Управление пользователями")
    users_df = pd.read_sql("SELECT username, is_admin FROM users", conn)
    st.table(users_df)
    
    st.subheader("Все рецепты")
    all_rec = pd.read_sql("SELECT id, author, mark, code FROM recipes", conn)
    st.dataframe(all_rec)
    del_id = st.number_input("ID для удаления рецепта:", step=1)
    if st.button("УДАЛИТЬ"):
        conn.cursor().execute("DELETE FROM recipes WHERE id=?", (del_id,))
        conn.commit()
        st.rerun()

conn.close()


