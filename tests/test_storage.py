"""第 5 课测试：会话的保存与恢复（JSONL 持久化）。"""

import json

from nanobot_st import storage
from nanobot_st.session import Session
from nanobot_st.storage import load_session, save_session


def _use_tmp_dir(monkeypatch, tmp_path):
    """把存储目录重定向到 pytest 临时目录——测试绝不碰真实数据。"""
    monkeypatch.setattr(storage, "SESSIONS_DIR", tmp_path)


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    """验证：保存后重新加载，会话名、消息一条不少、原样恢复。"""
    _use_tmp_dir(monkeypatch, tmp_path)
    session = Session(name="work")
    session.add_user("你好")
    session.add_assistant("你也好")
    session.messages.append(
        {"role": "tool", "tool_call_id": "c1", "name": "get_time", "content": "2026-09-26 10:00:00"}
    )

    save_session(session)
    loaded = load_session("work")

    assert loaded is not None
    assert loaded.name == "work"
    assert loaded.messages == session.messages
    assert loaded.created_at == session.created_at


def test_load_missing_session_returns_none(monkeypatch, tmp_path):
    """验证：没有存过盘的会话名返回 None（调用方据此新建会话）。"""
    _use_tmp_dir(monkeypatch, tmp_path)
    assert load_session("never_saved") is None


def test_load_skips_corrupt_lines(monkeypatch, tmp_path):
    """验证：文件里混有损坏行时跳过它，好行照常恢复——半份历史好过整个打不开。"""
    _use_tmp_dir(monkeypatch, tmp_path)
    lines = [
        json.dumps({"_type": "metadata", "name": "broken",
                    "created_at": "2026-01-01T00:00:00", "message_count": 2}),
        json.dumps({"role": "user", "content": "第一条"}, ensure_ascii=False),
        "{这不是合法JSON",
        json.dumps({"role": "assistant", "content": "第二条"}, ensure_ascii=False),
    ]
    (tmp_path / "broken.jsonl").write_text("\n".join(lines), encoding="utf-8")

    loaded = load_session("broken")

    assert [m["content"] for m in loaded.messages] == ["第一条", "第二条"]
