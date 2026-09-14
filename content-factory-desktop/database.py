import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "content.db"


POOL_STATUSES = [
    "План",
    "Темы утверждены",
    "Генерируется",
    "Есть замечания",
    "Готово к публикации",
    "Опубликовано",
    "Заблокировано",
]

ARTICLE_STATUSES = [
    "План",
    "Генерируется",
    "Черновик",
    "Проверка фактов",
    "Есть замечания",
    "На редактуре",
    "SEO-проверка",
    "Проверено",
    "Готово к публикации",
    "Опубликовано",
    "Заблокировано",
]


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                audience TEXT,
                style_requirements TEXT,
                status TEXT NOT NULL DEFAULT 'План',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                topic TEXT NOT NULL,
                article_type TEXT,
                search_intent TEXT,
                primary_query TEXT,
                secondary_queries TEXT,
                outline TEXT,
                source_text TEXT,
                draft TEXT,
                edited_text TEXT,
                fact_notes TEXT,
                seo_notes TEXT,
                dzen_notes TEXT,
                status TEXT NOT NULL DEFAULT 'План',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (pool_id) REFERENCES pools(id)
            );

            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_id INTEGER NOT NULL,
                article_id INTEGER,
                query TEXT NOT NULL,
                cluster TEXT,
                intent TEXT,
                priority TEXT,
                frequency TEXT,
                source TEXT,
                status TEXT NOT NULL DEFAULT 'Не распределён',
                FOREIGN KEY (pool_id) REFERENCES pools(id),
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                claim_type TEXT,
                risk_level TEXT NOT NULL DEFAULT 'Средний',
                source_url TEXT,
                source_title TEXT,
                verification_status TEXT NOT NULL DEFAULT 'Не проверено',
                reviewer_note TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT,
                source_type TEXT,
                reliability TEXT,
                local_path TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS process_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_id INTEGER,
                article_id INTEGER,
                level TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (pool_id) REFERENCES pools(id),
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );
            """
        )
        connection.commit()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_pool(name, description="", audience="", style_requirements=""):
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO pools
            (name, description, audience, style_requirements, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                description,
                audience,
                style_requirements,
                now(),
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_pools():
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM pools
            ORDER BY id DESC
            """
        ).fetchall()


def get_pool(pool_id):
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM pools WHERE id = ?",
            (pool_id,),
        ).fetchone()


def update_pool_status(pool_id, status):
    with connect() as connection:
        connection.execute(
            "UPDATE pools SET status = ? WHERE id = ?",
            (status, pool_id),
        )
        connection.commit()


def create_article(
    pool_id,
    position,
    topic,
    article_type="",
    search_intent="",
    primary_query="",
    secondary_queries="",
    source_text="",
):
    timestamp = now()

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO articles
            (
                pool_id,
                position,
                topic,
                article_type,
                search_intent,
                primary_query,
                secondary_queries,
                source_text,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pool_id,
                position,
                topic,
                article_type,
                search_intent,
                primary_query,
                secondary_queries,
                source_text,
                "План",
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_articles(pool_id=None):
    with connect() as connection:
        if pool_id is None:
            return connection.execute(
                """
                SELECT *
                FROM articles
                ORDER BY pool_id, position
                """
            ).fetchall()

        return connection.execute(
            """
            SELECT *
            FROM articles
            WHERE pool_id = ?
            ORDER BY position
            """,
            (pool_id,),
        ).fetchall()


def get_article(article_id):
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()


def update_article_text(article_id, draft, status="Черновик"):
    with connect() as connection:
        connection.execute(
            """
            UPDATE articles
            SET draft = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                draft,
                status,
                now(),
                article_id,
            ),
        )
        connection.commit()


def update_article_notes(
    article_id,
    fact_notes="",
    seo_notes="",
    dzen_notes="",
    status="Есть замечания",
):
    with connect() as connection:
        connection.execute(
            """
            UPDATE articles
            SET fact_notes = ?,
                seo_notes = ?,
                dzen_notes = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                fact_notes,
                seo_notes,
                dzen_notes,
                status,
                now(),
                article_id,
            ),
        )
        connection.commit()


def update_article_status(article_id, status):
    with connect() as connection:
        connection.execute(
            """
            UPDATE articles
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                now(),
                article_id,
            ),
        )
        connection.commit()


def add_keyword(
    pool_id,
    query,
    cluster="",
    intent="",
    priority="Средний",
    frequency="",
    source="Ручной ввод",
    article_id=None,
):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO keywords
            (
                pool_id,
                article_id,
                query,
                cluster,
                intent,
                priority,
                frequency,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pool_id,
                article_id,
                query,
                cluster,
                intent,
                priority,
                frequency,
                source,
            ),
        )
        connection.commit()


def get_keywords(pool_id):
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM keywords
            WHERE pool_id = ?
            ORDER BY id
            """,
            (pool_id,),
        ).fetchall()


def add_claim(
    article_id,
    claim_text,
    claim_type="",
    risk_level="Средний",
    source_url="",
    source_title="",
):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO claims
            (
                article_id,
                claim_text,
                claim_type,
                risk_level,
                source_url,
                source_title
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                claim_text,
                claim_type,
                risk_level,
                source_url,
                source_title,
            ),
        )
        connection.commit()


def get_claims(article_id):
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM claims
            WHERE article_id = ?
            ORDER BY id
            """,
            (article_id,),
        ).fetchall()


def add_source(
    title,
    url="",
    source_type="",
    reliability="",
    local_path="",
    notes="",
):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO sources
            (
                title,
                url,
                source_type,
                reliability,
                local_path,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                url,
                source_type,
                reliability,
                local_path,
                notes,
                now(),
            ),
        )
        connection.commit()


def get_sources():
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM sources
            ORDER BY id DESC
            """
        ).fetchall()


def add_log(message, level="info", pool_id=None, article_id=None):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO process_log
            (pool_id, article_id, level, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                pool_id,
                article_id,
                level,
                message,
                now(),
            ),
        )
        connection.commit()


def get_logs(pool_id=None, article_id=None, limit=100):
    with connect() as connection:
        if article_id is not None:
            return connection.execute(
                """
                SELECT *
                FROM process_log
                WHERE article_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (article_id, limit),
            ).fetchall()

        if pool_id is not None:
            return connection.execute(
                """
                SELECT *
                FROM process_log
                WHERE pool_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (pool_id, limit),
            ).fetchall()

        return connection.execute(
            """
            SELECT *
            FROM process_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()