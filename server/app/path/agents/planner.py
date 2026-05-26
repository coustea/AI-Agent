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
为他们设计一条最高效的学习路径（Course Path）。

输出规范：
1. 请提供一个精心设计的宏观课程标题。
2. adjustment_rationale 必须是字符串数组，每项写出一条基于画像或学习输入的调整依据。
3. confidence 必须是 0-100 的整数百分比。
4. 设计宏观的阶段骨架（stages），例如可以分为 4-6 个阶段（如基础入门、核心进阶、实战演练等），让学生能看到整体进度的全局预期。
5. 为所有阶段生成具体学习节点（nodes），后端会按 prerequisites 动态解锁；不要只返回第一个阶段。
6. 每个生成的节点应该是一个不可再分的最小知识点或能力点，明确指出前置依赖（prerequisites），形成拓扑结构。
"""

    async def generate_plan(self, request: GeneratePathRequest, profile: dict[str, Any]) -> AgentCoursePathPlan:
        """执行路径规划。"""
        logger.info(f"PathPlannerAgent 开始规划路径 - Topic: {request.topic}")
        
        profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
        current_knowledge_json = json.dumps(request.current_knowledge, ensure_ascii=False, indent=2)
        preferences_json = json.dumps(request.preferences, ensure_ascii=False, indent=2)
        
        human_content = f"""
请为我规划学习路径：

### 1. 学习目标
- 主题: {request.topic}
- 目标: {request.goal}

### 2. 用户当前画像 (请参考其中的已有技能和薄弱点，调整节点难度和重点)
```json
{profile_json}
```

### 3. 本次请求补充的已有知识
```json
{current_knowledge_json}
```

### 4. 本次请求补充的学习偏好
```json
{preferences_json}
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
