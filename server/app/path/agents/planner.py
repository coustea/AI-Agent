import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.infra.llm import get_llm
from app.path.schemas import AgentCoursePathPlan, GeneratePathRequest


class PathPlannerAgent:
    """课程级学习路径规划智能体。
    根据用户的学习目标和当前的画像，规划出详细的节点路线图。
    该类为纯 Agent 实现，不依赖于数据库。
    """

    def __init__(self):
        self.llm = get_llm()
        
        self.system_prompt = """你是一个世界顶级的课程教研专家与学习路径规划师。
你的任务是根据用户的学习目标和他们的个人画像（包含技术栈、薄弱点、偏好等），
为他们设计一条最高效的微型课程学习路径（Course Path）。

输出规范：
1. 请提供一个精心设计的宏观标题。
2. 解释你的规划思路（adjustment_rationale）。
3. 设计详细的节点列表（nodes）。每个节点应该是一个不可再分的最小知识点或能力点。
4. 明确指出节点之间的前置依赖（prerequisites），从而形成一张拓扑学习图（Course Atlas）。
5. 难度逐步递进（beginner -> intermediate -> advanced）。
"""

    async def generate_plan(self, request: GeneratePathRequest, profile: dict[str, Any]) -> AgentCoursePathPlan:
        """执行路径规划。"""
        logger.info(f"PathPlannerAgent 开始规划路径 - Topic: {request.topic}")
        
        profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
        
        human_content = f"""
请为我规划学习路径：

### 1. 学习目标
- 主题: {request.topic}
- 目标: {request.goal}

### 2. 用户当前画像 (请参考其中的已有技能和薄弱点，调整节点难度和重点)
```json
{profile_json}
```

请使用 JSON 返回完整的规划结果。
"""
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=human_content)
        ]
        
        try:
            result = await self.llm.ainvoke_json(AgentCoursePathPlan, messages)
            if not isinstance(result, AgentCoursePathPlan):
                raise ValueError("Model failed to output strictly matched AgentCoursePathPlan")
            
            logger.info(f"PathPlannerAgent 规划成功，生成了 {len(result.nodes)} 个节点")
            return result
            
        except Exception as e:
            logger.error(f"PathPlannerAgent 路径规划失败: {str(e)}")
            raise e
