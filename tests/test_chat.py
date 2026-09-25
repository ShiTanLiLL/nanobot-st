"""第 2 课测试：用假客户端验证"带着历史的对话回合"。"""

from nanobot_st.chat import chat_turn
from nanobot_st.session import Session


class FakeClient:
    """假装是 AsyncOpenAI 客户端：外观与真客户端一致（都有 .chat.completions.create）。

    相比第 1 课的假客户端，它升级了三处：
    1. create 变成 async（配合本课的异步改造）；
    2. 支持按顺序"播放"多份预设回答（scripted_answers）；
    3. 每次调用记录一份当时消息列表的快照（captured_calls），
       防止会话后续追加的消息倒灌进历史记录。
    """

    def __init__(self, scripted_answers: list[str]):
        self._scripted = list(scripted_answers)
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

    async def create(self, *, model, messages, **kwargs):
        """按剧本返回下一份回答，并记录本次请求参数的快照。"""
        answer = self._owner._scripted.pop(0)
        # messages 是会话里那个"活的"列表——必须当场拷贝一份存档，
        # 否则之后的对话会倒灌进来，把这次的历史记录改得面目全非。
        snapshot = [dict(m) for m in messages]
        self._owner.captured_calls.append({"model": model, "messages": snapshot})
        return _FakeResponse(answer)


class _FakeResponse:
    """模拟响应对象：和真的一样，是 choices 列表层层嵌套的形状。"""

    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeChoice:
    """模拟 choices 里的一项，持有 .message。"""

    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeMessage:
    """模拟 message，持有 .content——回答文本最终藏在这。"""

    def __init__(self, content: str):
        self.content = content


async def test_chat_turn_carries_history(monkeypatch):
    """验证：第二回合发出的请求带上了第一回合的问答，且两回合回答正确返回。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted_answers=["你好！很高兴见到你。", "你刚才说的是'你好'。"])
    session = Session()

    first = await chat_turn(client, session, "你好")
    second = await chat_turn(client, session, "我刚才说的第一句话是什么？")

    assert first == "你好！很高兴见到你。"
    assert second == "你刚才说的是'你好'。"
    # 第 1 次请求：信封里只有第 1 句问话
    assert client.captured_calls[0]["messages"] == [
        {"role": "user", "content": "你好"},
    ]
    # 第 2 次请求：信封变厚了——上一问、上一答、这一问，全都在
    assert client.captured_calls[1]["messages"] == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！很高兴见到你。"},
        {"role": "user", "content": "我刚才说的第一句话是什么？"},
    ]


async def test_chat_turn_records_whole_dialogue_in_session(monkeypatch):
    """验证：一个回合结束后，问与答都按顺序留在了会话历史里。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(scripted_answers=["第一答"])
    session = Session()

    await chat_turn(client, session, "第一问")

    assert session.messages == [
        {"role": "user", "content": "第一问"},
        {"role": "assistant", "content": "第一答"},
    ]
