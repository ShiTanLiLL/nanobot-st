"""工具基类与注册表：加一个新工具 = 新建一个类文件 + 注册一行。"""

import json
from abc import ABC, abstractmethod


class Tool(ABC):
    """所有工具的抽象基类：一份"自带说明书"的能力。

    子类只要填好四样东西：name（工具名）、description（说明）、
    parameters（参数的 JSON Schema）、execute（真正干活的函数），
    注册表就能自动生成工具菜单、自动按名分发——不再需要 if/elif。
    """

    name: str = ""
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具，返回结果文本（给模型看）。参数由注册表解析后按关键字传入。"""


class ToolRegistry:
    """工具注册表：登记所有工具，统一提供"菜单"与"按名分发"两样服务。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """登记一个工具（以它的 name 为键）。"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名字找工具；找不到返回 None。"""
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        """生成发给模型的工具菜单：把每个工具的"类属性"拼装成标准说明书。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments_json: str) -> str:
        """按名找到工具并执行：解析参数 JSON → 调用它的 execute → 返回结果文本。

        名字不认识、或参数不是合法 JSON 时，返回一句给模型看的提示（不崩溃）。
        """
        tool = self.get(name)
        if tool is None:
            return f"未知工具：{name}"
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError:
            return f"工具 {name} 的参数不是合法 JSON：{arguments_json}"
        return tool.execute(**arguments)
