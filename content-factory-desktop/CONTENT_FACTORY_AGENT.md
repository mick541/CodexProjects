# Content Factory Agent Context

## Обязательное правило

Перед любым изменением прочитайте:

- `CONTENT_FACTORY_PASSPORT.md`
- `CONTENT_FACTORY_AGENT.md`
- `CONTENT_FACTORY_CHANGELOG.md`

После изменения:

1. Выполните `python -m py_compile .\app.py`.
2. Запустите Streamlit.
3. Проверьте изменённую функцию вручную.
4. Обновите `CONTENT_FACTORY_CHANGELOG.md`.
5. Если изменилась архитектура, обновите `CONTENT_FACTORY_PASSPORT.md`.

## Проект

Главный файл приложения:

```text
app.py
```

Технология интерфейса:

```text
Streamlit
```

Модель подключается через OpenAI-совместимый API RouterAI.

## Основные функции app.py

- `init_db()` — создание структуры базы данных.
- `get_client()` — создание клиента RouterAI.
- `call_model()` — запрос к языковой модели.
- `run_seo_research()` — SEO-исследование.
- `generate_article()` — генерация статьи.
- `improve_article()` — базовое улучшение.
- `improve_article_mode()` — улучшение по выбранному режиму.
- `improve_and_recheck()` — улучшение и повторная проверка.
- `run_quality_for_item()` — запуск проверки качества.
- `build_article_markdown()` — экспорт только статьи.
- `build_metadata_markdown()` — экспорт служебных данных.
- `render_quality_check()` — интерфейс проверки.

## Ограничения

- Не удалять рабочие функции без резервной копии.
- Не вставлять PowerShell-синтаксис внутрь Python-кода.
- Не записывать API-ключ в `app.py`.
- Не считать SEO-балл гарантией поискового ранжирования.
- Не придумывать источники и факты.
- Не обещать достоверную «очистку от ИИ»; использовать редактуру естественности.
- Не смешивать статью и служебные данные в одном Markdown-файле.

## Команды

Проверка синтаксиса:

```powershell
python -m py_compile .\app.py
```

Запуск:

```powershell
python -m streamlit run .\app.py
```

## Требование к новым изменениям

Каждое изменение должно иметь:

- описание;
- статус;
- результат проверки;
- дату;
- при необходимости — известное ограничение.
