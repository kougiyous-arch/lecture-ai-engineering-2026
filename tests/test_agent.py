"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai.messages import DeferredToolRequests, ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app.agent import agent

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    deferred = result.output if isinstance(result.output, DeferredToolRequests) else None
    deferred_approvals = len(deferred.approvals) if deferred else 0
    assert len(_parts(result, ToolReturnPart)) + deferred_approvals == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


def test_learning_log_is_deferred_until_approved(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("第2回の学習記録を保存して")

    assert isinstance(result.output, DeferredToolRequests)
    assert [call.tool_name for call in result.output.approvals] == ["save_learning_log"]
    assert not (tmp_path / "learning_log").exists()

    approval = result.output.build_results(approve_all=True)
    with agent.override(model=TestModel(call_tools=[])):
        resumed = agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=approval,
        )

    assert isinstance(resumed.output, str)
    assert (tmp_path / "learning_log" / "learning_log.md").exists()


def test_learning_log_is_not_saved_when_denied(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")
    with agent.override(model=TestModel(call_tools=["save_learning_log"])):
        result = agent.run_sync("第2回の学習記録を保存して")

    assert isinstance(result.output, DeferredToolRequests)
    denied = result.output.build_results(
        approvals={result.output.approvals[0].tool_call_id: False}
    )
    with agent.override(model=TestModel(call_tools=[])):
        agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=denied,
        )

    assert not (tmp_path / "learning_log").exists()


def test_run_with_approval_prompts_before_saving(tmp_path, monkeypatch):
    from app import agent as agent_module, tools

    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")
    models = iter([TestModel(call_tools=["save_learning_log"]), TestModel(call_tools=[])])
    monkeypatch.setattr(agent_module, "build_model", lambda: next(models))
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = agent_module.run_with_approval(
        agent_module.agent, "第2回の学習記録を保存して"
    )

    assert isinstance(result.output, str)
    assert (tmp_path / "learning_log" / "learning_log.md").exists()
