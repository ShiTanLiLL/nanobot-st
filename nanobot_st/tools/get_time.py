"""工具：获取当前时间。"""

from datetime import datetime

from nanobot_st.tools.base import Tool


class GetTimeTool(Tool):
    """告诉模型现在几点了。"""

    name = "get_time"
    description = "获取当前的日期和时间。当用户询问现在几点、今天是几号时使用。"
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self) -> str:
        """返回当前本地时间，格式如 2026-09-25 14:30:00。"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
