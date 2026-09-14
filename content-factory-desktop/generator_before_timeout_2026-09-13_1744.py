from openai import OpenAI


OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen3:4b"


def get_client(base_url=OLLAMA_URL):
    return OpenAI(
        base_url=base_url,
        api_key="ollama",
    )


def build_prompt(
    pool_name,
    pool_description,
    audience,
    style_requirements,
    topic,
    article_type,
    search_intent,
    primary_query,
    secondary_queries,
    source_text,
):
    return f"""
Ты работаешь как редактор качественного русскоязычного медиа.

Твоя задача — создать полезный, понятный и проверяемый черновик статьи.
Не выдумывай факты, цифры, исследования, цитаты, названия организаций
или медицинские сведения. Если данных недостаточно, укажи, что именно
нужно проверить.

ПУЛ:
{pool_name}

ОБЩЕЕ ОПИСАНИЕ ПУЛА:
{pool_description or "не указано"}

АУДИТОРИЯ:
{audience or "широкая аудитория"}

ОБЩИЕ ТРЕБОВАНИЯ К СТИЛЮ:
{style_requirements or "ясный научно-популярный или практический стиль"}

КОНКРЕТНАЯ ТЕМА:
{topic}

ТИП СТАТЬИ:
{article_type or "информационная статья"}

ПОИСКОВОЕ НАМЕРЕНИЕ:
{search_intent or "информационное"}

ОСНОВНОЙ ПОИСКОВЫЙ ЗАПРОС:
{primary_query or "не указан"}

ДОПОЛНИТЕЛЬНЫЕ ЗАПРОСЫ:
{secondary_queries or "не указаны"}

ИСХОДНЫЕ ДАННЫЕ:
{source_text or "не указаны"}

ТРЕБОВАНИЯ К РЕЗУЛЬТАТУ:

1. Сначала предложи точный заголовок без кликбейта.
2. Затем составь краткое содержание статьи.
3. После этого напиши основной текст с подзаголовками.
4. Отвечай на конкретный вопрос читателя.
5. Не повторяй соседние статьи пула.
6. Не вставляй поисковые запросы искусственно.
7. Используй короткие абзацы и конкретные примеры.
8. Отделяй установленные факты от предположений и советов.
9. Для медицинских, финансовых, юридических и опасных тем
   добавь пометку, что материал требует экспертной проверки.
10. В конце составь список утверждений, которые нужно проверить.

ФОРМАТ ОТВЕТА:

ЗАГОЛОВОК:
...

КРАТКОЕ СОДЕРЖАНИЕ:
...

СТАТЬЯ:
...

ЧТО НУЖНО ПРОВЕРИТЬ:
- ...
- ...
"""


def stream_article(
    pool_name,
    pool_description,
    audience,
    style_requirements,
    topic,
    article_type="",
    search_intent="",
    primary_query="",
    secondary_queries="",
    source_text="",
    model=DEFAULT_MODEL,
    base_url=OLLAMA_URL,
):
    prompt = build_prompt(
        pool_name=pool_name,
        pool_description=pool_description,
        audience=audience,
        style_requirements=style_requirements,
        topic=topic,
        article_type=article_type,
        search_intent=search_intent,
        primary_query=primary_query,
        secondary_queries=secondary_queries,
        source_text=source_text,
    )

    response = get_client(base_url).chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты внимательный редактор. "
                    "Пиши естественным русским языком."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.55,
        stream=True,
    )

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None)

        if text:
            yield text


def generate_article(
    pool_name,
    pool_description,
    audience,
    style_requirements,
    topic,
    article_type="",
    search_intent="",
    primary_query="",
    secondary_queries="",
    source_text="",
    model=DEFAULT_MODEL,
    base_url=OLLAMA_URL,
):
    parts = []

    for part in stream_article(
        pool_name=pool_name,
        pool_description=pool_description,
        audience=audience,
        style_requirements=style_requirements,
        topic=topic,
        article_type=article_type,
        search_intent=search_intent,
        primary_query=primary_query,
        secondary_queries=secondary_queries,
        source_text=source_text,
        model=model,
        base_url=base_url,
    ):
        parts.append(part)

    return "".join(parts)