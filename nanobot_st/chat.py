"""第一次对话：把一个问题发给大模型，拿回回答。"""

import os
import sys

from openai import OpenAI


def resolve_model() -> str:
    """从环境变量读取要用的模型名；没设置时报错并给出操作指引。"""
    model = os.environ.get("NANOBOT_ST_MODEL")
    if not model:
        raise RuntimeError(
            "还没有设置模型名。请先执行：export NANOBOT_ST_MODEL=deepseek-chat "
            "（或你所使用服务的模型名）"
        )
    return model


def make_client() -> OpenAI:
    """根据环境变量创建 OpenAI 客户端。

    用到的环境变量（openai SDK 会自动读取，无需手动传参）：
    - OPENAI_API_KEY  密钥
    - OPENAI_BASE_URL 服务地址；不设置就用 OpenAI 官方，
      设置成兼容服务的地址即可使用 DeepSeek、智谱、Ollama 等。
    """
    return OpenAI()


def ask_question(client: OpenAI, question: str) -> str:
    """向 AI 提一个问题，返回回答文本。

    client:   由调用方传入的客户端——真实运行传 make_client() 的产物，
              测试时传 FakeClient，这样测试不花钱也不碰网络。
    question: 用户的问题字符串。
    """
    response = client.chat.completions.create(
        model=resolve_model(),
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content


def main() -> None:
    """命令行入口：把命令行参数拼成问题，打印 AI 的回答。"""
    question = " ".join(sys.argv[1:]).strip() or input("你想问什么？")
    print(ask_question(make_client(), question))


if __name__ == "__main__":
    main()
