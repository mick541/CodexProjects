from fact_checker import check_article
from seo import check_seo, format_seo_report
from dzen_rules import check_dzen_rules, format_dzen_report


def normalize_fact_result(result):
    if not isinstance(result, dict):
        return {
            "score": 0,
            "passed": False,
            "notes": [
                "Фактчекер вернул результат неизвестного формата."
            ],
        }

    normalized = dict(result)

    if "score" not in normalized:
        if normalized.get("passed") is True:
            normalized["score"] = 100
        elif normalized.get("passed") is False:
            normalized["score"] = 0
        else:
            normalized["score"] = 50

    if "passed" not in normalized:
        normalized["passed"] = normalized["score"] >= 70

    if "notes" not in normalized:
        notes = []

        for key in ("issues", "warnings", "problems"):
            value = normalized.get(key)

            if isinstance(value, list):
                notes.extend(str(item) for item in value)

        normalized["notes"] = notes

    return normalized


def run_fact_check(text, claims=None):
    try:
        result = check_article(text)
    except TypeError:
        try:
            result = check_article(
                text=text,
                claims=claims or [],
            )
        except TypeError:
            result = check_article(
                text,
            )

    return normalize_fact_result(result)


def run_quality_control(
    title,
    text,
    primary_query="",
    secondary_queries=None,
    related_topics=None,
    claims=None,
):
    secondary_queries = secondary_queries or []
    related_topics = related_topics or []
    claims = claims or []

    fact_result = run_fact_check(
        text=text,
        claims=claims,
    )

    seo_result = check_seo(
        title=title,
        text=text,
        primary_query=primary_query,
        secondary_queries=secondary_queries,
        related_topics=related_topics,
    )

    dzen_result = check_dzen_rules(
        title=title,
        text=text,
    )

    scores = [
        seo_result["score"],
        dzen_result["score"],
        fact_result["score"],
    ]

    total_score = round(sum(scores) / len(scores))

    passed = (
        fact_result["passed"]
        and dzen_result["passed"]
        and not seo_result["notes"]
    )

    return {
        "total_score": total_score,
        "facts": fact_result,
        "seo": seo_result,
        "dzen": dzen_result,
        "passed": passed,
    }


def format_quality_report(report):
    lines = [
        f"ИТОГОВАЯ ОЦЕНКА КАЧЕСТВА: {report['total_score']}/100",
        "",
        (
            "ОБЩИЙ СТАТУС: "
            + ("ПРОЙДЕНО" if report["passed"] else "ТРЕБУЕТ ДОРАБОТКИ")
        ),
        "",
        "ПРОВЕРКИ:",
        f"- SEO: {report['seo']['score']}/100",
        f"- Дзен: {report['dzen']['score']}/100",
        f"- Факты: {report['facts']['score']}/100",
        "",
        "SEO-ОТЧЁТ:",
        format_seo_report(report["seo"]),
        "",
        "ОТЧЁТ ПО ПРАВИЛАМ ДЗЕНА:",
        format_dzen_report(report["dzen"]),
        "",
        "ФАКТЧЕКИНГ:",
    ]

    fact_notes = report["facts"].get("notes", [])

    if fact_notes:
        lines.extend(
            f"- {note}"
            for note in fact_notes
        )
    else:
        lines.append("- Явных замечаний не обнаружено.")

    return "\n".join(lines)


if __name__ == "__main__":
    demo_title = "Как проверить материал перед публикацией"

    demo_text = (
        "Это демонстрационный текст для проверки качества материала. "
        "Он показывает, как единый модуль объединяет несколько проверок. "
        "Редактор может проверить структуру статьи, её заголовок и "
        "наличие потенциально проблемных формулировок."
    )

    result = run_quality_control(
        title=demo_title,
        text=demo_text,
        primary_query="проверка материала",
        secondary_queries=[
            "качество статьи",
            "подготовка публикации",
        ],
        related_topics=[
            "редактура",
            "фактчекинг",
        ],
        claims=[],
    )

    print(format_quality_report(result))