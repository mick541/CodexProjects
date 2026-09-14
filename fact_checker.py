import re


HIGH_RISK_KEYWORDS = [
    "лекарство",
    "препарат",
    "дозировка",
    "симптом",
    "диагноз",
    "лечение",
    "болезнь",
    "давление",
    "беременность",
    "инвестиции",
    "кредит",
    "налог",
    "договор",
    "закон",
    "суд",
    "опасно",
    "безопасность",
    "электричество",
    "газ",
]


SUSPICIOUS_PATTERNS = [
    (
        r"\bсупраоптическ\w*\s+яд\w*\b",
        "Похоже на ошибку в термине. Проверьте научное название.",
    ),
    (
        r"\bгарантированно\b",
        "Категоричное обещание требует подтверждения.",
    ),
    (
        r"\bвсем известно\b",
        "Обобщение без источника. Уточните или удалите.",
    ),
    (
        r"\bученые доказали\b",
        "Нужно указать конкретное исследование или источник.",
    ),
    (
        r"\bлучший\b",
        "Сравнительное утверждение требует критерия и подтверждения.",
    ),
    (
        r"\bсамый эффективный\b",
        "Нужно подтвердить сравнительное утверждение.",
    ),
]


def detect_risk_level(text):
    lowered = text.lower()

    if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
        return "Высокий"

    if any(
        marker in lowered
        for marker in [
            "%",
            "процентов",
            "исследование",
            "исследования",
            "статистика",
            "согласно",
            "учёные",
            "ученые",
            "эксперты",
            "миллион",
            "тысяч",
        ]
    ):
        return "Средний"

    return "Низкий"


def split_into_claims(text):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    claims = []

    for sentence in sentences:
        clean_sentence = sentence.strip()

        if len(clean_sentence) < 35:
            continue

        if clean_sentence.startswith(
            (
                "ЗАГОЛОВОК:",
                "КРАТКОЕ СОДЕРЖАНИЕ:",
                "СТАТЬЯ:",
                "ЧТО НУЖНО ПРОВЕРИТЬ:",
            )
        ):
            continue

        claims.append(
            {
                "claim_text": clean_sentence,
                "claim_type": "Фактическое утверждение",
                "risk_level": detect_risk_level(clean_sentence),
            }
        )

    return claims


def find_suspicious_patterns(text):
    findings = []

    for pattern, message in SUSPICIOUS_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        if matches:
            findings.append(
                {
                    "matched_text": matches[0],
                    "message": message,
                    "risk_level": "Высокий",
                }
            )

    return findings


def check_article(text):
    claims = split_into_claims(text)
    suspicious = find_suspicious_patterns(text)

    high_risk_claims = [
        claim for claim in claims if claim["risk_level"] == "Высокий"
    ]

    medium_risk_claims = [
        claim for claim in claims if claim["risk_level"] == "Средний"
    ]

    notes = []

    if high_risk_claims:
        notes.append(
            f"Найдено утверждений высокого риска: "
            f"{len(high_risk_claims)}. Нужны источники и ручная проверка."
        )

    if medium_risk_claims:
        notes.append(
            f"Найдено утверждений среднего риска: "
            f"{len(medium_risk_claims)}. Желательна проверка источников."
        )

    if suspicious:
        notes.append(
            f"Найдено подозрительных формулировок: {len(suspicious)}."
        )

    if not claims:
        notes.append(
            "Не удалось выделить проверяемые утверждения."
        )

    if not notes:
        notes.append(
            "Автоматический скрининг не нашёл явных проблем. "
            "Это не является подтверждением фактической точности."
        )

    return {
        "claims": claims,
        "suspicious": suspicious,
        "notes": notes,
        "requires_manual_review": bool(
            high_risk_claims or suspicious
        ),
    }


def format_report(report):
    lines = []

    lines.append("РЕЗУЛЬТАТ ПЕРВИЧНОЙ ПРОВЕРКИ:")
    lines.extend(f"- {note}" for note in report["notes"])

    lines.append("")
    lines.append("ПОДОЗРИТЕЛЬНЫЕ ФРАГМЕНТЫ:")

    if report["suspicious"]:
        for item in report["suspicious"]:
            lines.append(
                f"- {item['matched_text']}: {item['message']}"
            )
    else:
        lines.append("- Не обнаружены.")

    lines.append("")
    lines.append("УТВЕРЖДЕНИЯ ДЛЯ ПРОВЕРКИ:")

    if report["claims"]:
        for index, claim in enumerate(report["claims"], start=1):
            lines.append(
                f"{index}. [{claim['risk_level']}] "
                f"{claim['claim_text']}"
            )
    else:
        lines.append("- Не выделены.")

    if report["requires_manual_review"]:
        lines.append("")
        lines.append(
            "ИТОГ: требуется ручная проверка перед публикацией."
        )
    else:
        lines.append("")
        lines.append(
            "ИТОГ: автоматический скрининг завершён; "
            "ручная редактура всё равно обязательна."
        )

    return "\n".join(lines)