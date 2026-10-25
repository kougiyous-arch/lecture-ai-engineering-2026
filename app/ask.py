"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 会話履歴を保って続けて質問する
    uv run python -m app.ask --reset-history  # 保存した会話履歴を削除する

ツールを持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
STATE_DIRECTORY = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
HISTORY_PATH = STATE_DIRECTORY / "aie2026-exercises" / "ask-history.json"


def print_usage_metadata(response) -> None:
    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", None) if usage else None

    output_tokens = None
    if usage is not None:
        output_tokens = getattr(usage, "candidates_token_count", None)
        if output_tokens is None:
            output_tokens = getattr(usage, "response_token_count", None)

    if output_tokens is None and getattr(response, "candidates", None):
        output_tokens = getattr(response.candidates[0], "token_count", None)

    print(f"[usage] 入力トークン数: {input_tokens if input_tokens is not None else '不明'}")
    print(f"[usage] 出力トークン数: {output_tokens if output_tokens is not None else '不明'}")


def load_history() -> list[types.Content]:
    if not HISTORY_PATH.exists():
        return []
    saved_history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return [types.Content.model_validate(message) for message in saved_history]


def save_history(chat) -> None:
    HISTORY_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    HISTORY_PATH.parent.chmod(0o700)
    messages = [message.model_dump(mode="json", exclude_none=True) for message in chat.get_history()]
    HISTORY_PATH.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY_PATH.chmod(0o600)


def create_chat(client):
    return client.chats.create(model=MODEL, history=load_history())


def clear_history() -> None:
    HISTORY_PATH.unlink(missing_ok=True)


def send_message(chat, question: str):
    started_at = time.perf_counter()
    response = chat.send_message(question)
    elapsed = time.perf_counter() - started_at
    print(f"[time] 応答時間: {elapsed:.3f} 秒")
    print_usage_metadata(response)
    return response


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    chat = create_chat(client)
    response = send_message(chat, question)
    save_history(chat)
    return response.text


def interactive_chat() -> None:
    client = genai.Client(api_key=get_api_key())
    chat = create_chat(client)
    print("質問を入力してください（終了: exit / quit / 終了、または Ctrl-D）")

    while True:
        try:
            question = input("質問> ").strip()
        except EOFError:
            print()
            break

        if question.lower() in {"exit", "quit", "終了"}:
            break
        if not question:
            continue

        response = send_message(chat, question)
        save_history(chat)
        print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--interactive", action="store_true", help="会話履歴を保って続けて質問する（引数なしでも対話モード）")
    parser.add_argument("--reset-history", action="store_true", help="保存済みの会話履歴を削除する")
    args = parser.parse_args()

    if args.reset_history:
        clear_history()
        print("保存済みの会話履歴を削除しました")
        return

    print(f"[model] {MODEL}")
    if args.interactive or args.question is None:
        try:
            interactive_chat()
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            raise SystemExit(1)
        return

    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
