"""Quiz Agent 的结构化输出契约与确定性出题蓝图。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


QuizQuestionType = Literal[
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
]
QuizDifficulty = Literal["basic", "medium", "advanced"]

QUESTION_TYPE_MAP: dict[str, QuizQuestionType] = {
    "single": "single_choice",
    "multiple": "multiple_choice",
    "judge": "true_false",
    "fill": "fill_blank",
}
DEFAULT_QUESTION_TYPES: tuple[QuizQuestionType, ...] = (
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
)


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(pattern=r"^[A-D]$")
    content: str = Field(min_length=1, max_length=240)


class QuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    type: QuizQuestionType
    question: str = Field(min_length=1, max_length=600)
    options: list[QuizOption] = Field(default_factory=list, max_length=4)
    answer: str | bool | list[str]
    explanation: str = Field(min_length=1, max_length=1200)
    difficulty: QuizDifficulty
    knowledge_points: list[str] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_question_contract(self) -> "QuizQuestion":
        labels = [option.label for option in self.options]
        if len(labels) != len(set(labels)):
            raise ValueError("选项标签不能重复")

        if self.type in {"single_choice", "multiple_choice"}:
            if labels != ["A", "B", "C", "D"]:
                raise ValueError("选择题必须按 A、B、C、D 提供恰好四个选项")
        elif self.options:
            raise ValueError("判断题和填空题的 options 必须为空")

        if self.type == "single_choice":
            if not isinstance(self.answer, str) or self.answer not in labels:
                raise ValueError("单选题答案必须是一个有效选项标签")
        elif self.type == "multiple_choice":
            if not isinstance(self.answer, list):
                raise ValueError("多选题答案必须是选项标签数组")
            if len(self.answer) < 2 or len(self.answer) != len(set(self.answer)):
                raise ValueError("多选题必须包含至少两个不重复的正确选项")
            if any(answer not in labels for answer in self.answer):
                raise ValueError("多选题答案必须来自已有选项")
        elif self.type == "true_false":
            if type(self.answer) is not bool:
                raise ValueError("判断题答案必须是布尔值")
        elif not isinstance(self.answer, str) or not self.answer.strip():
            raise ValueError("填空题答案必须是非空字符串")

        return self


class QuizPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=300)
    questions: list[QuizQuestion] = Field(min_length=1, max_length=20)


class QuizBlueprintSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    type: QuizQuestionType
    difficulty: QuizDifficulty


def build_quiz_blueprint(
    *,
    question_count: int,
    question_types: list[str] | None,
    difficulty_mode: str,
) -> list[QuizBlueprintSlot]:
    """在调用模型前确定题目编号、题型和难度，避免模型自行分配后漂移。"""
    normalized_types = [
        QUESTION_TYPE_MAP[value]
        for value in (question_types or [])
        if value in QUESTION_TYPE_MAP
    ]
    types = tuple(dict.fromkeys(normalized_types)) or DEFAULT_QUESTION_TYPES

    if difficulty_mode == "basic":
        difficulty_cycle: tuple[QuizDifficulty, ...] = ("basic",)
    elif difficulty_mode == "exam":
        # 一个完整周期严格满足基础/中等/进阶 = 3:5:2。
        difficulty_cycle = (
            "basic",
            "medium",
            "medium",
            "advanced",
            "basic",
            "medium",
            "medium",
            "advanced",
            "basic",
            "medium",
        )
    else:
        # 自适应模式保留足够基础题，同时包含迁移与进阶检测。
        difficulty_cycle = ("basic", "medium", "basic", "medium", "advanced")

    return [
        QuizBlueprintSlot(
            id=index + 1,
            type=types[index % len(types)],
            difficulty=difficulty_cycle[index % len(difficulty_cycle)],
        )
        for index in range(question_count)
    ]


def validate_quiz_payload(
    payload: QuizPayload,
    blueprint: list[QuizBlueprintSlot],
) -> None:
    """校验模型输出与确定性蓝图完全一致。"""
    errors: list[str] = []
    if len(payload.questions) != len(blueprint):
        errors.append(
            f"题目数量应为 {len(blueprint)}，实际为 {len(payload.questions)}"
        )

    seen_questions: set[str] = set()
    for index, slot in enumerate(blueprint):
        if index >= len(payload.questions):
            break
        question = payload.questions[index]
        if question.id != slot.id:
            errors.append(
                f"第 {index + 1} 题 id 应为 {slot.id}，实际为 {question.id}"
            )
        if question.type != slot.type:
            errors.append(
                f"第 {index + 1} 题类型应为 {slot.type}，实际为 {question.type}"
            )
        if question.difficulty != slot.difficulty:
            errors.append(
                f"第 {index + 1} 题难度应为 {slot.difficulty}，实际为 {question.difficulty}"
            )

        normalized_question = " ".join(question.question.split()).casefold()
        if normalized_question in seen_questions:
            errors.append(f"第 {index + 1} 题与前面题目重复")
        seen_questions.add(normalized_question)

    if errors:
        raise ValueError("；".join(errors[:12]))

