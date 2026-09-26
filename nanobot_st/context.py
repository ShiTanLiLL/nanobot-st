"""上下文组装：固定人设（system prompt）+ 历史截断。"""

from nanobot_st.session import Session

# 固定人设：每次请求都作为第一条消息（system）发给模型
SYSTEM_PROMPT = """你是 shitan 的个人 AI 助手。
- 始终用简体中文回答，风格简洁、严谨
- 不确定的事要明说，不要编造
- 涉及数字计算时使用 calculator 工具，不要心算"""

# 历史最多带多少条消息（超出的从最老的开始丢弃）
MAX_HISTORY_MESSAGES = 60


class ContextBuilder:
    """把"人设 + 会话历史"组装成每次真正发给模型的消息列表。"""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT, max_history: int = MAX_HISTORY_MESSAGES):
        self.system_prompt = system_prompt
        self.max_history = max_history

    def build(self, session: Session) -> list[dict]:
        """产出 [system 人设] + [截断后的历史]；session 的原始历史不被修改。"""
        history = truncate_history(session.messages, self.max_history)
        return [{"role": "system", "content": self.system_prompt}, *history]


def truncate_history(messages: list[dict], keep_last: int) -> list[dict]:
    """只保留最近 keep_last 条历史，返回新列表（不动原列表）。

    铁律：不能把 assistant 便签截掉、却留下它的 tool 结果——
    "孤儿 tool 消息"是非法历史，API 会直接拒收。
    所以若切口正好落在 tool 结果上，就再多丢几条，直到切口安全。
    """
    if len(messages) <= keep_last:
        return list(messages)
    cut = messages[-keep_last:]
    safe_start = 0
    while safe_start < len(cut) and cut[safe_start].get("role") == "tool":
        safe_start += 1
    return cut[safe_start:]
