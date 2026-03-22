"""
ReAct Agent 主入口

测试 Agent 的完整工作流：Retrieve → Think → Plan → Act → Reflect
"""
import asyncio
import os
import sys
from pathlib import Path

# 将 src 目录加入路径
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from agent.core import Agent
from agent.tools import get_tools

load_dotenv()


async def main():
    # 设置控制台输出编码
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    print("\n" + "=" * 60)
    print("🚀 ReAct Agent 测试")
    print("=" * 60 + "\n")

    # 1. 初始化 LLM
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="qwen2.5:14b",
        temperature=0.7,
    )

    prompts_path = str(src_dir / "agent" / "prompts")
    skills_path = str(src_dir / "agent" / "skills")

    # 2. 初始化 Agent
    agent = Agent(
        llm=llm,
        tools=get_tools(),
        prompts_dir=prompts_path,
        skills_dir=skills_path,
        system_prompt="你是一个温柔、善良、贴心的智能助手，用清新的语气帮助用户解决问题。"
    )

    # 3. 打印配置
    print(agent.print_agent_config())
    print("-" * 60)

    # 4. 定义任务
    task = "告诉我长春市今天的天气，并且帮我制定一份长春市半日游的旅游计划！"
    print(f"\n👤 用户问题: {task}\n")

    # 5. 运行 Agent
    print("🤔 正在思考中...\n")

    try:
        # 使用流式输出查看过程
        async for output in agent.graph.astream({
            "task": task,
            "messages": [HumanMessage(content=task)],
            "current_sop": ""
        }):
            for node_name, state_update in output.items():
                # 显示节点执行情况
                if node_name == "retrieve":
                    print("📚 [1/5] 检索业务知识库...")
                elif node_name == "think":
                    if "messages" in state_update and state_update["messages"]:
                        content = state_update["messages"][-1].content
                        # 只显示思考的前100字符
                        preview = content[:100].replace("\n", " ")
                        print(f"🤔 [2/5] 思考: {preview}...")
                elif node_name == "plan":
                    if "messages" in state_update and state_update["messages"]:
                        content = state_update["messages"][-1].content
                        if "🛠️" in content:
                            print(f"🛠️ [3/5] 规划动作: 准备调用工具")
                        elif "✅" in content:
                            print(f"✅ [5/5] 生成最终答复")
                elif node_name == "act":
                    print("⚡ [4/5] 执行工具获取数据...")
                elif node_name == "reflect":
                    print("👀 [反思] 评估结果...")

        # 获取最终状态
        final_state = await agent.graph.ainvoke({
            "task": task,
            "messages": [HumanMessage(content=task)],
            "current_sop": ""
        })

        # 提取最终答案
        if final_state["messages"]:
            last_msg = final_state["messages"][-1]
            answer = last_msg.content

            # 去掉格式前缀
            if answer.startswith("✅ [最终答复]:\n"):
                answer = answer.replace("✅ [最终答复]:\n", "", 1)

            print("\n" + "=" * 60)
            print(f"✨ 最终答案:")
            print("=" * 60)
            print(f"\n{answer}\n")

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
