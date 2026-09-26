"""工具包：所有内置工具与注册表。

加一个新工具的三步（再不用改任何旧代码）：
1. 新建一个文件，写一个 Tool 子类（填 name/description/parameters/execute）；
2. 在下面的 builtin_registry() 里登记一行；
3. 完了。菜单自动生成、分发自动完成。
"""

from nanobot_st.tools.base import Tool, ToolRegistry
from nanobot_st.tools.calculator import CalculatorTool
from nanobot_st.tools.get_time import GetTimeTool
from nanobot_st.tools.random_number import RandomNumberTool


def builtin_registry() -> ToolRegistry:
    """创建一个装好全部内置工具的注册表（出厂标配）。"""
    registry = ToolRegistry()
    registry.register(GetTimeTool())
    registry.register(CalculatorTool())
    registry.register(RandomNumberTool())
    return registry


# 整个程序共用的默认工具箱（第 12 课子代理需要"受限工具箱"时再升级为按需定制）
REGISTRY = builtin_registry()
