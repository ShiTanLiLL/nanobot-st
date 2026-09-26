"""第 6 课测试：上下文组装（人设置顶 + 截断保配对）。"""

from nanobot_st.context import ContextBuilder, truncate_history
from nanobot_st.session import Session


def _assistant_note(call_id: str) -> dict:
    """造一条"AI 请求调用工具"的便签消息。"""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": call_id, "type": "function",
                        "function": {"name": "get_time", "arguments": "{}"}}],
    }


def _tool_result(call_id: str) -> dict:
    """造一条工具结果消息（与便签配对）。"""
    return {"role": "tool", "tool_call_id": call_id, "name": "get_time", "content": "2026-09-26 10:00:00"}


def test_build_prepends_system_prompt():
    """验证：组装结果的第一条恒为 system 人设，其后历史按序跟上。"""
    session = Session()
    session.add_user("你好")
    session.add_assistant("你也好")

    messages = ContextBuilder().build(session)

    assert messages[0]["role"] == "system"
    assert "简体中文" in messages[0]["content"]
    assert messages[1:] == session.messages
    # 原始历史未被修改（build 只读不改）
    assert len(session.messages) == 2


def test_truncate_keeps_most_recent_messages():
    """验证：超长历史只保留最近 N 条。"""
    messages = [{"role": "user", "content": f"问{i}"} for i in range(100)]

    cut = truncate_history(messages, keep_last=10)

    assert cut == messages[-10:]


def test_truncate_never_orphans_tool_results():
    """验证铁律：切口落在 tool 结果上时自动后移，绝不产生孤儿 tool 消息。

    构造的历史：[..., 便签c1, 结果c1, 用户问, AI答]
    keep_last=1 时朴素切口正好切在"结果c1"上（便签被切掉）——必须再多丢这一条。
    """
    messages = [
        {"role": "user", "content": "早"},
        _assistant_note("c1"),
        _tool_result("c1"),
        {"role": "user", "content": "晚"},
    ]

    cut = truncate_history(messages, keep_last=1)

    # 唯一幸存的是"晚"：孤儿 tool 被额外丢弃
    assert cut == [{"role": "user", "content": "晚"}]
    # 原列表不受影响
    assert len(messages) == 4


def test_truncate_short_history_untouched():
    """验证：历史不超限时原样返回（且是拷贝，不是同一个列表对象）。"""
    messages = [{"role": "user", "content": "只有一条"}]

    cut = truncate_history(messages, keep_last=10)

    assert cut == messages
    assert cut is not messages
