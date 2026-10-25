from types import SimpleNamespace

from google.genai import types

import app.ask
from app.ask import print_usage_metadata


def test_print_usage_metadata_reports_input_and_output_tokens(capsys):
    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=123,
            candidates_token_count=456,
            total_token_count=579,
        )
    )

    print_usage_metadata(response)

    captured = capsys.readouterr()
    assert "入力トークン数: 123" in captured.out
    assert "出力トークン数: 456" in captured.out


def test_send_message_reports_elapsed_time(monkeypatch, capsys):
    clock = iter([10.0, 11.234])
    monkeypatch.setattr(app.ask.time, "perf_counter", lambda: next(clock))

    class Chat:
        def send_message(self, question):
            assert question == "LoRAとは？"
            return SimpleNamespace(text="回答", usage_metadata=None)

    response = app.ask.send_message(Chat(), "LoRAとは？")

    assert response.text == "回答"
    assert "[time] 応答時間: 1.234 秒" in capsys.readouterr().out


def test_interactive_chat_reuses_chat_session(monkeypatch, tmp_path, capsys):
    questions = iter(["LoRAとは？", "その利点は？", "終了"])
    sent_questions = []

    class Chat:
        def get_history(self):
            return []

        def send_message(self, question):
            sent_questions.append(question)
            return SimpleNamespace(text=f"回答: {question}", usage_metadata=None)

    chat = Chat()

    class Chats:
        def create(self, *, model, history):
            assert model == app.ask.MODEL
            assert history == []
            return chat

    class Client:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.chats = Chats()

    monkeypatch.setattr(app.ask.genai, "Client", Client)
    monkeypatch.setattr(app.ask, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(app.ask, "HISTORY_PATH", tmp_path / "ask-history.json")
    monkeypatch.setattr("builtins.input", lambda _: next(questions))

    app.ask.interactive_chat()

    assert sent_questions == ["LoRAとは？", "その利点は？"]
    assert "回答: その利点は？" in capsys.readouterr().out


def test_ask_restores_history_across_calls(monkeypatch, tmp_path, capsys):
    history_path = tmp_path / "ask-history.json"
    received_histories = []

    class Chat:
        def __init__(self, history):
            self.history = history

        def send_message(self, question):
            self.history.extend(
                [
                    types.Content(role="user", parts=[types.Part(text=question)]),
                    types.Content(role="model", parts=[types.Part(text="回答")]),
                ]
            )
            return SimpleNamespace(text="回答", usage_metadata=None)

        def get_history(self):
            return self.history

    class Chats:
        def create(self, *, model, history):
            assert model == app.ask.MODEL
            received_histories.append(list(history))
            return Chat(history)

    class Client:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.chats = Chats()

    monkeypatch.setattr(app.ask, "HISTORY_PATH", history_path)
    monkeypatch.setattr(app.ask.genai, "Client", Client)
    monkeypatch.setattr(app.ask, "get_api_key", lambda: "test-key")

    app.ask.ask("私の好きな色は青です")
    app.ask.ask("私の好きな色は何ですか？")

    assert len(received_histories[0]) == 0
    assert len(received_histories[1]) == 2
    assert received_histories[1][0].parts[0].text == "私の好きな色は青です"
    assert "私の好きな色は青です" in history_path.read_text(encoding="utf-8")
    capsys.readouterr()


def test_main_starts_interactive_chat_without_question(monkeypatch):
    started = []
    monkeypatch.setattr("sys.argv", ["app.ask"])
    monkeypatch.setattr(app.ask, "interactive_chat", lambda: started.append(True))

    app.ask.main()

    assert started == [True]


def test_main_can_reset_saved_history(monkeypatch, tmp_path, capsys):
    history_path = tmp_path / "ask-history.json"
    history_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(app.ask, "HISTORY_PATH", history_path)
    monkeypatch.setattr("sys.argv", ["app.ask", "--reset-history"])

    app.ask.main()

    assert not history_path.exists()
    assert "削除しました" in capsys.readouterr().out
