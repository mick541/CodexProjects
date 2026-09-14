import json
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

from quality_control import (
    format_quality_report,
    run_quality_control,
)


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "content.db"

OLLAMA_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen3:4b"

STATUS_DRAFT = "Черновик"
STATUS_REVIEW = "На проверке"
STATUS_READY = "Готов"

MIN_WORDS = 850
MAX_WORDS = 1200


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

        extra_columns = {
            "seo_brief": "TEXT",
            "quality_report": "TEXT",
        }

        for column, column_type in extra_columns.items():
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE materials "
                    f"ADD COLUMN {column} {column_type}"
                )

        connection.commit()


def get_client():
    return OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama",
    )


def call_model(prompt, temperature=0.4):
    response = get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты опытный редактор, SEO-аналитик и фактчекер. "
                    "Отвечай на русском языке."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content


def extract_json(text):
    text = (text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Модель не вернула JSON-структуру."
        )

    return json.loads(text[start:end + 1])


def run_seo_research(topic, source, audience):
    prompt = f"""
Проведи SEO-исследование перед написанием статьи.

Тема:
{topic}

Исходные данные:
{source or "нет"}

Целевая аудитория:
{audience or "широкая русскоязычная аудитория"}

Верни только корректный JSON без Markdown:

{{
  "primary_query": "один основной поисковый запрос",
  "secondary_queries": [
    "дополнительный запрос 1",
    "дополнительный запрос 2",
    "дополнительный запрос 3",
    "дополнительный запрос 4",
    "дополнительный запрос 5"
  ],
  "search_intent": "краткое описание намерения читателя",
  "reader_questions": [
    "вопрос 1",
    "вопрос 2",
    "вопрос 3"
  ],
  "outline": [
    "раздел 1",
    "раздел 2",
    "раздел 3",
    "раздел 4",
    "раздел 5"
  ],
  "title_options": [
    "вариант заголовка 1",
    "вариант заголовка 2",
    "вариант заголовка 3"
  ],
  "fact_risks": [
    "какие утверждения потребуют источников"
  ],
  "related_topics": [
    "связанная тема 1",
    "связанная тема 2"
  ]
}}

Не используй кликбейт. Запросы должны соответствовать теме,
а не быть случайным набором популярных слов.
"""

    return extract_json(call_model(prompt, temperature=0.2))


def generate_article(topic, source, audience, seo_brief):
    prompt = f"""
Создай полезную русскоязычную статью.

Тема:
{topic}

Исходные данные:
{source or "нет"}

Целевая аудитория:
{audience or "широкая русскоязычная аудитория"}

SEO-БРИФ:
{json.dumps(seo_brief, ensure_ascii=False, indent=2)}

Требования:

1. Объём основного текста: от {MIN_WORDS} до {MAX_WORDS} слов.
2. Используй основной поисковый запрос естественно.
3. Используй дополнительные запросы только там, где это уместно.
4. Не повторяй ключевые фразы механически.
5. Заголовок должен точно соответствовать содержанию.
6. Не используй кликбейт, неподтверждённые сенсации и пустые обещания.
7. Не выдумывай цифры, даты, имена и ссылки.
8. Если утверждение нельзя подтвердить исходными данными,
   сформулируй его осторожно или укажи, что нужна проверка.
9. Добавь понятное введение, подзаголовки, практические шаги
   и заключение.
10. Не упоминай это задание, SEO-бриф или модель.

Верни строго в формате:

ЗАГОЛОВОК:
одна строка

СТАТЬЯ:
полный текст статьи
"""

    return call_model(prompt, temperature=0.6)


def improve_article(
    title,
    article,
    seo_brief,
    quality_report,
):
    prompt = f"""
Доработай статью после автоматической проверки.

Заголовок:
{title}

Текущая статья:
{article}

SEO-БРИФ:
{json.dumps(seo_brief, ensure_ascii=False, indent=2)}

ОТЧЁТ ПРОВЕРКИ:
{quality_report}

Требования:

- итоговый объём: от {MIN_WORDS} до {MAX_WORDS} слов;
- сохрани полезную фактическую информацию;
- исправь замечания проверки;
- убери подозрительные и чрезмерно категоричные формулировки;
- проверь соответствие заголовка содержанию;
- используй поисковые запросы естественно;
- не добавляй непроверенные цифры, даты и факты;
- не используй кликбейт.

Верни строго в формате:

ЗАГОЛОВОК:
одна строка

СТАТЬЯ:
полный исправленный текст
"""

    return call_model(prompt, temperature=0.4)


def add_material(
    topic,
    source,
    title,
    article,
    seo_brief,
):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO materials
            (topic, source, title, outline, article, status,
             created_at, seo_brief, quality_report)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                source,
                title,
                json.dumps(
                    seo_brief.get("outline", []),
                    ensure_ascii=False,
                ),
                article,
                STATUS_REVIEW,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                json.dumps(
                    seo_brief,
                    ensure_ascii=False,
                ),
                "",
            ),
        )
        connection.commit()


def get_materials():
    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute(
            """
            SELECT id, topic, source, title, outline, article,
                   status, created_at, seo_brief, quality_report
            FROM materials
            ORDER BY id DESC
            """
        ).fetchall()


def update_material(
    material_id,
    title,
    article,
    status=None,
    quality_report=None,
):
    fields = [
        "title = ?",
        "article = ?",
    ]

    values = [
        title,
        article,
    ]

    if status is not None:
        fields.append("status = ?")
        values.append(status)

    if quality_report is not None:
        fields.append("quality_report = ?")
        values.append(quality_report)

    values.append(material_id)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            f"""
            UPDATE materials
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values,
        )
        connection.commit()


def update_status(material_id, status):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE materials
            SET status = ?
            WHERE id = ?
            """,
            (status, material_id),
        )
        connection.commit()


def parse_generated_article(text):
    text = text or ""

    if "ЗАГОЛОВОК:" in text and "СТАТЬЯ:" in text:
        title_part, article_part = text.split(
            "СТАТЬЯ:",
            1,
        )

        title = title_part.replace(
            "ЗАГОЛОВОК:",
            "",
        ).strip()

        article = article_part.strip()

        return title, article

    return "", text.strip()


def get_seo_brief(item):
    raw_brief = item[8]

    if not raw_brief:
        return {}

    try:
        return json.loads(raw_brief)
    except json.JSONDecodeError:
        return {}


def run_quality_for_item(item):
    material_id = item[0]
    topic = item[1]
    title = item or topic[3]
    article = item or ""[5]
    seo_brief = get_seo_brief(item)

    report = run_quality_control(
        title=title,
        text=article,
        primary_query=seo_brief.get(
            "primary_query",
            topic,
        ),
        secondary_queries=seo_brief.get(
            "secondary_queries",
            [],
        ),
        related_topics=seo_brief.get(
            "related_topics",
            [],
        ),
        claims=[],
    )

    report_text = format_quality_report(report)

    update_material(
        material_id=material_id,
        title=title,
        article=article,
        quality_report=report_text,
    )

    return report, report_text


def render_quality_check(item):
    (
        material_id,
        topic,
        source,
        title,
        outline,
        article,
        status,
        created_at,
        seo_brief_raw,
        quality_report,
    ) = item

    title = title or topic
    article = article or ""

    st.subheader(title)
    st.caption(f"Тема: {topic} | Создано: {created_at}")

    if st.button(
        "Запустить проверку",
        key=f"run_quality_{material_id}",
        type="primary",
    ):
        with st.spinner("Проверяем материал..."):
            try:
                report, report_text = run_quality_for_item(item)

                st.session_state[
                    f"report_{material_id}"
                ] = report_text

                st.session_state[
                    f"report_data_{material_id}"
                ] = report

            except Exception as error:
                st.error("Не удалось выполнить проверку.")
                st.code(str(error))

    report_text = st.session_state.get(
        f"report_{material_id}",
        quality_report or "",
    )

    report_data = st.session_state.get(
        f"report_data_{material_id}",
        None,
    )

    if report_text:
        st.text(report_text)

    if report_data:
        if report_data["passed"]:
            st.success("Материал прошёл автоматическую проверку.")
        else:
            st.warning(
                "Материал требует редакторской доработки."
            )

        if st.button(
            "Доработать статью",
            key=f"improve_{material_id}",
        ):
            seo_brief = get_seo_brief(item)

            with st.spinner(
                "Модель дорабатывает статью..."
            ):
                try:
                    improved = improve_article(
                        title=title,
                        article=article,
                        seo_brief=seo_brief,
                        quality_report=report_text,
                    )

                    improved_title, improved_article = (
                        parse_generated_article(improved)
                    )

                    if improved_title:
                        title = improved_title

                    update_material(
                        material_id=material_id,
                        title=title,
                        article=improved_article,
                        status=STATUS_REVIEW,
                        quality_report="",
                    )

                    st.success(
                        "Статья доработана. Запустите проверку повторно."
                    )
                    st.rerun()

                except Exception as error:
                    st.error(
                        "Не удалось доработать статью."
                    )
                    st.code(str(error))


init_db()

st.set_page_config(
    page_title="Content Factory Dzen",
    page_icon="📄",
    layout="wide",
)

st.title("Content Factory Dzen")
st.caption(
    "Подготовка материалов через SEO-исследование и редакторскую проверку"
)

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
    drafts = sum(
        item == STATUS_DRAFT[6]
        for item in materials
    )
    review = sum(
        item == STATUS_REVIEW[6]
        for item in materials
    )
    ready = sum(
    item[6] == STATUS_READY
    for item in materials
)
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Всего материалов", total)

    with col2:
        st.metric("Черновики", drafts)

    with col3:
        st.metric("На проверке", review)

    with col4:
        st.metric("Готово", ready)

    if total:
        st.subheader("Последние материалы")

        for item in materials[:5]:
            st.write(
                f"**{item[3] or item[1]}** — {item[6]} — {item[7]}"
                f"{item} — {item}"[6][7]
            )
    else:
        st.info("Материалов пока нет.")

elif page == "Создание материала":
    st.header("Создание материала")

    topic = st.text_input(
        "Тема материала",
        placeholder=(
            "Например: как выбрать зимние шины"
        ),
    )

    audience = st.text_input(
        "Целевая аудитория",
        placeholder=(
            "Например: начинающие автовладельцы"
        ),
    )

    source = st.text_area(
        "Исходные данные",
        placeholder=(
            "Вставьте факты, ссылки или описание темы"
        ),
        height=180,
    )

    if st.button(
        "1. Провести SEO-исследование",
        type="primary",
    ):
        if not topic.strip():
            st.warning("Введите тему материала.")
        else:
            with st.spinner(
                "Проводим SEO-исследование..."
            ):
                try:
                    st.session_state["seo_brief"] = (
                        run_seo_research(
                            topic=topic.strip(),
                            source=source.strip(),
                            audience=audience.strip(),
                        )
                    )

                    st.session_state[
                        "research_topic"
                    ] = topic.strip()

                    st.session_state[
                        "research_source"
                    ] = source.strip()

                    st.session_state[
                        "research_audience"
                    ] = audience.strip()

                except Exception as error:
                    st.error(
                        "Не удалось выполнить SEO-исследование."
                    )
                    st.code(str(error))

    seo_brief = st.session_state.get(
        "seo_brief",
        None,
    )

    if seo_brief:
        st.subheader("SEO-бриф")

        primary_query = st.text_input(
            "Основной поисковый запрос",
            value=seo_brief.get(
                "primary_query",
                "",
            ),
        )

        search_intent = st.text_area(
            "Поисковый интент",
            value=seo_brief.get(
                "search_intent",
                "",
            ),
        )

        secondary_text = st.text_area(
            "Дополнительные запросы — по одному в строке",
            value="\n".join(
                seo_brief.get(
                    "secondary_queries",
                    [],
                )
            ),
        )

        outline_text = st.text_area(
            "План статьи — по одному разделу в строке",
            value="\n".join(
                seo_brief.get(
                    "outline",
                    [],
                )
            ),
        )

        titles_text = st.text_area(
            "Варианты заголовка — по одному в строке",
            value="\n".join(
                seo_brief.get(
                    "title_options",
                    [],
                )
            ),
        )

        if st.button(
            "2. Сгенерировать статью 850–1200 слов",
            type="primary",
        ):
            final_brief = dict(seo_brief)

            final_brief["primary_query"] = primary_query

            final_brief["search_intent"] = search_intent

            final_brief["secondary_queries"] = [
                line.strip()
                for line in secondary_text.splitlines()
                if line.strip()
            ]

            final_brief["outline"] = [
                line.strip()
                for line in outline_text.splitlines()
                if line.strip()
            ]

            final_brief["title_options"] = [
                line.strip()
                for line in titles_text.splitlines()
                if line.strip()
            ]

            with st.spinner(
                "Готовим статью..."
            ):
                try:
                    generated = generate_article(
                        topic=st.session_state[
                            "research_topic"
                        ],
                        source=st.session_state[
                            "research_source"
                        ],
                        audience=st.session_state[
                            "research_audience"
                        ],
                        seo_brief=final_brief,
                    )

                    generated_title, generated_article = (
                        parse_generated_article(
                            generated
                        )
                    )

                    if not generated_title:
                        generated_title = (
                            final_brief.get(
                                "title_options",
                                [topic],
                            )[0]
                        )

                    add_material(
                        topic=st.session_state[
                            "research_topic"
                        ],
                        source=st.session_state[
                            "research_source"
                        ],
                        title=generated_title,
                        article=generated_article,
                        seo_brief=final_brief,
                    )

                    st.success(
                        "Статья создана и отправлена на проверку."
                    )

                    st.subheader(generated_title)
                    st.write(generated_article)

                except Exception as error:
                    st.error(
                        "Не удалось создать статью."
                    )
                    st.code(str(error))

elif page == "Материалы":
    st.header("Материалы")

    if not materials:
        st.info("Материалов пока нет.")
    else:
        for item in materials:
            material_id = item[0]
            title = item or item[1][3]
            status = item[6]

            with st.expander(
                f"{title} — {status}"
            ):
                st.caption(
                    f"Создано: {item}"[7]
                )
                st.write(
                    item or "Текст отсутствует"[5]
                )

                statuses = [
                    STATUS_DRAFT,
                    STATUS_REVIEW,
                    STATUS_READY,
                ]

                new_status = st.selectbox(
                    "Статус",
                    statuses,
                    index=(
                        statuses.index(status)
                        if status in statuses
                        else 0
                    ),
                    key=f"status_{material_id}",
                )

                if new_status != status:
                    update_status(
                        material_id,
                        new_status,
                    )
                    st.success(
                        "Статус обновлён."
                    )
                    st.rerun()

elif page == "Проверка":
    st.header("Проверка материалов")

    review_materials = [
        item for item in materials
        if item == STATUS_REVIEW[6]
    ]

    if not review_materials:
        st.info(
            "Материалов на проверке пока нет."
        )
    else:
        for item in review_materials:
            render_quality_check(item)

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
        "Генерация выполняется локально через Ollama."
    )