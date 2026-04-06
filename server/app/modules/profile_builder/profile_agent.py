import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


from app.modules.memory.service import memory_service
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)


# ==========================================
# 1. 定义大模型严格输出的 JSON 结构 (Pydantic)
# ==========================================
class ProfileExtraction(BaseModel):
    """大模型需要输出的 8 个维度特征（合并后的最新完整版）"""
    knowledge_level: Optional[str] = Field(default=None, description="知识基础")
    knowledge_level_score: Optional[int] = Field(default=None, description="知识基础评分(0-100), 根据描述内容评估该维度的掌握程度, 越高越好")
    cognitive_style: Optional[str] = Field(default=None, description="认知风格")
    cognitive_style_score: Optional[int] = Field(default=None, description="认知风格评分(0-100), 评估学生对自己学习方式的认知清晰度")
    error_pattern: Optional[str] = Field(default=None, description="易错点偏好")
    error_pattern_score: Optional[int] = Field(default=None, description="易错模式评分(0-100), 评估学生识别和改进错误的能力")
    learning_goal: Optional[str] = Field(default=None, description="学习目标")
    learning_goal_score: Optional[int] = Field(default=None, description="学习目标评分(0-100), 评估目标的清晰度与合理性")
    learning_history: Optional[str] = Field(default=None, description="学习历史与专业")
    learning_history_score: Optional[int] = Field(default=None, description="学习历史评分(0-100), 评估知识积累的深度和广度")
    interest_preference: Optional[str] = Field(default=None, description="兴趣偏好")
    interest_preference_score: Optional[int] = Field(default=None, description="兴趣偏好评分(0-100), 评估兴趣的明确性和与学习目标的契合度")
    learning_pace: Optional[str] = Field(default=None, description="学习节奏")
    learning_pace_score: Optional[int] = Field(default=None, description="学习节奏评分(0-100), 评估学习节奏的合理性和自律程度")
    cognitive_level: Optional[str] = Field(default=None, description="认知水平")
    cognitive_level_score: Optional[int] = Field(default=None, description="认知水平评分(0-100), 评估综合认知能力, 包括分析、推理和应用能力")
    profile_summary: Optional[str] = Field(default=None, description="画像总结: 用一句话概括整体学习状态")


# ==========================================
# 2. 随学随新：合并式的 System Prompt
# ==========================================
PROFILE_BUILDER_PROMPT = """
# 角色与目标
你是一个顶尖的 AI 教育心理学家和数据分析引擎。你的任务是根据学生【原有的学习画像】和【最新的一段对话记录】，推断并提取新的特征，合并生成【最新的学习画像】。

# 原有学习画像：
{current_profile}

# 最新对话记录：
{chat_history}

# 更新与合并规则 (最高优先级)
1. **合并而非覆盖**：如果最新对话中出现了新的特征（比如新的易错点、新兴趣），请将其与“原有学习画像”中的对应字段进行**逻辑合并**。保留旧信息，补充新信息。
2. **保持原有**：如果最新对话中没有涉及到某个维度的信息，请直接**照搬**“原有学习画像”中该字段的内容，绝对不能将其清空。
3. **状态更替**：如果最新对话中显示学生已经克服了之前的错误，或者改变了目标，请根据最新情况**修改**原有描述。
4. **空值处理**：如果某维度原来是空(null)，且最新对话也没体现，继续输出 null。
5. **全局总结**：请基于你合并后的所有维度，重新撰写 `profile_summary`，用一句话凝练该学生当前的学习状态。

# 评分规则
6. **维度评分**：对每个非空的维度字段，请同时输出一个 0-100 的整数评分。评分标准：
   - 0-30: 初级（了解概念，但缺乏实践或经常出错）
   - 31-60: 中级（有一定基础，能应用但不够熟练或深度不足）
   - 61-80: 良好（掌握较好，能灵活运用，有自省能力）
   - 81-100: 优秀（深入掌握，能举一反三，有系统性思考）
7. **评分依据**：评分应基于对话中展现的实际水平，而非主观臆测。如果某维度信息不足，请输出 null 而非猜测分数。
8. **合并评分**：如果原有评分存在且对话中没有新的相关证据，保留原有评分。如有新证据，合理调整。
"""


# ==========================================
# 3. ProfileBuilderAgent 核心实现
# ==========================================
class ProfileBuilderAgent:
    def __init__(self):
        self.memory = memory_service
        self.module_name = "profile_builder"
        self.global_session_id = "global_profile_chat"

        # 实例化大模型 (后台提取任务建议使用低温度，保证合并逻辑严谨不发散)
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.1,
        )

        # 强制大模型以 ProfileExtraction 的 JSON 格式输出
        self.structured_llm = llm.with_structured_output(ProfileExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", PROFILE_BUILDER_PROMPT)
        ])

    async def build_profile(self, user_id: int):
        """
        后台异步执行的核心任务：提取并合并最新画像
        """
        logger.info(f"[ProfileBuilder] 开始为用户 {user_id} 执行画像合并更新...")

        # 1. 获取【近期对话记录】
        recent_msgs = self.memory.get_recent_messages(
            user_id=user_id,
            session_id=self.global_session_id,
            module=self.module_name,
            limit=20  # 获取最近 10 轮(20条)对话作为增量信息
        )
        if not recent_msgs:
            logger.info(f"[ProfileBuilder] 用户 {user_id} 暂无新对话，无需更新。")
            return

        chat_history_str = "\n".join(
            [f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {msg.content}" for msg in recent_msgs])

        # 2. 获取【原有学习画像】
        current_profile = self.memory.get_user_profile(user_id)
        current_profile_str = "暂无原有画像（新用户）"

        if current_profile:
            # 导出有值的字段给大模型参考
            profile_dict = current_profile.model_dump(exclude_unset=True,
                                                      exclude={"user_id", "updated_at", "created_at", "id"})
            if profile_dict:
                current_profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])

        # 3. 调用大模型，执行【合并+提取】
        try:
            prompt = self.prompt_template.invoke({
                "current_profile": current_profile_str,
                "chat_history": chat_history_str
            })
            # 大模型会返回合并后的完整 Pydantic 对象
            updated_data: ProfileExtraction = await self.structured_llm.ainvoke(prompt)
        except Exception as e:
            logger.error(f"[ProfileBuilder] 画像提取与合并失败: {str(e)}")
            return

        # 4. 过滤空值并写入数据库
        # exclude_unset=True 可以过滤掉大模型输出的 null，防止污染数据库
        final_features = updated_data.model_dump(exclude_none=True)

        if not final_features:
            logger.info(f"[ProfileBuilder] 画像无实质性更新。")
            return

        # 5. 调用 MemoryService 更新数据库 (你的 update_user_profile 会自动处理追加和版本快照)
        self.memory.update_user_profile(
            user_id=user_id,
            features=final_features,
            change_reason="基于近期对话增量合并"
        )

        logger.info(f"[ProfileBuilder] 用户 {user_id} 画像合并更新完毕！更新字段: {list(final_features.keys())}")

profile_agent = ProfileBuilderAgent()