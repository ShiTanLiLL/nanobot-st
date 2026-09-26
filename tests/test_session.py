"""第 2 课测试：会话对象正确记录对话双方的消息。"""

from nanobot_st.session import Session


def test_session_records_dialogue_in_order():
    """验证：用户与 AI 的话按发生顺序、以标准信封格式存进历史。"""
    session = Session()
    session.add_user("你好")
    session.add_assistant("你也好")

    assert session.messages == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你也好"},
    ]


def test_session_starts_empty():
    """验证：新会话从空历史开始，有默认名字与诞生时间。"""
    session = Session()
    assert session.messages == []
    assert session.name == "default"
    assert session.created_at  # ISO 时间串非空
