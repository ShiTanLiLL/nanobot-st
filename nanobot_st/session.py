"""内存会话：用一个消息列表记住当前这轮对话的全部历史。"""


class Session:
    """一个会话 = 一份不断变长的消息列表。

    它是 AI"记忆"的载体：每次请求把整个列表发给模型，
    模型看起来"记得上文"，其实是我们每次都把历史重发了一遍。
    注意：它只存在内存里，程序一退出就消失（第 5 课解决）。
    """

    def __init__(self):
        self.messages: list[dict] = []

    def add_user(self, text: str) -> None:
        """把用户说的话装进标准信封，追加到历史末尾。"""
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        """把 AI 的回答追加到历史末尾。"""
        self.messages.append({"role": "assistant", "content": text})
