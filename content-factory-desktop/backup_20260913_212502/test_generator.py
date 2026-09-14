from types import SimpleNamespace

import pytest
import openai

import generator


def test_get_client_uses_explicit_timeout_and_retries():
    client = generator.get_client("http://example.test/v1")

    assert client.timeout is not None
    assert client.max_retries == 0


def test_build_prompt_contains_topic_and_source():
    prompt = generator.build_prompt(
        "Тестовый пул",
        "",
        "",
        "",
        "Проверяемая тема",
        "",
        "",
        "",
        "",
        "Исходные данные",
    )

    assert "Проверяемая тема" in prompt
    assert "Исходные данные" in prompt


def test_stream_article_collects_content(monkeypatch):
    chunks = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="Первая часть")
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=" и вторая часть")
                )
            ]
        ),
        SimpleNamespace(choices=[]),
    ]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert kwargs["stream"] is True
            return iter(chunks)

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setattr(generator, "get_client", lambda base_url: FakeClient())

    result = generator.generate_article(
        "Пул",
        "",
        "",
        "",
        "Тема",
        model="test-model",
        base_url="http://mock.test/v1",
    )

    assert result == "Первая часть и вторая часть"

def test_generate_article_propagates_connection_error(monkeypatch):
    error = openai.APIConnectionError(
        message="connection failed",
        request=None,
    )

    class FakeCompletions:
        def create(self, **kwargs):
            raise error

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setattr(generator, "get_client", lambda base_url: FakeClient())

    with pytest.raises(openai.APIConnectionError):
        generator.generate_article(
            "Пул",
            "",
            "",
            "",
            "Тема",
            model="test-model",
            base_url="http://mock.test/v1",
        )

