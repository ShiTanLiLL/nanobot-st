"""和 AI 聊天：流式对话引擎——边生成边输出，工具循环照旧。"""

import asyncio
import os

from openai import AsyncOpenAI

from nanobot_st.context import ContextBuilder
from nanobot_st.session import Session
from nanobot_st.storage import load_session, save_session
from nanobot_st.tools import REGISTRY

# 一回合内最多让模型要几轮工具：防止异常情况下无限循环白烧钱
MAX_TOOL_ROUNDS = 10

# 上下文组装器（人设 + 截断），整个程序共用一份
CONTEXT_BUILDER = ContextBuilder()


def resolve_model() -> str:
    """从环境变量读取要用的模型名；没设置时报错并给出操作指引。"""
    model = os.environ.get("NANOBOT_ST_MODEL")
    if not model:
        raise RuntimeError(
            "还没有设置模型名。请先执行：export NANOBOT_ST_MODEL=deepseek-chat "
            "（或你所使用服务的模型名）"
        )
    return model


def make_client() -> AsyncOpenAI:
    """根据环境变量创建异步 OpenAI 客户端。

    用到的环境变量（openai SDK 会自动读取，无需手动传参）：
    - OPENAI_API_KEY  密钥
    - OPENAI_BASE_URL 服务地址；不设置就用 OpenAI 官方，
      设置成兼容服务的地址即可使用 DeepSeek、智谱、Ollama 等。
    """
    return AsyncOpenAI()


async def request_model(
    client: AsyncOpenAI, messages: list[dict], on_content_delta=None
) -> dict:
    """发起一次流式请求，把各式各样的流式块聚合成统一结果。

    流式响应像挤牙膏：文本一小段一小段地来（delta），工具调用的
    参数也是一小片一小片地来。本函数边收边做两件事：
    1. 文本增量随手通过回调 on_content_delta(片段) 交出去（打字机效果靠它）；
    2. 把碎片拼回完整的东西，最后返回统一结果：
       {"finish_reason": ..., "content": 完整文本, "tool_calls": [标准 dict 信封]}
    """
    stream = await client.chat.completions.create(
        model=resolve_model(),
        messages=messages,
        tools=REGISTRY.schemas(),
        stream=True,
    )
    content_parts: list[str] = []
    tool_calls_acc: dict[int, dict] = {}  # 工具调用暂存间：index → 碎片累积
    finish_reason = None
    async for chunk in stream:
        if not chunk.choices:
            continue  # 个别服务会发一个没有正文的空块
        choice = chunk.choices[0]
        delta = choice.delta
        piece = delta.content
        if piece:
            content_parts.append(piece)
            if on_content_delta:
                on_content_delta(piece)
        for tc in delta.tool_calls or []:
            slot = tool_calls_acc.setdefault(
                tc.index, {"id": "", "name": "", "arguments": ""}
            )
            if tc.id:
                slot["id"] = tc.id
            if tc.function and tc.function.name:
                slot["name"] = tc.function.name
            if tc.function and tc.function.arguments:
                slot["arguments"] += tc.function.arguments
        if choice.finish_reason:
            finish_reason = choice.finish_reason
    tool_calls = [
        {
            "id": slot["id"],
            "type": "function",
            "function": {"name": slot["name"], "arguments": slot["arguments"]},
        }
        for _, slot in sorted(tool_calls_acc.items())
    ]
    return {
        "finish_reason": finish_reason,
        "content": "".join(content_parts),
        "tool_calls": tool_calls,
    }


async def chat_turn(
    client: AsyncOpenAI, session: Session, question: str, on_content_delta=None
) -> str:
    """进行一个对话回合（可能含多轮工具调用），返回最终回答文本。

    on_content_delta: 可选回调，模型每吐出一段文字就调用它一次（打字机效果）。
    """
    session.add_user(question)
    for _ in range(MAX_TOOL_ROUNDS):
        result = await request_model(
            client, CONTEXT_BUILDER.build(session), on_content_delta=on_content_delta
        )
        if result["finish_reason"] == "tool_calls":
            # 把"AI 请求调用工具"记入历史（request_model 已聚合成标准信封）
            session.add_assistant_tool_calls(result["tool_calls"])
            # 逐个执行工具，结果记入历史（分发交给注册表）
            for tc in result["tool_calls"]:
                tool_result = REGISTRY.execute(
                    tc["function"]["name"], tc["function"]["arguments"]
                )
                session.add_tool_result(tc["id"], tc["function"]["name"], tool_result)
            # 带着工具结果把全部历史再发给模型，看它还有什么要说的
            continue
        # finish_reason == "stop"：最终文本回答，回合结束
        session.add_assistant(result["content"])
        return result["content"]
    raise RuntimeError(f"模型连续 {MAX_TOOL_ROUNDS} 轮请求工具，已强制停止本回合")


def print_delta(text: str) -> None:
    """流式打印回调：拿到一小段就立刻打出来（end='' 不换行，flush=True 立刻刷新）。"""
    print(text, end="", flush=True)


async def main() -> None:
    """终端聊天入口：启动恢复会话，回答逐字打出，每回合落盘。"""
    client = make_client()
    session = load_session("default") or Session("default")
    if session.messages:
        print(f"已恢复上次对话（{len(session.messages)} 条历史），继续聊（输入 exit 退出）")
    else:
        print("开始新的对话（输入 exit 退出）")
    while True:
        question = input("你：").strip()
        if not question:
            continue
        if question in ("exit", "quit", "退出"):
            print("下次再聊～（对话已保存）")
            break
        print("AI：", end="", flush=True)
        await chat_turn(client, session, question, on_content_delta=print_delta)
        print()  # 打字机已逐字输出完毕，这里只补一个换行收尾
        save_session(session)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n下次再聊～")
