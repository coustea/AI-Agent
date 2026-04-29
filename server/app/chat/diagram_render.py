"""图解渲染模块。

将结构化图解数据转换为 Mermaid 语法，供前端渲染。
"""

from __future__ import annotations

import re
from typing import Any


# 匹配非安全字符的正则表达式，用于生成合法的 Mermaid 节点ID
_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_]")


def build_diagram_render(diagram: dict[str, Any]) -> dict[str, str]:
    """构建图解渲染结果。

    Args:
        diagram: 结构化图解数据，包含 type 和 spec 字段。

    Returns:
        包含 engine、format、source 的渲染信息字典。
    """
    source = _build_mermaid_source(diagram)
    return {"engine": "mermaid", "format": "text", "source": source}


def _build_mermaid_source(diagram: dict[str, Any]) -> str:
    """根据图解类型构建 Mermaid 源码。

    Args:
        diagram: 结构化图解数据。

    Returns:
        Mermaid 语法的图解源码。

    Raises:
        ValueError: 不支持的图解类型。
    """
    diagram_type = diagram.get("type")
    spec = diagram.get("spec") or {}

    # 根据类型分发到对应的构建函数
    if diagram_type == "sequence":
        return _build_sequence(spec)
    if diagram_type == "flow":
        return _build_flow(spec)
    if diagram_type == "state":
        return _build_state(spec)
    if diagram_type == "relation":
        return _build_relation(spec)
    if diagram_type == "hierarchy":
        return _build_hierarchy(spec)
    if diagram_type == "compare":
        return _build_compare(spec)

    # 计算机学科专用图表类型
    if diagram_type == "class":
        return _build_class(spec)
    if diagram_type == "er":
        return _build_er(spec)
    if diagram_type == "block":
        return _build_block(spec)
    if diagram_type == "packet":
        return _build_packet(spec)
    if diagram_type == "git":
        return _build_git(spec)

    # 软件工程教学常用图表类型
    if diagram_type == "activity":
        return _build_activity(spec)
    if diagram_type == "usecase":
        return _build_usecase(spec)
    if diagram_type == "component":
        return _build_component(spec)
    if diagram_type == "package":
        return _build_package(spec)
    if diagram_type == "deployment":
        return _build_deployment(spec)
    if diagram_type == "object":
        return _build_object(spec)
    if diagram_type == "communication":
        return _build_communication(spec)

    raise ValueError(f"unsupported diagram type: {diagram_type!r}")


def _build_sequence(spec: dict[str, Any]) -> str:
    """构建时序图 Mermaid 源码。

    Args:
        spec: 时序图规格，包含 actors 和 messages。

    Returns:
        sequenceDiagram 语法的 Mermaid 源码。
    """
    lines = ["sequenceDiagram"]
    # 声明参与者
    for actor in spec.get("actors", []):
        lines.append(f"    participant {_node_id(actor.get('id'))} as {_label(actor)}")

    # 声明消息
    for message in spec.get("messages", []):
        source = _node_id(message.get("from"))
        target = _node_id(message.get("to"))
        lines.append(f"    {source}->>{target}: {_plain_text(message.get('label'))}")

    return "\n".join(lines)


def _build_flow(spec: dict[str, Any]) -> str:
    """构建流程图 Mermaid 源码。

    Args:
        spec: 流程图规格，包含 steps 和 edges。

    Returns:
        flowchart TD 语法的 Mermaid 源码。
    """
    lines = ["flowchart TD"]
    # 声明步骤节点
    for step in spec.get("steps", []):
        node_id = _node_id(step.get("id"))
        lines.append(f"    {node_id}[{_label(step)}]")

    # 声明边
    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_state(spec: dict[str, Any]) -> str:
    """构建状态图 Mermaid 源码。

    Args:
        spec: 状态图规格，包含 states 和 transitions。

    Returns:
        stateDiagram-v2 语法的 Mermaid 源码。
    """
    lines = ["stateDiagram-v2"]
    # 声明状态
    for state in spec.get("states", []):
        lines.append(f"    state {_label(state)} as {_node_id(state.get('id'))}")

    # 声明转换
    for transition in spec.get("transitions", []):
        source = _node_id(transition.get("from"))
        target = _node_id(transition.get("to"))
        label = _plain_text(transition.get("label"))
        lines.append(f"    {source} --> {target}: {label}")

    return "\n".join(lines)


def _build_relation(spec: dict[str, Any]) -> str:
    """构建关系图 Mermaid 源码。

    Args:
        spec: 关系图规格，包含 nodes 和 edges。

    Returns:
        graph TD 语法的 Mermaid 源码。
    """
    lines = ["graph TD"]
    # 声明节点
    for node in spec.get("nodes", []):
        node_id = _node_id(node.get("id"))
        lines.append(f"    {node_id}[{_label(node)}]")

    # 声明边
    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_hierarchy(spec: dict[str, Any]) -> str:
    """构建层级结构图 Mermaid 源码。

    Args:
        spec: 层级结构规格，包含 root 节点。

    Returns:
        graph TD 语法的 Mermaid 源码。
    """
    lines = ["graph TD"]
    root = spec.get("root") or {}
    if root:
        _append_hierarchy_node(lines, root)
    return "\n".join(lines)


def _append_hierarchy_node(lines: list[str], node: dict[str, Any]) -> None:
    """递归追加层级节点到行列表。

    Args:
        lines: Mermaid 源码行列表。
        node: 当前层级节点。
    """
    parent_id = _node_id(node.get("id"))
    lines.append(f"    {parent_id}[{_label(node)}]")
    # 递归处理子节点
    for child in node.get("children", []):
        child_id = _node_id(child.get("id"))
        _append_hierarchy_node(lines, child)
        lines.append(f"    {parent_id} --> {child_id}")


def _build_compare(spec: dict[str, Any]) -> str:
    """构建对比图 Mermaid 源码。

    Args:
        spec: 对比图规格，包含 items 列表。

    Returns:
        flowchart LR 语法的 Mermaid 源码。
    """
    lines = ["flowchart LR"]
    previous_id: str | None = None
    # 声明对比项节点，使用隐形连接符 ~~~ 保持水平排列
    for index, item in enumerate(spec.get("items", []), start=1):
        node_id = f"item_{index}"
        lines.append(f"    {node_id}[{_compare_label(item)}]")
        if previous_id is not None:
            lines.append(f"    {previous_id} ~~~ {node_id}")
        previous_id = node_id

    return "\n".join(lines)


def _build_class(spec: dict[str, Any]) -> str:
    """构建类图 Mermaid 源码。

    Args:
        spec: 类图规格，包含 classes 和 relationships。

    Returns:
        classDiagram 语法的 Mermaid 源码。
    """
    lines = ["classDiagram"]
    # 声明类
    for cls in spec.get("classes", []):
        class_name = _node_id(cls.get("name"))
        lines.append(f"    class {class_name} {{")
        # 属性
        for attr in cls.get("attributes", []):
            lines.append(f"        {_plain_text(attr)}")
        # 方法
        for method in cls.get("methods", []):
            lines.append(f"        {_plain_text(method)}")
        lines.append("    }")
        # 注解（如 <<interface>>）
        annotation = cls.get("annotation")
        if annotation:
            lines.append(f"    <<{_plain_text(annotation)}>> {class_name}")

    # 声明关系
    for rel in spec.get("relationships", []):
        source = _node_id(rel.get("from"))
        target = _node_id(rel.get("to"))
        rel_type = rel.get("type", "association")
        label = _plain_text(rel.get("label", ""))
        rel_line = _class_relation_line(source, target, rel_type, label)
        if rel_line:
            lines.append(f"    {rel_line}")

    return "\n".join(lines)


def _class_relation_line(source: str, target: str, rel_type: str, label: str) -> str:
    """构建类图关系的 Mermaid 语法行。

    Args:
        source: 源类名。
        target: 目标类名。
        rel_type: 关系类型 (inheritance, composition, aggregation, dependency, association)。
        label: 关系标签。

    Returns:
        关系的 Mermaid 语法行。
    """
    # Mermaid 类图关系符号
    relation_symbols = {
        "inheritance": f"{source} --|> {target}",
        "implementation": f"{source} ..|> {target}",
        "composition": f"{source} *-- {target}",
        "aggregation": f"{source} o-- {target}",
        "dependency": f"{source} ..> {target}",
        "association": f"{source} --> {target}",
        "bidirectional": f"{source} -- {target}",
    }
    line = relation_symbols.get(rel_type, f"{source} --> {target}")
    if label:
        line = f"{line} : {label}"
    return line


def _build_er(spec: dict[str, Any]) -> str:
    """构建实体关系图 Mermaid 源码。

    Args:
        spec: ER 图规格，包含 entities 和 relationships。

    Returns:
        erDiagram 语法的 Mermaid 源码。
    """
    lines = ["erDiagram"]
    # 声明实体
    for entity in spec.get("entities", []):
        entity_name = _node_id(entity.get("name"))
        lines.append(f"    {entity_name} {{")
        for field in entity.get("fields", []):
            field_type = _plain_text(field.get("type", ""))
            field_name = _plain_text(field.get("name", ""))
            key_type = field.get("key", "")
            key_mark = ""
            if key_type == "pk":
                key_mark = " PK"
            elif key_type == "fk":
                key_mark = " FK"
            elif key_type == "unique":
                key_mark = " UK"
            lines.append(f"        {field_type} {field_name}{key_mark}")
        lines.append("    }")

    # 声明关系
    for rel in spec.get("relationships", []):
        source = _node_id(rel.get("from"))
        target = _node_id(rel.get("to"))
        rel_type = rel.get("type", "||--||")
        label = _plain_text(rel.get("label", ""))
        lines.append(f"    {source} {rel_type} {target} : \"{label}\"")

    return "\n".join(lines)


def _build_block(spec: dict[str, Any]) -> str:
    """构建方块图 Mermaid 源码。

    Args:
        spec: 方块图规格，包含 blocks 和 connections。

    Returns:
        block-beta 语法的 Mermaid 源码。
    """
    lines = ["block-beta"]
    # 声明列数
    columns = spec.get("columns", 3)
    lines.append(f"    columns {columns}")

    # 声明方块
    for block in spec.get("blocks", []):
        block_id = _node_id(block.get("id"))
        block_type = block.get("type", "block")
        label = _plain_text(block.get("label", ""))
        if block_type == "space":
            lines.append("    space")
        elif block_type == "x":
            lines.append(f"    x")
        else:
            lines.append(f"    {block_id}[\"{label}\"]")

    # 声明连接
    for conn in spec.get("connections", []):
        source = _node_id(conn.get("from"))
        target = _node_id(conn.get("to"))
        label = _plain_text(conn.get("label", ""))
        if label:
            lines.append(f"    {source} --> \"{label}\" {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_packet(spec: dict[str, Any]) -> str:
    """构建网络包图 Mermaid 源码。

    Args:
        spec: 网络包规格，包含 title 和 fields。

    Returns:
        packet-beta 语法的 Mermaid 源码。
    """
    lines = ["packet-beta"]
    # 标题
    title = spec.get("title")
    if title:
        lines.append(f"    title {_plain_text(title)}")

    # 声明字段
    for field in spec.get("fields", []):
        field_name = _plain_text(field.get("name", ""))
        start_bit = field.get("start", 0)
        length = field.get("length", 1)
        end_bit = start_bit + length - 1
        lines.append(f"    {start_bit}-{end_bit}: \"{field_name}\"")

    return "\n".join(lines)


def _build_git(spec: dict[str, Any]) -> str:
    """构建 Git 图 Mermaid 源码。

    Args:
        spec: Git 图规格，包含 commits 和 branches。

    Returns:
        gitGraph 语法的 Mermaid 源码。
    """
    lines = ["gitGraph"]
    # 声明提交
    for commit in spec.get("commits", []):
        commit_type = commit.get("type", "commit")
        commit_id = _plain_text(commit.get("id", ""))
        tag = commit.get("tag")

        if commit_type == "commit":
            if commit_id:
                lines.append(f"    commit id: \"{commit_id}\"")
            else:
                lines.append("    commit")
            if tag:
                lines.append(f"    tag \"{_plain_text(tag)}\"")
        elif commit_type == "branch":
            branch_name = _plain_text(commit.get("name", ""))
            lines.append(f"    branch {branch_name}")
        elif commit_type == "checkout":
            branch_name = _plain_text(commit.get("name", ""))
            lines.append(f"    checkout {branch_name}")
        elif commit_type == "merge":
            branch_name = _plain_text(commit.get("name", ""))
            lines.append(f"    merge {branch_name}")
        elif commit_type == "cherry-pick":
            target_id = _plain_text(commit.get("target", ""))
            lines.append(f"    cherry-pick id: \"{target_id}\"")

    return "\n".join(lines)


def _build_activity(spec: dict[str, Any]) -> str:
    """构建活动图 Mermaid 源码。

    活动图用于描述业务流程、算法步骤、操作流程等。

    Args:
        spec: 活动图规格，包含 activities、decisions、transitions。

    Returns:
        flowchart TD 语法的 Mermaid 源码（模拟活动图）。
    """
    lines = ["flowchart TD"]
    # 开始节点
    lines.append('    start([开始])')

    # 声明活动节点
    for activity in spec.get("activities", []):
        node_id = _node_id(activity.get("id"))
        label = _plain_text(activity.get("label", ""))
        node_type = activity.get("nodeType", "activity")

        if node_type == "start":
            lines.append(f'    {node_id}([{label}])')
        elif node_type == "end":
            lines.append(f'    {node_id}([{label}])')
        elif node_type == "action":
            lines.append(f'    {node_id}[{label}]')
        elif node_type == "decision":
            lines.append(f'    {node_id}{{{label}}}')
        elif node_type == "fork" or node_type == "join":
            lines.append(f'    {node_id}==="{label}"===')
        else:
            lines.append(f'    {node_id}[{label}]')

    # 结束节点
    lines.append('    end([结束])')

    # 声明转换
    for transition in spec.get("transitions", []):
        source = _node_id(transition.get("from"))
        target = _node_id(transition.get("to"))
        label = _plain_text(transition.get("label", ""))
        if label:
            lines.append(f"    {source} -->|{label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_usecase(spec: dict[str, Any]) -> str:
    """构建用例图 Mermaid 源码。

    用例图用于描述系统功能、用户交互、需求分析。

    Args:
        spec: 用例图规格，包含 actors、usecases、relationships。

    Returns:
        flowchart LR 语法的 Mermaid 源码（模拟用例图）。
    """
    lines = ["flowchart LR"]
    # 系统边界
    system_name = _plain_text(spec.get("system", "系统"))
    lines.append(f"    subgraph {system_name}")

    # 声明用例
    for usecase in spec.get("usecases", []):
        node_id = _node_id(usecase.get("id"))
        label = _plain_text(usecase.get("label", ""))
        lines.append(f'        {node_id}(({label}))')

    lines.append("    end")

    # 声明参与者（角色）
    for actor in spec.get("actors", []):
        actor_id = _node_id(actor.get("id"))
        label = _plain_text(actor.get("label", ""))
        lines.append(f'    {actor_id}~[{label}]~')

    # 声明关系
    for rel in spec.get("relationships", []):
        source = _node_id(rel.get("from"))
        target = _node_id(rel.get("to"))
        rel_type = rel.get("type", "association")
        label = _plain_text(rel.get("label", ""))

        if rel_type == "association":
            lines.append(f"    {source} --> {target}")
        elif rel_type == "include":
            lines.append(f"    {source} -.->|<<include>>| {target}")
        elif rel_type == "extend":
            lines.append(f"    {source} -.->|<<extend>>| {target}")
        elif rel_type == "generalization":
            lines.append(f"    {source} --|> {target}")
        elif label:
            lines.append(f"    {source} -->|{label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_component(spec: dict[str, Any]) -> str:
    """构建组件图 Mermaid 源码。

    组件图用于描述系统架构、模块划分、接口依赖。

    Args:
        spec: 组件图规格，包含 components、interfaces、connections。

    Returns:
        flowchart TB 语法的 Mermaid 源码（模拟组件图）。
    """
    lines = ["flowchart TB"]

    # 声明组件
    for comp in spec.get("components", []):
        comp_id = _node_id(comp.get("id"))
        label = _plain_text(comp.get("label", ""))
        comp_type = comp.get("type", "component")

        if comp_type == "component":
            lines.append(f'    {comp_id}[("{label}")]')
        elif comp_type == "package":
            lines.append(f"    subgraph {comp_id} [{label}]")
            for child in comp.get("children", []):
                child_id = _node_id(child.get("id"))
                child_label = _plain_text(child.get("label", ""))
                lines.append(f'        {child_id}("{child_label}")')
            lines.append("    end")
        else:
            lines.append(f'    {comp_id}("{label}")')

    # 声明接口
    for interface in spec.get("interfaces", []):
        iface_id = _node_id(interface.get("id"))
        label = _plain_text(interface.get("label", ""))
        iface_type = interface.get("ifaceType", "provided")

        if iface_type == "provided":
            lines.append(f'    {iface_id}○["{label}"]')
        else:  # required
            lines.append(f'    {iface_id}⦿["{label}"]')

    # 声明连接
    for conn in spec.get("connections", []):
        source = _node_id(conn.get("from"))
        target = _node_id(conn.get("to"))
        conn_type = conn.get("type", "dependency")
        label = _plain_text(conn.get("label", ""))

        if conn_type == "dependency":
            if label:
                lines.append(f"    {source} -.->|{label}| {target}")
            else:
                lines.append(f"    {source} -.-> {target}")
        elif conn_type == "interface":
            lines.append(f"    {source} --> {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_package(spec: dict[str, Any]) -> str:
    """构建包图 Mermaid 源码。

    包图用于描述代码组织、模块依赖、架构划分。

    Args:
        spec: 包图规格，包含 packages、dependencies。

    Returns:
        flowchart TB 语法的 Mermaid 源码（模拟包图）。
    """
    lines = ["flowchart TB"]

    # 声明包
    for pkg in spec.get("packages", []):
        pkg_id = _node_id(pkg.get("id"))
        label = _plain_text(pkg.get("label", ""))

        # 检查是否有子包
        children = pkg.get("children", [])
        if children:
            lines.append(f"    subgraph {pkg_id} [{label}]")
            for child in children:
                child_id = _node_id(child.get("id"))
                child_label = _plain_text(child.get("label", ""))
                lines.append(f'        {child_id}["{child_label}"]')
            lines.append("    end")
        else:
            lines.append(f'    {pkg_id}["{label}"]')

    # 声明依赖
    for dep in spec.get("dependencies", []):
        source = _node_id(dep.get("from"))
        target = _node_id(dep.get("to"))
        dep_type = dep.get("type", "dependency")
        label = _plain_text(dep.get("label", ""))

        if dep_type == "dependency":
            lines.append(f"    {source} -.->|{label}| {target}")
        elif dep_type == "import":
            lines.append(f"    {source} -->|import| {target}")
        elif dep_type == "access":
            lines.append(f"    {source} -->|access| {target}")
        else:
            if label:
                lines.append(f"    {source} -.->|{label}| {target}")
            else:
                lines.append(f"    {source} -.-> {target}")

    return "\n".join(lines)


def _build_deployment(spec: dict[str, Any]) -> str:
    """构建部署图 Mermaid 源码。

    部署图用于描述运行环境、硬件节点、分布式系统架构。

    Args:
        spec: 部署图规格，包含 nodes、artifacts、connections。

    Returns:
        flowchart TB 语法的 Mermaid 源码（模拟部署图）。
    """
    lines = ["flowchart TB"]

    # 声明节点
    for node in spec.get("nodes", []):
        node_id = _node_id(node.get("id"))
        label = _plain_text(node.get("label", ""))
        node_type = node.get("type", "device")

        if node_type == "device":
            lines.append(f'    {node_id}["{label}"]')
        elif node_type == "execution":
            lines.append(f'    {node_id}("{label}")')
        else:
            lines.append(f'    {node_id}["{label}"]')

        # 节点内的制品
        artifacts = node.get("artifacts", [])
        if artifacts:
            for artifact in artifacts:
                artifact_id = _node_id(artifact.get("id"))
                artifact_label = _plain_text(artifact.get("label", ""))
                lines.append(f'    {artifact_id}<<"{artifact_label}">>')

    # 声明连接
    for conn in spec.get("connections", []):
        source = _node_id(conn.get("from"))
        target = _node_id(conn.get("to"))
        label = _plain_text(conn.get("label", ""))
        conn_type = conn.get("type", "association")

        if conn_type == "association":
            if label:
                lines.append(f"    {source} ===|{label}| {target}")
            else:
                lines.append(f"    {source} === {target}")
        elif conn_type == "dependency":
            lines.append(f"    {source} -.->|{label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_object(spec: dict[str, Any]) -> str:
    """构建对象图 Mermaid 源码。

    对象图用于描述对象实例、运行时状态、对象关系。

    Args:
        spec: 对象图规格，包含 objects、links。

    Returns:
        flowchart TB 语法的 Mermaid 源码（模拟对象图）。
    """
    lines = ["flowchart TB"]

    # 声明对象
    for obj in spec.get("objects", []):
        obj_id = _node_id(obj.get("id"))
        obj_name = _plain_text(obj.get("name", ""))
        class_name = _plain_text(obj.get("class", ""))

        # 对象格式: objectName:ClassName
        if obj_name and class_name:
            label = f"{obj_name}:{class_name}"
        elif obj_name:
            label = obj_name
        else:
            label = class_name

        # 对象框
        lines.append(f'    {obj_id}["{label}"]')

        # 属性值
        attributes = obj.get("attributes", [])
        if attributes:
            lines.append(f'    subgraph {obj_id}_attrs ["属性"]')
            for i, attr in enumerate(attributes):
                attr_name = _plain_text(attr.get("name", ""))
                attr_value = _plain_text(attr.get("value", ""))
                attr_id = f"{obj_id}_attr_{i}"
                lines.append(f'        {attr_id}["{attr_name} = {attr_value}"]')
            lines.append("    end")

    # 声明链接
    for link in spec.get("links", []):
        source = _node_id(link.get("from"))
        target = _node_id(link.get("to"))
        label = _plain_text(link.get("label", ""))
        link_type = link.get("type", "association")

        if link_type == "association":
            if label:
                lines.append(f"    {source} ---|{label}| {target}")
            else:
                lines.append(f"    {source} --- {target}")
        elif link_type == "aggregation":
            lines.append(f"    {source} o-- {target}")
        elif link_type == "composition":
            lines.append(f"    {source} *-- {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _build_communication(spec: dict[str, Any]) -> str:
    """构建通信图 Mermaid 源码。

    通信图用于描述对象协作、消息流向、交互关系。

    Args:
        spec: 通信图规格，包含 objects、messages。

    Returns:
        flowchart LR 语法的 Mermaid 源码（模拟通信图）。
    """
    lines = ["flowchart LR"]

    # 声明对象
    for obj in spec.get("objects", []):
        obj_id = _node_id(obj.get("id"))
        obj_name = _plain_text(obj.get("name", ""))
        class_name = _plain_text(obj.get("class", ""))

        if obj_name and class_name:
            label = f"{obj_name}:{class_name}"
        else:
            label = obj_name or class_name

        lines.append(f'    {obj_id}("{label}")')

    # 声明消息
    for msg in spec.get("messages", []):
        source = _node_id(msg.get("from"))
        target = _node_id(msg.get("to"))
        label = _plain_text(msg.get("label", ""))
        seq_num = msg.get("sequence", "")

        if seq_num:
            full_label = f"{seq_num}: {label}"
        else:
            full_label = label

        if full_label:
            lines.append(f"    {source} -->|{full_label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def _edge_line(edge: dict[str, Any]) -> str:
    """构建边的 Mermaid 语法行。

    Args:
        edge: 边数据，包含 source、target、label。

    Returns:
        边的 Mermaid 语法行。
    """
    source = _node_id(edge.get("source"))
    target = _node_id(edge.get("target"))
    label = _plain_text(edge.get("label"))
    if label:
        return f"    {source} -->|{label}| {target}"
    return f"    {source} --> {target}"


def _node_id(value: Any) -> str:
    """生成合法的 Mermaid 节点ID。

    将非字母数字下划线字符替换为下划线，确保不以数字开头。

    Args:
        value: 原始节点ID值。

    Returns:
        合法的 Mermaid 节点ID。
    """
    text = str(value or "node")
    text = _SAFE_ID_RE.sub("_", text).strip("_")
    if not text:
        return "node"
    # Mermaid 节点ID 不能以数字开头
    if text[0].isdigit():
        return f"n_{text}"
    return text


def _label(item: dict[str, Any]) -> str:
    """构建节点的显示标签。

    合并 label 和 description 字段。

    Args:
        item: 节点数据。

    Returns:
        引号包裹的标签文本。
    """
    parts = [item.get("label"), item.get("description")]
    return _quoted_label(part for part in parts if part)


def _compare_label(item: dict[str, Any]) -> str:
    """构建对比项的显示标签。

    合并 label、description 和 points 字段。

    Args:
        item: 对比项数据。

    Returns:
        引号包裹的标签文本。
    """
    parts = [item.get("label"), item.get("description"), *item.get("points", [])]
    return _quoted_label(part for part in parts if part)


def _quoted_label(parts: Any) -> str:
    """将标签部分合并并用引号包裹。

    Args:
        parts: 标签部分的可迭代对象。

    Returns:
        引号包裹的标签文本。
    """
    text = "<br/>".join(_plain_text(part) for part in parts)
    return f'"{text}"'


def _plain_text(value: Any) -> str:
    """将值转换为纯文本。

    移除多余空白，替换可能破坏 Mermaid 语法的特殊字符。

    Args:
        value: 任意值。

    Returns:
        处理后的纯文本。
    """
    text = str(value or "")
    # 合并连续空白为单个空格
    text = re.sub(r"\s+", " ", text).strip()
    # 替换可能破坏 Mermaid 语法的字符
    return (
        text.replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
    )
