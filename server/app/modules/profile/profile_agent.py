import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


from app.services.memory import memory_service
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

PROFILE_UPDATE_TOKEN_THRESHOLD = 120
PROFILE_SIGNIFICANT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "learning_goal": ("目标", "计划", "考试", "考研", "冲刺", "通过", "下周", "期末", "证书"),
    "preference": ("偏好", "喜欢", "不喜欢", "习惯", "更想", "更愿意", "风格", "案例", "图解"),
    "weakness": ("不会", "薄弱", "总是错", "卡住", "困难", "看不懂", "做错", "没思路"),
    "learning_pace": ("每天", "每周", "节奏", "进度", "突击", "复习", "时间不够", "拖延"),
    "background": ("我是", "专业", "年级", "基础", "工作", "转行", "之前学过"),
}
PROFILE_NON_SIGNIFICANT_TEXTS = {"谢谢", "好的", "收到", "明白了", "再来一道题", "继续", "ok", "OK"}


# ==========================================
# 1. 定义大模型严格输出的 JSON 结构 (Pydantic)
# ==========================================
class ProfileExtraction(BaseModel):
    """大模型需要输出的 8 个核心维度特征（全息画像矩阵）"""
    knowledge_level: Optional[str] = Field(default=None, description="知识基础: 当前专业、学情边界")
    knowledge_level_score: Optional[int] = Field(default=None, description="知识基础评分(0-100)")
    cognitive_style: Optional[str] = Field(default=None, description="认知风格: 偏好视觉/案例/推导等")
    cognitive_style_score: Optional[int] = Field(default=None, description="认知风格评分(0-100)")
    error_pattern: Optional[str] = Field(default=None, description="易错点偏好: 逻辑盲区、常犯错误")
    error_pattern_score: Optional[int] = Field(default=None, description="易错模式评分(0-100)")
    learning_goal: Optional[str] = Field(default=None, description="学习目标: 考试/兴趣/职业等")
    learning_goal_score: Optional[int] = Field(default=None, description="学习目标评分(0-100)")
    learning_history: Optional[str] = Field(default=None, description="学习历史: 过去经验、相关背景")
    learning_history_score: Optional[int] = Field(default=None, description="学习历史评分(0-100)")
    interest_preference: Optional[str] = Field(default=None, description="兴趣偏好: 个人喜好、关注点")
    interest_preference_score: Optional[int] = Field(default=None, description="兴趣偏好评分(0-100)")
    learning_pace: Optional[str] = Field(default=None, description="学习节奏: 频率、时长、突击/平稳")
    learning_pace_score: Optional[int] = Field(default=None, description="学习节奏评分(0-100)")
    cognitive_level: Optional[str] = Field(default=None, description="认知水平: 深度思考、逻辑推演能力")
    cognitive_level_score: Optional[int] = Field(default=None, description="认知水平评分(0-100)")
    profile_summary: Optional[str] = Field(default=None, description="画像总结: 用一句话概括整体学习状态")


# ==========================================
# 2. 随学随新：合并式的 System Prompt
# ==========================================
PROFILE_BUILDER_PROMPT = """
# 角色与目标
你是一个顶尖的 AI 教育心理学家和数据分析引擎。你的任务是根据学生【原有的学习画像】和【最新的一段对话记录】，推断并提取新的特征，合并生成包含 **8 个核心维度** 的【最新的全息学习画像】。

# 8 个核心维度矩阵：
1. 知识基础 (Knowledge Level)
2. 认知风格 (Cognitive Style)
3. 易错点偏好 (Error Pattern)
4. 学习目标 (Learning Goal)
5. 学习历史 (Learning History)
6. 兴趣偏好 (Interest Preference)
7. 学习节奏 (Learning Pace)
8. 认知水平 (Cognitive Level)

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
        # 读取 mentor 模块的聊天记录（TutorAgent 保存消息时用的 module_name）
        self.module_name = "mentor"


        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.1,
        )

        self.structured_llm = llm.with_structured_output(ProfileExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", PROFILE_BUILDER_PROMPT)
        ])

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join((text or "").strip().lower().split())

    def should_trigger_profile_update(self, messages: list) -> bool:
        """轻量显著性判断：优先规则，不依赖大模型。"""
        if not messages:
            return False

        non_significant = {self._normalize_text(t) for t in PROFILE_NON_SIGNIFICANT_TEXTS}
        candidate_texts: list[str] = []
        for msg in messages[-8:]:
            if msg.role != "user":
                continue
            cleaned = self._normalize_text(msg.content)
            if not cleaned:
                continue
            if cleaned in non_significant:
                continue
            candidate_texts.append(cleaned)

        if not candidate_texts:
            return False

        joined = "\n".join(candidate_texts)
        for _, keywords in PROFILE_SIGNIFICANT_KEYWORDS.items():
            if any(k.lower() in joined for k in keywords):
                return True

        # 回退启发式：较长且包含明显自我描述的陈述
        return any(
            ("我" in text and len(text) >= 20 and ("想" in text or "需要" in text or "不会" in text))
            for text in candidate_texts
        )

    async def build_profile(self, user_id: int, session_id: str | None = None) -> bool:
        """
        后台异步执行的核心任务：提取并合并最新画像。
        session_id 为 None 时，自动查找该用户最近的 mentor 会话。
        """
        effective_session = session_id
        if effective_session is None:
            sessions = await self.memory.get_user_chat_sessions(
                user_id=user_id, module=self.module_name, limit=1
            )
            if sessions:
                effective_session = sessions[0].id
            else:
                effective_session = f"user-{user_id}-default-mentor"

        logger.info(f"[ProfileBuilder] 开始为用户 {user_id} 执行画像合并更新 (session={effective_session})...")

        # 1. 获取【近期对话记录】
        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=effective_session,
            module=self.module_name,
            limit=20  # 获取最近 10 轮(20条)对话作为增量信息
        )
        if not recent_msgs:
            logger.info(f"[ProfileBuilder] 用户 {user_id} 暂无新对话，无需更新。")
            return True

        if not self.should_trigger_profile_update(recent_msgs):
            logger.info(f"[ProfileBuilder] 用户 {user_id} 最近对话缺少画像显著信息，跳过更新。")
            return True

        logger.info(f"[ProfileBuilder] 找到用户 {user_id} 的 {len(recent_msgs)} 条近期对话，准备提取特征。")
        chat_history_str = "\n".join(
            [f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {msg.content}" for msg in recent_msgs])

        # 2. 获取【原有学习画像】
        current_profile = await self.memory.get_user_profile(user_id)
        current_profile_str = "暂无原有画像（新用户）"

        if current_profile:
            # 导出有值的字段给大模型参考
            profile_dict = current_profile.model_dump(exclude_unset=True,
                                                      exclude={"user_id", "updated_at", "created_at", "id"})
            if profile_dict:
                current_profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])
                logger.info(f"[ProfileBuilder] 已加载用户 {user_id} 的现有画像。")

        # 3. 调用大模型，执行【合并+提取】
        logger.info(f"[ProfileBuilder] 正在请求 LLM 进行画像合并提取 (user_id={user_id})...")
        try:
            prompt = self.prompt_template.invoke({
                "current_profile": current_profile_str,
                "chat_history": chat_history_str
            })
            updated_data: ProfileExtraction = await self.structured_llm.ainvoke(prompt)
            logger.info(f"[ProfileBuilder] LLM 提取成功 (user_id={user_id})")
        except Exception as e:
            logger.error(f"[ProfileBuilder] 画像提取与合并失败: {str(e)}")
            return False

        # 4. 过滤空值并写入数据库
        # exclude_unset=True 可以过滤掉大模型输出的 null，防止污染数据库
        final_features = updated_data.model_dump(exclude_none=True)

        if not final_features:
            logger.info(f"[ProfileBuilder] 用户 {user_id} 画像无实质性更新。")
            return True

        # 5. 调用 MemoryService 更新数据库 (你的 update_user_profile 会自动处理追加和版本快照)
        try:
            await self.memory.update_user_profile(
                user_id=user_id,
                features=final_features,
                change_reason=f"基于最近{len(recent_msgs)}条有效对话的显著特征增量合并"
            )
            logger.info(f"[ProfileBuilder] 用户 {user_id} 画像合并更新完毕！更新字段: {list(final_features.keys())}")
            return True
        except Exception as e:
            logger.error(f"[ProfileBuilder] 保存更新后的画像失败 (user_id={user_id}): {str(e)}")
            return False

profile_agent = ProfileBuilderAgent()
