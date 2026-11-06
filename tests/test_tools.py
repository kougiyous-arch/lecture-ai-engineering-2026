"""ツールのテスト（LLMもAPIキーも使わない）。"""

import json

from app import tools


def test_glossary_ids_are_unique_and_related_links_exist():
    terms = tools.load_glossary()
    ids = [t["id"] for t in terms]
    assert len(ids) == len(set(ids))
    for t in terms:
        for r in t["related"]:
            assert r in ids, f"{t['id']} の related に存在しない id: {r}"


def test_search_finds_term_by_name_and_alias():
    for query in ["LoRA", "lora", "Low-Rank Adaptation"]:
        hits = json.loads(tools.search_glossary(query))
        assert hits[0]["term"] == "LoRA", query


def test_search_finds_course_specific_term():
    hits = json.loads(tools.search_glossary("lecNN-start"))
    assert hits[0]["term"] == "lecNN-start タグ"


def test_search_limits_number_of_results():
    hits = json.loads(tools.search_glossary("エージェント"))
    assert 1 <= len(hits) <= tools.MAX_RESULTS


def test_search_reports_not_found():
    assert "見つかりませんでした" in tools.search_glossary("存在しない用語xyz")


def test_lecture_summary():
    assert "エージェント" in tools.get_lecture_summary(3)
    assert "まだありません" in tools.get_lecture_summary(99)


def test_make_quiz_returns_question_and_answer_for_known_lecture():
    quiz = tools.make_quiz(1)
    assert "第1回の確認問題" in quiz
    assert "とは何ですか？" in quiz
    assert "答え:" in quiz


def test_make_quiz_reports_missing_lecture():
    quiz = tools.make_quiz(99)
    assert "まだありません" in quiz


def test_save_learning_log_appends_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")

    first = tools.save_learning_log(2, "LoRAのランクについて学んだ。")
    second = tools.save_learning_log(3, "ツール呼び出しを試した。")

    saved = (tmp_path / "learning_log" / "learning_log.md").read_text(encoding="utf-8")
    assert "第2回" in first and "保存しました" in first
    assert "第3回" in second and "保存しました" in second
    assert "LoRAのランクについて学んだ。" in saved
    assert "ツール呼び出しを試した。" in saved


def test_save_learning_log_rejects_invalid_input(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")

    assert "回番号は1以上" in tools.save_learning_log(0, "記録")
    assert "学習記録が空" in tools.save_learning_log(1, "  \n ")
    assert not (tmp_path / "learning_log").exists()


def test_default_question_of_lecture1_is_answerable_from_glossary():
    """第1回の既定の質問（app.ask）は、第3回のエージェントが用語集で正しく答えられること。"""
    from app.ask import DEFAULT_QUESTION

    assert "3レベル" in DEFAULT_QUESTION
    hits = json.loads(tools.search_glossary("3レベル"))
    assert hits[0]["term"] == "宿題の3レベル"
