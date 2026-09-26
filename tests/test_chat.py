"""第 3 课测试：用假客户端验证"带工具的对话回合"。"""

from nanobot_st.chat import chat_turn
from nanobot_st.session import Session
from nanobot_st.tools import GET_TIME_SCHEMA


class FakeClient:
    """假装是 AsyncOpenAI 客户端，按"剧本"依次播放预设响应。

    剧本是一列 dict，每一幕有两种戏码：
    - {"finish_reason": "stop", "content": "..."}            → 模型直接给最终回答
    - {"finish_reason": "tool_calls", "tool_calls": [...]}   → 模型请求调用工具
    """

    def __init__(self, scripted: list[dict]):
        self._scripted = list(scripted)
        self.captured_calls: list[dict] = []
        self.chat = _FakeChat(self)


class _FakeChat:
    """模拟 client.chat 这一层，只为提供 .completions 属性。"""

    def __init__(self, owner: "FakeClient"):
        self.completions = _FakeCompletions(owner)


class _FakeCompletions:
    """模拟 client.chat.completions 这一层，提供异步 create()。"""

    def __init__(self, owner: "FakeClient"):
        self._owner = owner

    async def create(self, *, model, messages, tools=None, **kwargs):
        """播放剧本的下一幕，并记录本次请求参数的快照。"""
        scenario = self._owner._scripted.pop(0)
        snapshot = [dict(m) for m in messages]  # 快照：防止历史倒灌
        self._owner.captured_calls.append(
            {"model": model, "messages": snapshot, "tools": tools}
        )
        return _FakeResponse(scenario)


class _FakeResponse:
    """模拟响应对象：和真的一样是 choices 列表。"""

    def __init__(self, scenario: dict):
        self.choices = [_FakeChoice(scenario)]


class _FakeChoice:
    """模拟 choices[0]：持有 finish_reason 和 message。"""

    def __init__(self, scenario: dict):
        self.finish_reason = scenario["finish_reason"]
        self.message = _FakeMessage(scenario)


class _FakeMessage:
    """模拟 message：要么是纯文本回答，要么带 tool_calls 请求。"""

    def __init__(self, scenario: dict):
        self.content = scenario.get("content", "")
        self.tool_calls = [_FakeToolCall(tc) for tc in scenario.get("tool_calls", [])] or None


class _FakeToolCall:
    """模拟单个工具调用请求：id + function(name + arguments)。"""

    def __init__(self, tc: dict):
        self.id = tc["id"]
        self.type = "function"
        self.function = _FakeFunction(tc["name"], tc["arguments"])


class _FakeFunction:
    """模拟 function：name 是工具名，arguments 是 JSON 字符串形式的参数。"""

    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


async def test_chat_turn_executes_tool_then_answers(monkeypatch):
    """验证完整工具回合：请求带工具菜单 → 执行 get_time → 结果回填 → 二次请求 → 最终回答。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted=[
        {"finish_reason": "tool_calls",
         "tool_calls": [{"id": "call_1", "name": "get_time", "arguments": "{}"}]},
        {"finish_reason": "stop", "content": "现在是 2026-09-25 14:30:00。"},
    ])
    session = Session()

    answer = await chat_turn(client, session, "现在几点了？")

    assert answer == "现在是 2026-09-25 14:30:00。"
    # 第 1 次请求：带上了工具菜单
    assert client.captured_calls[0]["tools"] == [GET_TIME_SCHEMA]
    # 第 2 次请求：历史里带着工具结果——模型"看到"结果，靠的就是这次重发
    second_messages = client.captured_calls[1]["messages"]
    assert second_messages[2]["role"] == "tool"
    assert second_messages[2]["tool_call_id"] == "call_1"
    # 真正的 get_time 确实被执行了：结果是 19 个字符的时间串（YYYY-MM-DD HH:MM:SS）
    assert len(second_messages[2]["content"]) == 19
    # 回合结束后的完整历史：问 → 请求调用 → 工具结果 → 最终回答
    assert [m["role"] for m in session.messages] == ["user", "assistant", "tool", "assistant"]


async def test_chat_turn_plain_answer_without_tools(monkeypatch):
    """验证普通回合不受影响：模型不想要工具时，一次请求直接回答。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted=[
        {"finish_reason": "stop", "content": "你好！"},
    ])
    session = Session()

    answer = await chat_turn(client, session, "你好")

    assert answer == "你好！"
    assert len(client.captured_calls) == 1
    assert [m["role"] for m in session.messages] == ["user", "assistant"]
