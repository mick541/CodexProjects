import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "content.db"

OLLAMA_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen3:4b"


def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                source TEXT,
                title TEXT,
                outline TEXT,
                article TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(materials)"
            ).fetchall()
        }

        for column in ["title", "outline", "article"]:
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE materials ADD COLUMN {column} TEXT"
                )

        connection.commit()


def get_client():
    return OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama",
    )


def generate_material(topic, source):
    prompt = f"""
Ты редактор русскоязычного канала. Подготовь интересный материал по теме.

Тема:
{topic}

Исходные данные:
{source or "нет"}

Ответь строго в следующем формате:

ЗАГОЛОВОК:
одна привлекательная строка

ПЛАН:
краткий план из 4–6 пунктов

СТАТЬЯ:
полный полезный текст на русском языке объёмом примерно 600–900 слов.
Пиши понятно, без выдуманных фактов и без упоминания этого задания.
"""

    response = get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "Ты опытный редактор и автор статей.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content


def add_material(topic, source, generated_text):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO materials
            (topic, source, title, outline, article, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                source,
                topic,
                "",
                generated_text,
                "На проверке",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        connection.commit()


def get_materials():
    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute(
            """
            SELECT id, topic, source, title, outline, article,
                   status, created_at
            FROM materials
            ORDER BY id DESC
            """
        ).fetchall()


def update_status(material_id, status):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE materials SET status = ? WHERE id = ?",
            (status, material_id),
        )
        connection.commit()


init_db()

st.set_page_config(
    page_title="Content Factory Dzen",
    page_icon="📝",
    layout="wide",
)

st.title("Content Factory Dzen")
st.caption("Локальная панель управления контентом")

st.sidebar.header("Навигация")
page = st.sidebar.radio(
    "Раздел",
    [
        "Главная",
        "Создание материала",
        "Материалы",
        "Проверка",
        "Настройки",
    ],
)

materials = get_materials()

if page == "Главная":
    st.header("Рабочая панель")

    total = len(materials)
    drafts = sum(item[6] == "Черновик" for item in materials)
    review = sum(item[6] == "На проверке" for item in materials)
    ready = sum(item[6] == "Готов" for item in materials)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Всего материалов", total)

    with col2:
        st.metric("Черновики", drafts)

    with col3:
        st.metric("На проверке", review)

    with col4:
        st.metric("Готово", ready)

    if total == 0:
        st.info("Материалов пока нет.")
    else:
        st.subheader("Последние материалы")
        for item in materials[:5]:
            st.write(f"**{item[1]}** — {item[6]} — {item[7]}")

elif page == "Создание материала":
    st.header("Создание материала")

    with st.form("new_material"):
        topic = st.text_input(
            "Тема материала",
            placeholder="Например: Как подготовить дачный участок к зиме",
        )

        source = st.text_area(
            "Исходные данные",
            placeholder="Вставьте текст, ссылки или краткое описание темы",
            height=180,
        )

        submitted = st.form_submit_button(
            "Сгенерировать материал",
            type="primary",
        )

    if submitted:
        if not topic.strip():
            st.warning("Введите тему материала.")
        else:
            with st.spinner("Локальная модель готовит материал..."):
                try:
                    generated_text = generate_material(
                        topic.strip(),
                        source.strip(),
                    )

                    add_material(
                        topic.strip(),
                        source.strip(),
                        generated_text,
                    )

                    st.success("Материал создан и отправлен на проверку.")
                    st.markdown(generated_text)

                except Exception as error:
                    st.error("Не удалось обратиться к Ollama.")
                    st.code(str(error))

elif page == "Материалы":
    st.header("Материалы")

    if not materials:
        st.info("Материалов пока нет.")
    else:
        for item in materials:
            (
                material_id,
                topic,
                source,
                title,
                outline,
                article,
                status,
                created_at,
            ) = item

            with st.expander(f"{topic} — {status}"):
                st.write(f"Создано: {created_at}")

                st.subheader("Текст материала")
                st.write(article or "Текст отсутствует")

                new_status = st.selectbox(
                    "Статус",
                    ["Черновик", "На проверке", "Готов"],
                    index=["Черновик", "На проверке", "Готов"].index(status),
                    key=f"status_{material_id}",
                )

                if new_status != status:
                    update_status(material_id, new_status)
                    st.success("Статус обновлён.")
                    st.rerun()

elif page == "Проверка":
    st.header("Проверка материалов")

    review_materials = [
        item for item in materials if item[6] == "На проверке"
    ]

    if not review_materials:
        st.info("Материалов на проверке пока нет.")
    else:
        for item in review_materials:
            st.subheader(item[1])
            st.write(item[5])

elif page == "Настройки":
    st.header("Настройки")

    st.text_input(
        "Адрес локального генератора",
        value=OLLAMA_URL,
        disabled=True,
    )

    st.text_input(
        "Используемая модель",
        value=MODEL_NAME,
        disabled=True,
    )

    st.info(
        "Генерация выполняется локально через Ollama. "
        "Подключение внешних моделей добавим позже."
    )