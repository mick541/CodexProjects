from types import SimpleNamespace

import app


def test_app_client_uses_explicit_timeout_and_no_retries(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(app, "OpenAI", FakeOpenAI)

    app.get_client()

    assert captured["base_url"] == app.OLLAMA_URL
    assert captured["api_key"] == "ollama"
    assert captured["timeout"] == 120.0
    assert captured["max_retries"] == 0


def test_call_model_returns_message_content(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == app.MODEL_NAME
            assert kwargs["temperature"] == 0.25
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Тестовый ответ")
                    )
                ]
            )

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setattr(app, "get_client", lambda: FakeClient())

    assert app.call_model("Тестовый prompt", temperature=0.25) == "Тестовый ответ"

