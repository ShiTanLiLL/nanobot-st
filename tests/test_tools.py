"""第 3 课测试：工具模块自身的单元测试。"""

from nanobot_st.tools import execute_tool, get_time


def test_get_time_returns_19_char_timestamp():
    """验证：get_time 返回 YYYY-MM-DD HH:MM:SS 格式的 19 字符时间串。"""
    assert len(get_time()) == 19


def test_execute_tool_dispatches_by_name():
    """验证：execute_tool 能按名字找到工具并执行（空参数也走一遍 JSON 解析）。"""
    result = execute_tool("get_time", "{}")
    assert len(result) == 19


def test_execute_tool_rejects_unknown_name():
    """验证：工具名不认识时不崩溃，返回一句给模型看的提示。"""
    assert "未知工具" in execute_tool("no_such_tool", "{}")
