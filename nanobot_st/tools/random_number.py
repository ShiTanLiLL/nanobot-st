"""工具：在指定范围内掷骰子。"""

import random

from nanobot_st.tools.base import Tool


class RandomNumberTool(Tool):
    """取一个随机整数。"""

    name = "random_number"
    description = "在指定范围内生成一个随机整数（含两端）。需要抽签、掷骰子、随机选择时使用。"
    parameters = {
        "type": "object",
        "properties": {
            "minimum": {"type": "integer", "description": "范围下限（含）"},
            "maximum": {"type": "integer", "description": "范围上限（含）"},
        },
        "required": ["minimum", "maximum"],
    }

    def execute(self, minimum: int, maximum: int) -> str:
        """返回 [minimum, maximum] 闭区间内的一个随机整数文本。"""
        return str(random.randint(minimum, maximum))
