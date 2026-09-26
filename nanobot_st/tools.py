"""内置工具：AI 的"双手"。本课先只有一个——获取当前时间。"""

import json
from datetime import datetime

# 工具说明书（OpenAI tools 格式）：告诉模型"有哪些工具可用、怎么用"。
# parameters 用 JSON Schema 描述参数——get_time 不需要参数，所以是个空对象。
GET_TIME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前的日期和时间。当用户询问现在几点、今天是几号时使用。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

# 本次对话向模型开放的全部工具清单（发给模型的"工具菜单"）
TOOLS = [GET_TIME_SCHEMA]


def get_time() -> str:
    """返回当前本地时间，格式如 2026-09-25 14:30:00。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def execute_tool(name: str, arguments_json: str) -> str:
    """按工具名执行对应函数，返回结果文本（注意：这个文本是给模型看的）。

    arguments_json 是模型给的参数，永远是一段 JSON 字符串（即使没参数也是 "{}"），
    必须先解析成 dict 才能使用。
    """
    arguments = json.loads(arguments_json)
    if name == "get_time":
        return get_time(**arguments)
    return f"未知工具：{name}"
