"""Fail-closed course profiles for renderer-neutral PPT visual planning."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.shared.ppt.contract import CourseDomain, VisualFamily


@dataclass(frozen=True)
class CourseProfile:
    """Planning guidance and representative models for one course domain.

    Attributes:
        name_zh: Human-readable Chinese course-family name.
        planning_guidance: Domain-specific guidance for choosing visual models.
        preferred_families: Ranked visual families suited to the domain.
        representative_models: Concrete semantic models planners may consider.
    """

    name_zh: str
    planning_guidance: str
    preferred_families: tuple[VisualFamily, ...]
    representative_models: tuple[str, ...]


COURSE_PROFILES: Mapping[CourseDomain, CourseProfile] = MappingProxyType(
    {
        CourseDomain.ALGORITHMS: CourseProfile(
            name_zh="算法与数据结构",
            planning_guidance=(
                "优先呈现状态逐步变化、控制流程、复杂度证据和理论边界；"
                "用状态帧、关系图和公式解释机制，不展示代码。"
            ),
            preferred_families=(
                VisualFamily.ALGORITHM_FRAMES,
                VisualFamily.QUANTITATIVE,
                VisualFamily.HIERARCHY,
            ),
            representative_models=(
                "算法状态帧",
                "递归树",
                "复杂度曲线",
                "正确性与复杂度公式",
            ),
        ),
        CourseDomain.OPERATING_SYSTEMS: CourseProfile(
            name_zh="操作系统",
            planning_guidance=(
                "围绕状态迁移、资源所有权、并发时序与内存区域组织视觉，明确系统"
                "边界和触发条件。"
            ),
            preferred_families=(
                VisualFamily.STATE_MACHINE,
                VisualFamily.MEMORY_LAYOUT,
                VisualFamily.TIMELINE,
                VisualFamily.DATA_FLOW,
            ),
            representative_models=(
                "进程状态机",
                "虚拟内存布局",
                "并发时序",
                "系统调用数据流",
            ),
        ),
        CourseDomain.NETWORKS: CourseProfile(
            name_zh="计算机网络",
            planning_guidance=(
                "优先展示端点、分层职责、报文流与协议时序，保持方向、封装边界和"
                "故障传播关系可见。"
            ),
            preferred_families=(
                VisualFamily.GRAPH,
                VisualFamily.DATA_FLOW,
                VisualFamily.TIMELINE,
                VisualFamily.HIERARCHY,
            ),
            representative_models=(
                "网络拓扑",
                "协议分层",
                "报文数据流",
                "握手时序",
            ),
        ),
        CourseDomain.COMPUTER_ARCHITECTURE: CourseProfile(
            name_zh="计算机组成与体系结构",
            planning_guidance=(
                "以部件连接、信号路径、流水时序和存储层级为主，区分结构关系与"
                "一次执行过程。"
            ),
            preferred_families=(
                VisualFamily.CIRCUIT,
                VisualFamily.DATA_FLOW,
                VisualFamily.MEMORY_LAYOUT,
                VisualFamily.TIMELINE,
            ),
            representative_models=(
                "组合逻辑电路",
                "处理器数据通路",
                "存储层级",
                "流水线时序",
            ),
        ),
        CourseDomain.DATABASES: CourseProfile(
            name_zh="数据库系统",
            planning_guidance=(
                "优先呈现实体现实关系、模式映射、关系表与查询数据流；比较方案时"
                "显式保留约束和代价维度。"
            ),
            preferred_families=(
                VisualFamily.MAPPING,
                VisualFamily.TABLE_MATRIX,
                VisualFamily.GRAPH,
                VisualFamily.DATA_FLOW,
            ),
            representative_models=(
                "实体关系图",
                "关系表矩阵",
                "模式映射",
                "查询执行流",
            ),
        ),
        CourseDomain.COMPILERS: CourseProfile(
            name_zh="编译原理",
            planning_guidance=(
                "区分语法层级、自动机状态、编译阶段和中间表示变换，使用索引关系"
                "表达结构而非渲染坐标。"
            ),
            preferred_families=(
                VisualFamily.HIERARCHY,
                VisualFamily.STATE_MACHINE,
                VisualFamily.DATA_FLOW,
                VisualFamily.ALGORITHM_FRAMES,
            ),
            representative_models=(
                "抽象语法树",
                "词法自动机",
                "编译阶段数据流",
                "规约过程帧",
            ),
        ),
        CourseDomain.DISCRETE_THEORY: CourseProfile(
            name_zh="离散数学与理论计算机",
            planning_guidance=(
                "围绕定义、关系、证明步骤与反例组织视觉；公式必须解释变量，图论"
                "结构必须保留节点间关系。"
            ),
            preferred_families=(
                VisualFamily.FORMULA,
                VisualFamily.GRAPH,
                VisualFamily.TABLE_MATRIX,
                VisualFamily.MAPPING,
            ),
            representative_models=(
                "证明推导",
                "图论关系图",
                "真值表",
                "集合映射",
            ),
        ),
        CourseDomain.SOFTWARE_DISTRIBUTED: CourseProfile(
            name_zh="软件工程与分布式系统",
            planning_guidance=(
                "突出组件职责、调用链、分布式时序、状态复制和故障边界；复杂场景"
                "可组合多个互补但独立的视觉面板。"
            ),
            preferred_families=(
                VisualFamily.GRAPH,
                VisualFamily.TIMELINE,
                VisualFamily.DATA_FLOW,
                VisualFamily.COMPOSITE,
            ),
            representative_models=(
                "组件依赖图",
                "分布式时序",
                "请求数据流",
                "故障恢复组合图",
            ),
        ),
        CourseDomain.GENERAL_CS: CourseProfile(
            name_zh="通用计算机基础",
            planning_guidance=(
                "先根据知识关系选择最直接的语义模型；仅当单一模型无法承载教学"
                "目标时使用组合视觉。"
            ),
            preferred_families=(
                VisualFamily.HIERARCHY,
                VisualFamily.GRAPH,
                VisualFamily.TIMELINE,
                VisualFamily.COMPOSITE,
            ),
            representative_models=(
                "概念层级",
                "关系图",
                "过程时间线",
                "多视角组合图",
            ),
        ),
    }
)


def _validate_profiles() -> None:
    declared = set(CourseDomain)
    registered = set(COURSE_PROFILES)
    if declared != registered:
        missing = sorted(domain.value for domain in declared - registered)
        extra = sorted(domain.value for domain in registered - declared)
        raise RuntimeError(
            f"PPT course profile mismatch: missing={missing} extra={extra}"
        )
    for domain, profile in COURSE_PROFILES.items():
        if not profile.name_zh or not profile.planning_guidance:
            raise RuntimeError(f"PPT course profile {domain.value} lacks guidance")
        if not profile.preferred_families:
            raise RuntimeError(
                f"PPT course profile {domain.value} has no preferred visual family"
            )
        if any(not isinstance(family, VisualFamily) for family in profile.preferred_families):
            raise RuntimeError(
                f"PPT course profile {domain.value} contains an invalid visual family"
            )
        if not profile.representative_models:
            raise RuntimeError(
                f"PPT course profile {domain.value} has no representative model"
            )


_validate_profiles()


def course_profile(domain: CourseDomain) -> CourseProfile:
    """Return the validated planning profile for a course domain.

    Args:
        domain: Closed course-domain value selected by the logic model.

    Returns:
        The immutable profile registered for the domain.
    """

    return COURSE_PROFILES[domain]


__all__ = ["COURSE_PROFILES", "CourseProfile", "course_profile"]
