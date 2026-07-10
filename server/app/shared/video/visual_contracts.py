"""Visual contracts — per-visual_type schema that the LLM must follow.

Each contract specifies the exact keys and value shapes that the `visual`
dict must contain for a given visual_type.  These contracts are injected
into the scene-writer prompt so the LLM produces data matching what the
Remotion React components expect.

If a component accesses ``scene.visual.steps`` and expects
``[{id, label, description}]``, the contract must spell that out.
This eliminates the class of runtime crashes where the LLM generates
``"steps": ["step1", "step2"]`` (flat strings) instead of structured objects.
"""

from __future__ import annotations

from app.shared.video.schemas import VisualType

# Each value is a dict of {key: description} that the LLM sees.
# We use human-readable descriptions rather than formal JSON Schema because
# the LLM produces better output with natural-language constraints.

# 各 visual_type 对应的视觉契约：规定 visual 字典的键名与值形状，注入场景编写提示词
VISUAL_CONTRACTS: dict[VisualType, dict] = {
    "title_intro": {
        "course": "string — 课程名称",
        "chapter": "string — 章节标题",
        "subtitle": "string — 副标题/学习目标",
        "tags": "string[] — 关键标签（2-4个）",
        "hero_keywords": "string[] — 中心展示关键词（2-3个）",
        "hero_center": "string — 中心大字（默认用标题）",
    },
    "concept_explain": {
        "main_concept": "string — 核心概念名称",
        "definition": "string — 简明定义",
        "keywords": "string[] — 关键词列表（3-5个）",
        "why_it_matters": "string[] — 为什么重要（2-4条）",
        "related_concepts": "object[] — 关联概念，每项 {name: string, relation: string}",
        "common_misconception": "string — 常见误区（可选，留空则不显示）",
    },
    "process_flow": {
        "process_name": "string — 流程名称",
        "inputs": "string[] — 输入条件（1-3个）",
        "outputs": "string[] — 输出结果（1-3个）",
        "steps": "object[] — 流程步骤，每项必须包含 {id: string, label: string, description: string}",
        "failure_points": "object[] — 失败点（可选），每项 {step_id: string, reason: string}",
    },
    "state_machine": {
        "machine_name": "string — 状态机名称",
        "initial_state": "string — 初始状态ID",
        "states": "object[] — 状态列表，每项 {id: string, label: string, description: string}",
        "transitions": "object[] — 转移列表，每项 {from: string, to: string, label: string}",
        "event_sequence": "object[] — 事件序列（可选），每项 {time: number, event: string, active_state: string}",
        "explanation_map": "object — 状态说明映射（可选），{state_id: explanation_string}",
    },
    "data_structure": {
        "structure_type": "string — 数据结构类型（如 linked_list, binary_tree, hash_table）",
        "initial_state": "object — 初始状态 {nodes: DataNode[], edges: Edge[]}，DataNode={id,label,value}, Edge={from,to,label}",
        "operations": "object[] — 操作序列，每项 {action: string, target?: string, new_node?: DataNode, description: string, from?: string, to?: string}",
        "pointer_labels": "object[] — 指针标签（可选），每项 {name: string, target: string}",
        "complexity": "object — 复杂度 {time: string, space: string, condition?: string}",
        "invariant": "string — 不变式（可选）",
    },
    "algorithm_trace": {
        "algorithm_name": "string — 算法名称",
        "problem": "string — 问题描述",
        "data": "(number|string)[] — 输入数据",
        "pseudocode": "string[] — 伪代码行",
        "steps": "object[] — 追踪步骤，每项 {line: number, description: string, variables: object, highlight_indices: number[]}",
        "complexity": "object — 复杂度 {time: string, space: string}",
        "result": "string — 最终结果",
    },
    "memory_layout": {
        "layout_type": "string — 布局类型（如 stack_heap, process_memory）",
        "code": "string — 相关代码片段",
        "memory_regions": "object[] — 内存区域，每项 {name: string, start: string, size: string, color_hint: string}",
        "actions": "object[] — 内存操作，每项 {step: number, action: string, region: string, detail: string}",
        "explanation": "string — 布局说明",
    },
    "cpu_architecture": {
        "architecture_name": "string — 架构名称（如 MIPS, RISC-V, x86）",
        "current_instruction": "string — 当前执行的指令",
        "modules": "object[] — CPU模块，每项 {id: string, name: string, type: string, description: string}",
        "data_paths": "object[] — 数据通路，每项 {from: string, to: string, label: string, width?: string}",
        "steps": "object[] — 执行步骤，每项 {phase: string, description: string, active_modules: string[]}",
        "registers": "object[] — 寄存器（可选），每项 {name: string, value: string, size: string}",
        "explanation": "string — 执行说明",
    },
    "network_protocol": {
        "protocol_name": "string — 协议名称",
        "messages": "object[] — 消息序列，每项 {from: string, to: string, label: string, detail: string}",
        "packet_fields": "object[] — 报文字段（可选），每项 {name: string, value: string, size: string}",
        "state_changes": "object[] — 状态变化（可选），每项 {entity: string, from_state: string, to_state: string, trigger: string}",
        "key_point": "string — 关键要点",
    },
    "layered_architecture": {
        "architecture_name": "string — 架构名称（如 OSI, TCP/IP, MVC）",
        "layers": "object[] — 层级列表，每项 {id: string, name: string, responsibility: string, protocols?: string[]}",
        "current_focus_layer": "string — 当前聚焦层ID",
        "examples": "string[] — 实例列表",
    },
    "code_execution": {
        "language": "string — 编程语言（如 python, java, c）",
        "code": "string — 代码片段",
        "steps": "object[] — 执行步骤，每项 {line: number, description: string, variables: object, output?: string}",
        "output": "string — 最终输出",
        "error_or_misconception": "string — 错误或误区（可选）",
    },
    "compare_summary": {
        "compare_title": "string — 对比标题",
        "left": "object — 左侧数据 {title: string, points: string[]}",
        "right": "object — 右侧数据 {title: string, points: string[]}",
        "same_points": "string[] — 共同点",
        "different_points": "object[] — 差异维度，每项 {dimension: string, left: string, right: string}",
        "conclusion": "string — 结论",
        "exam_hint": "string — 考试提示（可选）",
    },
    "knowledge_check": {
        "question": "string — 检测问题",
        "options": "object[] — 选项列表，每项 {id: string, text: string}",
        "correct_answer": "string — 正确答案选项ID",
        "explanation": "string — 答案解释",
        "related_concept": "string — 关联概念",
        "review_points": "string[] — 复习要点",
    },
    "array_linked_list": {
        "structure_type": "string — 结构类型（array 或 linked_list）",
        "nodes": "object[] — 节点列表，每项 {id: string, value: string, index: number}",
        "operations": "object[] — 操作序列，每项 {type: string, description: string, target_index?: number, value?: string}",
        "time_complexity": "string — 时间复杂度",
        "space_complexity": "string — 空间复杂度",
    },
    "stack_queue": {
        "structure_type": "string — 结构类型（stack 或 queue）",
        "items": "object[] — 元素列表，每项 {value: string, status: string}",
        "operations": "object[] — 操作序列，每项 {type: string, value?: string, description: string}",
    },
    "process_state": {
        "states": "object[] — 进程状态，每项 {id: string, name: string, description: string, color_hint: string}",
        "transitions": "object[] — 状态转移，每项 {from: string, to: string, trigger: string, description: string}",
    },
    "storage_hierarchy": {
        "levels": "object[] — 存储层级，每项 {name: string, speed: string, capacity: string, cost: string, examples: string[]}",
        "transfers": "object[] — 数据传输（可选），每项 {from: string, to: string, method: string, speed: string}",
        "highlight_level": "string — 高亮层级名称（可选）",
    },
}


# 返回指定 visual_type 的视觉契约，未知类型回退为空 dict
def get_visual_contract(visual_type: VisualType) -> dict:
    """Return the visual contract for a given visual_type.

    Falls back to an empty dict for unknown types (which will be
    rendered by UnknownSceneFallback anyway).
    """
    return VISUAL_CONTRACTS.get(visual_type, {})
