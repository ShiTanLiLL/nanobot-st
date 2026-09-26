"""会话持久化：把内存里的会话保存为 JSONL 文件，重启后恢复。"""

import json
import os
from pathlib import Path

from nanobot_st.session import Session

# 数据目录：项目根目录下的 data/（.gitignore 已忽略，永远不进 git）
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"


def session_path(name: str) -> Path:
    """会话名 → 对应的 JSONL 文件路径。"""
    return SESSIONS_DIR / f"{name}.jsonl"


def save_session(session: Session) -> None:
    """把整个会话原子写入文件：首行元数据 + 每行一条消息。

    "原子"指：先写进临时文件，全部写完后再用 os.replace 一步换成正式文件——
    中途断电/崩溃最多留下半个临时文件，正式文件永远是完整的一份。
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "_type": "metadata",
                "name": session.name,
                "created_at": session.created_at,
                "message_count": len(session.messages),
            },
            ensure_ascii=False,
        ),
        *[json.dumps(m, ensure_ascii=False) for m in session.messages],
    ]
    target = session_path(session.name)
    tmp = target.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, target)


def load_session(name: str) -> Session | None:
    """按名字从磁盘恢复会话；文件不存在返回 None；损坏行跳过不崩溃。"""
    path = session_path(name)
    if not path.exists():
        return None
    session = Session(name=name)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # 跳过损坏行：丢一条消息，好过整个会话打不开
            if record.get("_type") == "metadata":
                session.created_at = record["created_at"]
                continue
            session.messages.append(record)
    return session
