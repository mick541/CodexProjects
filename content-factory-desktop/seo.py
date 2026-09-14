import re
from collections import Counter


CLICKBAIT_PATTERNS = [
    r"\bвы не поверите\b",
    r"\bшок\b",
    r"\bсенсация\b",
    r"\bсрочно\b",
    r"\bсекрет\b",
    r"\bникто не ожидал\b",
    r"\bшокирующ\w*\b",
    r"\bразоблачени\w*\b",
]


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def count_phrase(text, phrase):
    text_normalized = normalize(text)
    phrase_normalized = normalize(phrase)

    if not phrase_normalized:
        return 0

    return text_normalized.count(phrase_normalized)


def extract_headings(text):
    headings = []

    for line in (text or "").splitlines():
        clean_line = line.strip()

        if clean_line.startswith("#"):
            headings.append(clean_line.lstrip("#").strip())

        elif clean_line.isupper() and 3 <= len(clean_line) <= 120:
            headings.append(clean_line)

    return headings


def calculate_readability(text):
    words = re.findall(r"\b[А-Яа-яЁёA-Za-z]+\b", text or "")
    sentences = re.findall(r"[.!?]+", text or "")

    word_count = len(words)
    sentence_count = max(len(sentences), 1)

    average_sentence_length = word_count / sentence_count

    if average_sentence_length <= 18:
        level = "Хорошая"
    elif average_sentence_length <= 28:
        level = "Средняя"
    else:
        level = "Тяжёлая"

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "average_sentence_length": round(
            average_sentence_length,
            1,
        ),
        "level": level,
    }


def find_repeated_words(text, minimum_length=6, limit=10):
    words = re.findall(
        r"\b[А-Яа-яЁёA-Za-z]{%d,}\b" % minimum_length,
        normalize(text),
    )

    stop_words = {
        "который",
        "которая",
        "которые",
        "можно",
        "нужно",
        "также",
        "будет",
        "этого",
        "потому",
        "если",
        "чтобы",
        "между",
        "после",
        "перед",
        "только",
        "однако",
        "статьи",
        "материала",
    }

    filtered = [
        word for word in words if word not in stop_words
    ]

    return Counter(filtered).most_common(limit)


def check_keyword_usage(text, primary_query, secondary_queries):
    notes = []
    primary_count = count_phrase(text, primary_query)

    if not primary_query:
        notes.append("Основной поисковый запрос не задан.")
    elif primary_count == 0:
        notes.append(
            "Основной поисковый запрос не найден. "
            "Проверьте естественные словоформы и соответствие темы."
        )
    elif primary_count > 8:
        notes.append(
            "Основной запрос повторяется слишком часто. "
            "Возможен переспам."
        )

    secondary_found = []

    for query in secondary_queries or []:
        if count_phrase(text, query) > 0:
            secondary_found.append(query)

    if secondary_queries and not secondary_found:
        notes.append(
            "Ни один дополнительный запрос не найден. "
            "Проверьте, действительно ли семантика относится к статье."
        )

    return {
        "primary_count": primary_count,
        "secondary_found": secondary_found,
        "notes": notes,
    }


def check_clickbait(title, text):
    combined = f"{title or ''} {text or ''}"
    found = []

    for pattern in CLICKBAIT_PATTERNS:
        matches = re.findall(
            pattern,
            combined,
            flags=re.IGNORECASE,
        )

        found.extend(matches)

    notes = []

    if found:
        notes.append(
            "Обнаружены потенциально кликбейтные выражения: "
            + ", ".join(sorted(set(found)))
        )

    if title and text:
        title_words = set(normalize(title).split())
        text_words = set(normalize(text).split())

        if title_words and len(title_words & text_words) < 2:
            notes.append(
                "Заголовок слабо связан с текстом. "
                "Проверьте соответствие обещания содержанию."
            )

    return {
        "found": sorted(set(found)),
        "notes": notes,
    }


def check_internal_links(text, related_topics=None):
    topics = related_topics or []
    normalized_text = normalize(text)

    found_topics = [
        topic for topic in topics
        if normalize(topic) in normalized_text
    ]

    notes = []

    if len(topics) >= 2 and not found_topics:
        notes.append(
            "Связанные темы пула не упомянуты. "
            "Добавьте ссылки или полезные переходы, если они уместны."
        )

    return {
        "found_topics": found_topics,
        "notes": notes,
    }


def check_seo(
    title,
    text,
    primary_query="",
    secondary_queries=None,
    related_topics=None,
):
    secondary_queries = secondary_queries or []
    related_topics = related_topics or []

    readability = calculate_readability(text)
    keyword_result = check_keyword_usage(
        text,
        primary_query,
        secondary_queries,
    )
    clickbait_result = check_clickbait(title, text)
    links_result = check_internal_links(
        text,
        related_topics,
    )
    repeated_words = find_repeated_words(text)

    notes = []

    if not title.strip():
        notes.append("Заголовок отсутствует.")

    if readability["word_count"] < 250:
        notes.append(
            "Текст короткий для полноценной статьи. "
            "Проверьте, достаточно ли раскрыта тема."
        )

    if readability["level"] == "Тяжёлая":
        notes.append(
            "Предложения в среднем слишком длинные. "
            "Упростите синтаксис и разбейте абзацы."
        )

    notes.extend(keyword_result["notes"])
    notes.extend(clickbait_result["notes"])
    notes.extend(links_result["notes"])

    if repeated_words:
        top_word, top_count = repeated_words[0]

        if top_count >= 12:
            notes.append(
                f"Слово «{top_word}» повторяется {top_count} раз. "
                "Проверьте естественность текста."
            )

    score = 100

    score -= min(len(notes) * 10, 60)

    if readability["level"] == "Средняя":
        score -= 5

    if readability["level"] == "Тяжёлая":
        score -= 15

    if clickbait_result["found"]:
        score -= 15

    score = max(score, 0)

    return {
        "score": score,
        "readability": readability,
        "keywords": keyword_result,
        "clickbait": clickbait_result,
        "internal_links": links_result,
        "repeated_words": repeated_words,
        "notes": notes,
    }


def format_seo_report(report):
    lines = [
        f"ПРЕДВАРИТЕЛЬНАЯ SEO-ОЦЕНКА: {report['score']}/100",
        "",
        "ЧИТАЕМОСТЬ:",
        f"- Слов: {report['readability']['word_count']}",
        f"- Предложений: {report['readability']['sentence_count']}",
        (
            "- Средняя длина предложения: "
            f"{report['readability']['average_sentence_length']}"
        ),
        f"- Уровень: {report['readability']['level']}",
        "",
        "ПОИСКОВЫЕ ЗАПРОСЫ:",
        (
            "- Основной запрос найден: "
            f"{report['keywords']['primary_count']} раз"
        ),
        (
            "- Дополнительных запросов найдено: "
            f"{len(report['keywords']['secondary_found'])}"
        ),
        "",
        "ВНУТРЕННИЕ СВЯЗИ:",
        (
            "- Связанных тем найдено: "
            f"{len(report['internal_links']['found_topics'])}"
        ),
        "",
        "ЗАМЕЧАНИЯ:",
    ]

    if report["notes"]:
        lines.extend(f"- {note}" for note in report["notes"])
    else:
        lines.append("- Явных проблем не обнаружено.")

    lines.extend(
        [
            "",
            "ВАЖНО: эта оценка предварительная и не гарантирует "
            "поисковое ранжирование.",
        ]
    )

    return "\n".join(lines)