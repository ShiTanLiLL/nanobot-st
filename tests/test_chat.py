"""第 1 课测试：不花真钱，用假客户端验证 ask_question 的行为。"""

from nanobot_st.chat import ask_question


class FakeClient:
    """假装是 OpenAI 客户端：外观与真客户端一致（都有 .chat.completions.create）。

    它做两件事：
    1. 把 create 收到的参数记进 captured，供测试断言"我们发出去的格式对不对"；
    2. 返回一个预设回答 answer，其嵌套形状与真实响应一致。
    """

    def __init__(self, answer: str = "这是预设的回答"):
        self.answer = answer
        self.captured: dict = {}
        self.chat = _FakeChat(self)


class _FakeChat:
    """模拟 client.chat 这一层，只为提供 .completions 属性。"""

    def __init__(self, owner: "FakeClient"):
        self.completions = _FakeCompletions(owner)


class _FakeCompletions:
    """模拟 client.chat.completions 这一层，提供 create() 方法。"""

    def __init__(self, owner: "FakeClient"):
        self._owner = owner

    def create(self, *, model, messages, **kwargs):
        """记录本次请求参数，并返回形状与真实响应一致的假对象。"""
        self._owner.captured = {"model": model, "messages": messages}
        return _FakeResponse(self._owner.answer)


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


def test_ask_question_sends_user_message(monkeypatch):
    """验证：问题被装进标准 user 信封发出，模型名来自环境变量。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient()

    ask_question(client, "你好")

    assert client.captured["model"] == "fake-model"
    assert client.captured["messages"] == [{"role": "user", "content": "你好"}]


def test_ask_question_returns_answer_text(monkeypatch):
    """验证：能从嵌套的响应结构里正确取出回答文本。"""
    monkeypatch.setenv("NANOBOT_ST_MODEL", "fake-model")
    client = FakeClient(answer="今天天气不错")

    assert ask_question(client, "今天天气如何") == "今天天气不错"
