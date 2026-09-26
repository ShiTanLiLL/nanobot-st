"""第 7 课测试：流式对话回合（假客户端按剧本"挤牙膏"）。"""

from nanobot_st.chat import chat_turn
from nanobot_st.session import Session


class FakeClient:
    """假装是 AsyncOpenAI 客户端：create 返回一个可 async for 的假流。

    剧本每一幕有两种戏码（与真实流式 API 一致）：
    - {"finish_reason": "stop", "content": "..."}            → 文本被拆成小块陆续吐出
    - {"finish_reason": "tool_calls", "tool_calls": [...]}   → 参数被拆成碎片陆续吐出
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

    async def create(self, *, model, messages, tools=None, stream=False, **kwargs):
        """播放剧本下一幕：记录请求快照，返回一串假流式块。"""
        scenario = self._owner._scripted.pop(0)
        snapshot = [dict(m) for m in messages]  # 快照：防止历史倒灌
        self._owner.captured_calls.append(
            {"model": model, "messages": snapshot, "tools": tools}
        )
        return _FakeStream(scenario)


def _build_chunks(scenario: dict) -> list:
    """把一幕剧本拆成一串流式块，模拟真实 API 的"挤牙膏"。

    文本按 2 个字符一块拆；工具调用参数从中间劈成两半——
    专门考验引擎的碎片聚合能力。
    """
    chunks = []
    if scenario["finish_reason"] == "stop":
        content = scenario.get("content", "")
        pieces = [content[i : i + 2] for i in range(0, len(content), 2)] or [""]
        for piece in pieces:
            chunks.append(_FakeChunk(delta=_FakeDelta(content=piece), finish_reason=None))
    else:
        for index, tc in enumerate(scenario["tool_calls"]):
            args = tc["arguments"]
            mid = max(1, len(args) // 2)
            chunks.append(_FakeChunk(
                delta=_FakeDelta(tool_calls=[_FakeChunkToolCall(
                    index=index, id=tc["id"], name=tc["name"], arguments=args[:mid])]),
                finish_reason=None))
            if args[mid:]:
                chunks.append(_FakeChunk(
                    delta=_FakeDelta(tool_calls=[_FakeChunkToolCall(
                        index=index, arguments=args[mid:])]),
                    finish_reason=None))
    chunks.append(_FakeChunk(delta=_FakeDelta(), finish_reason=scenario["finish_reason"]))
    return chunks


class _FakeStream:
    """模拟 SDK 的流式响应对象：支持 async for 逐块消费。"""

    def __init__(self, scenario: dict):
        self._chunks = _build_chunks(scenario)

    def __aiter__(self):
        """async for 的入口：把自己交出去当迭代器。"""
        return self

    async def __anext__(self):
        """交出下一块；没有下一块时抛 StopAsyncIteration 结束循环。"""
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class _FakeChunk:
    """模拟一个流式块：choices 列表。"""

    def __init__(self, delta, finish_reason):
        self.choices = [_FakeChunkChoice(delta=delta, finish_reason=finish_reason)]


class _FakeChunkChoice:
    """模拟块里的 choices[0]：delta 增量 + finish_reason（最后一块才有）。"""

    def __init__(self, delta, finish_reason):
        self.delta = delta
        self.finish_reason = finish_reason


class _FakeDelta:
    """模拟增量：本块新到的一小段文本，或一小片工具调用碎片。"""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeChunkToolCall:
    """模拟工具调用碎片：第一片带 id 和 name，后续片只有 arguments 补充。"""

    def __init__(self, index, id=None, name=None, arguments=""):
        self.index = index
        self.id = id
        self.function = _FakeFunctionFragment(name, arguments)


class _FakeFunctionFragment:
    """模拟 function 碎片：name 只在第一片出现，arguments 是本轮新增的一小段。"""

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


async def test_chat_turn_executes_tool_then_answers(monkeypatch):
    """验证完整工具回合（含碎片聚合）：参数劈成两半也能拼回去并正确执行。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted=[
        {"finish_reason": "tool_calls",
         "tool_calls": [{"id": "call_1", "name": "get_time", "arguments": "{}"}]},
        {"finish_reason": "stop", "content": "现在是 2026-09-25 14:30:00。"},
    ])
    session = Session()

    answer = await chat_turn(client, session, "现在几点了？")

    assert answer == "现在是 2026-09-25 14:30:00。"
    # 第 1 次请求：首条是 system 人设，且带上了完整的工具菜单（由注册表自动生成）
    first_messages = client.captured_calls[0]["messages"]
    assert first_messages[0]["role"] == "system"
    tool_names = [t["function"]["name"] for t in client.captured_calls[0]["tools"]]
    assert tool_names == ["get_time", "calculator", "random_number"]
    # 第 2 次请求：历史里带着工具结果——模型"看到"结果，靠的就是这次重发
    # （序列为 [system, user 问, assistant 便签, tool 结果]）
    second_messages = client.captured_calls[1]["messages"]
    assert second_messages[2]["role"] == "assistant"
    assert second_messages[2]["tool_calls"][0]["id"] == "call_1"
    assert second_messages[3]["role"] == "tool"
    assert second_messages[3]["tool_call_id"] == "call_1"
    # 19 字符的时间串（YYYY-MM-DD HH:MM:SS）
    assert len(second_messages[3]["content"]) == 19
    # 回合结束后的完整历史：问 → 请求调用 → 工具结果 → 最终回答
    assert [m["role"] for m in session.messages] == ["user", "assistant", "tool", "assistant"]


async def test_chat_turn_handles_multiple_tool_calls_in_one_round(monkeypatch):
    """验证一轮两只手：两个工具的碎片各自聚合、按 index 排序、按序回填。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted=[
        {"finish_reason": "tool_calls", "tool_calls": [
            {"id": "call_1", "name": "calculator",
             "arguments": '{"a": 12, "b": 34, "operator": "*"}'},
            {"id": "call_2", "name": "random_number",
             "arguments": '{"minimum": 1, "maximum": 6}'},
        ]},
        {"finish_reason": "stop", "content": "12 乘 34 等于 408；骰子掷出了 3。"},
    ])
    session = Session()

    answer = await chat_turn(client, session, "算一下 12*34，再掷一个骰子")

    assert answer == "12 乘 34 等于 408；骰子掷出了 3。"
    second_messages = client.captured_calls[1]["messages"]
    # 便签里有两次调用，其后跟着两份结果，顺序与配对都正确
    # （序列为 [system, user 问, assistant 便签, tool 结果1, tool 结果2]）
    assert second_messages[2]["tool_calls"][0]["id"] == "call_1"
    assert second_messages[2]["tool_calls"][1]["id"] == "call_2"
    assert second_messages[3]["tool_call_id"] == "call_1"
    assert second_messages[3]["content"] == "408"          # 碎片参数拼回后计算器：确定值
    assert second_messages[4]["tool_call_id"] == "call_2"
    assert int(second_messages[4]["content"]) in range(1, 7)  # 骰子：1~6 之间
    assert [m["role"] for m in session.messages] == [
        "user", "assistant", "tool", "tool", "assistant",
    ]


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


async def test_chat_turn_streams_deltas_in_order(monkeypatch):
    """验证打字机链路：回调按到达顺序收到文本片段，聚合后等于最终回答。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted=[
        {"finish_reason": "stop", "content": "你好！很高兴见到你。"},
    ])
    session = Session()
    received: list[str] = []

    answer = await chat_turn(
        client, session, "打个招呼", on_content_delta=received.append
    )

    # 文本按 2 字一块"挤牙膏"，回调收到的顺序 = 到达顺序
    assert received == ["你好", "！很", "高兴", "见到", "你。"]
    assert answer == "你好！很高兴见到你。"
    # 会话里入库的是聚合后的完整文本（不是碎片）
    assert session.messages[-1]["content"] == "你好！很高兴见到你。"
