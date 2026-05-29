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

    async def adjust_plan(
        self,
        active_path: Any,
        completed_nodes: list[Any],
        remaining_nodes: list[Any],
        profile: dict[str, Any],
        feedback: str,
    ) -> AgentCoursePathPlan:
        """根据画像和反馈动态微调未完成的路径节点。"""
        logger.info(f"PathPlannerAgent 开始微调路径 - Path ID: {active_path.id}")

        completed_data = [
            {
                "node_id": n.node_id,
                "stage_id": n.stage_id,
                "title": n.title,
                "difficulty": n.difficulty,
                "mastery_target": n.mastery_target,
            }
            for n in completed_nodes
        ]

        remaining_data = [
            {
                "node_id": n.node_id,
                "stage_id": n.stage_id,
                "title": n.title,
                "prerequisites": n.prerequisites or [],
                "difficulty": n.difficulty,
                "mastery_target": n.mastery_target,
            }
            for n in remaining_nodes
        ]

        profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
        completed_json = json.dumps(completed_data, ensure_ascii=False, indent=2)
        remaining_json = json.dumps(remaining_data, ensure_ascii=False, indent=2)

        adjust_system_prompt = """你是一个世界顶级的课程教研专家与学习路径诊断微调师。
你的任务是根据用户当前的已完成学习记录、原定的剩余待学节点、最新的学生画像以及用户反馈/评估建议，对后续的学习路径进行精细化调整和纠偏。

输出规范：
1. 请提供一个精心设计的、能够体现调整后焦点的课程标题。
2. adjustment_rationale 必须是字符串数组，每项写出一条基于画像、测试成绩或反馈的微调调整依据（例如："根据 SQL 测验的不及格表现，增加了 outer join 的实操纠错节点"）。
3. confidence 必须是 0-100 的整数百分比。
4. 设计调整后的全局阶段骨架（stages），必须包含已完成的阶段以及调整后的剩余阶段。
5. 生成所有节点的完整列表（nodes），包括：
   a. **必须原样保留所有已完成的节点**：保持其 node_id, stage_id, title 绝对不变。
   b. **对后续未完成节点进行精细化调整**：可以删除不必要的后续节点、增加针对薄弱知识点的强化复习/实操节点、调整节点难度（beginner/intermediate/advanced）、或重新编排节点顺序，以最契合学生当前的认知风格与易错偏好。
   c. 确保所有新节点的 prerequisites 拓扑依赖结构正确（新节点可以依赖已完成的节点或新的前置节点）。
"""

        human_content = f"""
请为我诊断并优化后续的学习路径：

### 1. 学习目标与当前课程
- 课程主题: {active_path.title}
- 学习目标: {active_path.goal}

### 2. 用户最新画像 (请重点关注其中的薄弱点、易错倾向和交互偏好)
```json
{profile_json}
```

### 3. 用户反馈或评估建议
“{feedback}”

### 4. 已完成的节点（已掌握的技能，在输出中必须绝对保留）
```json
{completed_json}
```

### 5. 原定的剩余待学节点（仅供参考，你可以根据需要对其进行增删改排）
```json
{remaining_json}
```

请使用 JSON 返回完整的微调后规划结果（AgentCoursePathPlan 格式，需包含已完成节点和微调后的未完成节点）。
"""

        messages = [
            SystemMessage(content=adjust_system_prompt),
            HumanMessage(content=human_content)
        ]

        try:
            result = await self.llm.ainvoke_json(AgentCoursePathPlan, messages)
            if not isinstance(result, AgentCoursePathPlan):
                raise ValueError("Model failed to output strictly matched AgentCoursePathPlan")

            logger.info(f"PathPlannerAgent 路径微调成功，生成了 {len(result.nodes)} 个节点")
            return result

        except Exception as e:
            logger.error(f"PathPlannerAgent 路径微调失败: {str(e)}")
            raise e
