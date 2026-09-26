"""工具：精确计算两个数的四则运算。"""

from nanobot_st.tools.base import Tool


class CalculatorTool(Tool):
    """模型心算大数字容易错，涉及计算时让它用这个工具。"""

    name = "calculator"
    description = "精确计算两个数的四则运算。涉及任何数字计算时都应使用本工具，不要心算。"
    parameters = {
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "第一个数"},
            "b": {"type": "number", "description": "第二个数"},
            "operator": {"type": "string", "enum": ["+", "-", "*", "/"], "description": "运算符"},
        },
        "required": ["a", "b", "operator"],
    }

    def execute(self, a: float, b: float, operator: str) -> str:
        """按运算符计算 a op b，返回结果文本；除以零等错误返回给模型看的提示。"""
        if operator == "+":
            return str(a + b)
        if operator == "-":
            return str(a - b)
        if operator == "*":
            return str(a * b)
        if operator == "/":
            if b == 0:
                return "错误：除数不能为 0"
            return str(a / b)
        return f"错误：不支持的运算符 {operator}"
