"""内存会话：用一个消息列表记住当前这轮对话的全部历史。"""

from datetime import datetime


class Session:
    """一个会话 = 一份不断变长的消息列表。

    它是 AI"记忆"的载体：每次请求把整个列表发给模型，
    模型看起来"记得上文"，其实是我们每次都把历史重发了一遍。
    name 是会话名（也是存盘文件名）；created_at 记录诞生时刻。
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.messages: list[dict] = []

    def add_user(self, text: str) -> None:
        """把用户说的话装进标准信封，追加到历史末尾。"""
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        """把 AI 的回答追加到历史末尾。"""
        self.messages.append({"role": "assistant", "content": text})

    def add_assistant_tool_calls(self, tool_calls: list[dict]) -> None:
        """把"AI 请求调用工具"这条消息记入历史（role 仍是 assistant，但带 tool_calls）。"""
        self.messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})

    def add_tool_result(self, tool_call_id: str, name: str, result: str) -> None:
        """把一条工具执行结果记入历史。

        tool_call_id 必须与"请求调用"时的 id 一致——协议靠这个 id
        把"哪一次请求"和"哪一份结果"配成一对。
        """
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "name": name, "content": result}
        )
