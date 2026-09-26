"""第 4 课测试：工具注册表体系（基类、菜单生成、按名分发、防御）。"""

from nanobot_st.tools import builtin_registry


def test_registry_generates_menu_for_all_builtin_tools():
    """验证：出厂注册表能自动生成全部内置工具的标准说明书。"""
    schemas = builtin_registry().schemas()
    names = [s["function"]["name"] for s in schemas]
    assert names == ["get_time", "calculator", "random_number"]
    for s in schemas:
        assert s["type"] == "function"
        assert s["function"]["description"]
        assert "parameters" in s["function"]


def test_registry_executes_calculator_with_arguments():
    """验证：带参数的工具被正确分发执行——JSON 字符串解析成关键字参数。"""
    result = builtin_registry().execute(
        "calculator", '{"a": 12, "b": 34, "operator": "*"}'
    )
    assert result == "408"


def test_registry_rejects_unknown_tool():
    """验证：工具名不认识时不崩溃，返回给模型看的提示。"""
    assert "未知工具" in builtin_registry().execute("no_such_tool", "{}")


def test_registry_rejects_invalid_json_arguments():
    """验证：参数不是合法 JSON 时同样温柔拦截。"""
    assert "不是合法 JSON" in builtin_registry().execute("calculator", "{oops}")
