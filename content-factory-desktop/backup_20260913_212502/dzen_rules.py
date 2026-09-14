import re


CLICKBAIT_PATTERNS = [
    r"\bвы не поверите\b",
    r"\bникто не ожидал\b",
    r"\bшок\b",
    r"\bсенсаци\w*\b",
    r"\bсрочно\b",
    r"\bсекрет\w*\b",
    r"\bразоблачени\w*\b",
    r"\bвот что произойдет\b",
    r"\bэто изменит вашу жизнь\b",
    r"\bвсе скрывают\b",
    r"\bправда вас удивит\b",
]


FORBIDDEN_PATTERNS = [
    r"\bубийств\w*\b",
    r"\bсамоубийств\w*\b",
    r"\bнаркотик\w*\b",
    r"\bпорно\w*\b",
    r"\bнасили\w*\b",
    r"\bэкстремизм\w*\b",
    r"\bтерроризм\w*\b",
]


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def count_letters(text):
    return len(re.findall(r"[A-Za-zА-Яа-яЁё]", text or ""))


def count_uppercase_letters(text):
    return len(re.findall(r"[A-ZА-ЯЁ]", text or ""))


def split_words(text):
    return re.findall(
        r"[A-Za-zА-Яа-яЁё0-9-]+",
        text or "",
    )


def find_matches(text, patterns):
    found = []

    for pattern in patterns:
        found.extend(
            re.findall(
                pattern,
                text or "",
                flags=re.IGNORECASE,
            )
        )

    return sorted(set(found))


def check_title(title):
    title = normalize(title)
    issues = []
    warnings = []

    if not title:
        issues.append("Заголовок отсутствует.")
        return {
            "passed": False,
            "issues": issues,
            "warnings": warnings,
            "clickbait": [],
        }

    title_length = len(title)

    if title_length < 20:
        warnings.append(
            "Заголовок очень короткий. "
            "Проверьте, понятно ли читателю содержание."
        )

    if title_length > 140:
        warnings.append(
            "Заголовок слишком длинный. "
            "Попробуйте сделать его компактнее."
        )

    if title.endswith(("!", "!!", "!!!", "?")):
        warnings.append(
            "Заголовок заканчивается эмоциональным знаком. "
            "Проверьте, не выглядит ли он как манипуляция."
        )

    if re.search(r"[!?]{2,}", title):
        issues.append(
            "В заголовке несколько знаков вопроса или восклицания подряд."
        )

    letters = count_letters(title)
    uppercase = count_uppercase_letters(title)

    if letters > 0 and uppercase / letters >= 0.5:
        issues.append(
            "В заголовке слишком много заглавных букв."
        )

    if re.search(r"\.{3,}", title):
        warnings.append(
            "В заголовке используется многоточие."
        )

    clickbait = find_matches(
        title,
        CLICKBAIT_PATTERNS,
    )

    if clickbait:
        issues.append(
            "Обнаружены потенциально кликбейтные формулировки: "
            + ", ".join(clickbait)
        )

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "clickbait": clickbait,
    }


def check_text(text):
    text = normalize(text)
    issues = []
    warnings = []

    words = split_words(text)
    word_count = len(words)

    if word_count < 250:
        warnings.append(
            "Материал содержит меньше 250 слов. "
            "Проверьте, достаточно ли полно раскрыта тема."
        )

    if word_count < 100:
        issues.append(
            "Материал слишком короткий для полноценной статьи."
        )

    forbidden = find_matches(
        text,
        FORBIDDEN_PATTERNS,
    )

    if forbidden:
        warnings.append(
            "Проверьте контекст потенциально чувствительных слов: "
            + ", ".join(forbidden)
        )

    if re.search(r"\b(100%|гарантированно|точно разбогатеете)\b", text, re.I):
        warnings.append(
            "Обнаружены категоричные обещания. "
            "Проверьте, есть ли у них подтверждение."
        )

    if re.search(r"\b(учёные доказали|эксперты уверены|все знают)\b", text, re.I):
        warnings.append(
            "Есть обобщённые ссылки на экспертов или учёных. "
            "Желательно указать конкретный источник."
        )

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "word_count": word_count,
        "sensitive_words": forbidden,
    }


def check_title_relevance(title, text):
    title_words = {
        word.lower()
        for word in split_words(title)
        if len(word) >= 4
    }

    text_words = {
        word.lower()
        for word in split_words(text)
    }

    if not title_words:
        return {
            "passed": False,
            "message": "Невозможно проверить соответствие пустого заголовка.",
        }

    overlap = title_words & text_words
    ratio = len(overlap) / len(title_words)

    if ratio < 0.25:
        return {
            "passed": False,
            "message": (
                "Заголовок слабо связан с текстом. "
                "Проверьте, соответствует ли обещание содержанию."
            ),
            "overlap": sorted(overlap),
            "ratio": round(ratio, 2),
        }

    return {
        "passed": True,
        "message": "Заголовок и текст выглядят тематически связанными.",
        "overlap": sorted(overlap),
        "ratio": round(ratio, 2),
    }


def check_dzen_rules(title, text):
    title_result = check_title(title)
    text_result = check_text(text)
    relevance_result = check_title_relevance(title, text)

    issues = []
    warnings = []

    issues.extend(title_result["issues"])
    issues.extend(text_result["issues"])

    warnings.extend(title_result["warnings"])
    warnings.extend(text_result["warnings"])

    if not relevance_result["passed"]:
        warnings.append(relevance_result["message"])

    passed = not issues

    score = 100
    score -= min(len(issues) * 25, 75)
    score -= min(len(warnings) * 7, 35)

    score = max(score, 0)

    return {
        "passed": passed,
        "score": score,
        "title": title_result,
        "text": text_result,
        "relevance": relevance_result,
        "issues": issues,
        "warnings": warnings,
    }


def format_dzen_report(report):
    lines = [
        f"ПРОВЕРКА ПРАВИЛ ДЗЕНА: {report['score']}/100",
        "",
        (
            "СТАТУС: "
            + ("ПРОЙДЕНО" if report["passed"] else "ЕСТЬ ПРОБЛЕМЫ")
        ),
        "",
        "КРИТИЧЕСКИЕ ПРОБЛЕМЫ:",
    ]

    if report["issues"]:
        lines.extend(
            f"- {issue}"
            for issue in report["issues"]
        )
    else:
        lines.append("- Не обнаружены.")

    lines.extend(
        [
            "",
            "ПРЕДУПРЕЖДЕНИЯ:",
        ]
    )

    if report["warnings"]:
        lines.extend(
            f"- {warning}"
            for warning in report["warnings"]
        )
    else:
        lines.append("- Не обнаружены.")

    lines.extend(
        [
            "",
            "ПРОВЕРКА СВЯЗИ ЗАГОЛОВКА И ТЕКСТА:",
            f"- {report['relevance']['message']}",
            "",
            "Примечание: автоматическая проверка не заменяет "
            "финальную редактуру и проверку фактов.",
        ]
    )

    return "\n".join(lines)