"""和 AI 聊天：带着全部历史的异步对话。"""

import asyncio
import os

from openai import AsyncOpenAI

from nanobot_st.session import Session


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
    """进行一个对话回合：把提问记入历史 → 带着全部历史请求模型 → 回答也记入历史。

    client:   由调用方传入的异步客户端（真实运行传 make_client() 的产物，
              测试时传 FakeClient，不花钱不碰网）。
    session:  本次对话的会话，历史就存在它身上。
    question: 用户这一回合的提问。
    """
    session.add_user(question)
    response = await client.chat.completions.create(
        model=resolve_model(),
        messages=session.messages,
    )
    answer = response.choices[0].message.content
    session.add_assistant(answer)
    return answer


async def main() -> None:
    """终端聊天入口：循环"你一句、我一句"，直到输入 exit 退出。"""
    client = make_client()
    session = Session()
    print("开始聊天吧（输入 exit 退出）")
    while True:
        question = input("你：").strip()
        if not question:
            continue
        if question in ("exit", "quit", "退出"):
            print("下次再聊～")
            break
        answer = await chat_turn(client, session, question)
        print(f"AI：{answer}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n下次再聊～")
