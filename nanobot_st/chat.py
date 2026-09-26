"""和 AI 聊天：带着全部历史的异步对话（现在 AI 能用工具了）。"""

import asyncio
import os

from openai import AsyncOpenAI

from nanobot_st.session import Session
from nanobot_st.storage import load_session, save_session
from nanobot_st.tools import REGISTRY

# 一回合内最多让模型要几轮工具：防止异常情况下无限循环白烧钱
MAX_TOOL_ROUNDS = 10


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


async def chat_turn(client: AsyncOpenAI, session: Session, question: str) -> str:
    """进行一个对话回合（其中可能包含多轮工具调用）。

    工具循环（agent 的心脏）：
    请求模型 → 模型要工具就执行并把结果回填、再请求模型 → 直到给出最终回答。
    """
    session.add_user(question)
    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=resolve_model(),
            messages=session.messages,
            tools=REGISTRY.schemas(),
        )
        choice = response.choices[0]
        if choice.finish_reason == "tool_calls":
            # 第一步：把"AI 请求调用工具"原样记入历史
            #（SDK 给的是对象，先转成标准 dict 信封，历史里存的都是信封）
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
            session.add_assistant_tool_calls(tool_calls)
            # 第二步：逐个执行工具，把每份结果也记入历史（分发交给注册表）
            for tc in tool_calls:
                result = REGISTRY.execute(tc["function"]["name"], tc["function"]["arguments"])
                session.add_tool_result(tc["id"], tc["function"]["name"], result)
            # 第三步：带着工具结果把全部历史再发给模型，看它还有什么要说的
            continue
        # finish_reason == "stop"：模型给出最终文本回答，回合结束
        session.add_assistant(choice.message.content)
        return choice.message.content
    raise RuntimeError(f"模型连续 {MAX_TOOL_ROUNDS} 轮请求工具，已强制停止本回合")


async def main() -> None:
    """终端聊天入口：启动时恢复上次会话，每回合落盘，重启不失忆。"""
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
        answer = await chat_turn(client, session, question)
        save_session(session)
        print(f"AI：{answer}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n下次再聊～")
