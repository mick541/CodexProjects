import re

RULES = [
    (
        "META_INTRO",
        re.compile(
            r"\b(в этой статье мы расскажем|в данной статье мы рассмотрим|"
            r"сегодня мы поговорим|давайте разберёмся)\b",
            re.IGNORECASE,
        ),
        "Мета-введение: текст сообщает о статье вместо непосредственного ответа.",
    ),
    (
        "GENERIC_CLAIM",
        re.compile(
            r"\b(важно понимать|стоит отметить|не секрет, что|"
            r"как известно|всем известно)\b",
            re.IGNORECASE,
        ),
        "Общая вводная формулировка без конкретного содержания.",
    ),
    (
        "PROMOTIONAL_ABSOLUTE",
        re.compile(
            r"\b(идеальный|уникальный|революционный|"
            r"лучший|самый эффективный|гарантированно)\b",
            re.IGNORECASE,
        ),
        "Категоричное или рекламное утверждение требует основания.",
    ),
]


def check_no_ai_slop(text):
    if not isinstance(text, str):
        text = str(text or "")

    findings = []

    for rule_id, pattern, message in RULES:
        for match in pattern.finditer(text):
            findings.append(
                {
                    "rule_id": rule_id,
                    "matched_text": match.group(0),
                    "message": message,
                    "risk_level": "Средний",
                }
            )

    return {
        "passed": not findings,
        "score": max(0, 100 - min(len(findings) * 10, 100)),
        "findings": findings,
        "notes": [
            (
                f"Найдено потенциальных признаков AI-slop: {len(findings)}. "
                "Требуется редакторская оценка."
            )
            if findings
            else "Явных признаков AI-slop не обнаружено."
        ],
        "changed": False,
    }


def format_no_ai_slop_report(report):
    lines = ["AI CLEANER / NO-AI-SLOP:"]

    for note in report.get("notes", []):
        lines.append(f"- {note}")

    for index, finding in enumerate(report.get("findings", []), start=1):
        lines.append(
            f"{index}. [{finding['risk_level']}] "
            f"{finding['rule_id']}: {finding['message']} "
            f"Фрагмент: «{finding['matched_text']}»"
        )

    if not report.get("findings"):
        lines.append("- Замечаний нет.")

    lines.append("- Исходный текст не изменён автоматически.")
    return "\n".join(lines)
