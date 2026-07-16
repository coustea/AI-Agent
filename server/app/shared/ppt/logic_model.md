# OUTPUT CONTRACT

输出符合 `DeckLogicDraft` 的 JSON。只输出字段白名单中的教学语义，不得添加额外字段。

## 枚举约束

- `course_domain` 只能是：{course_domains}
- `nodes[].role` 只能是：{logic_node_roles}

## 字段白名单

顶层：

- `course_domain`：最能描述本课程核心知识结构的单一课程域
- `chapters`：2～5 个连续教学章节，全部章节共 5～16 个节点

每个章节：

- `title`：2～32 字符
- `nodes`：1～8 个节点，按完整教学顺序排列

每个节点：

- `title`：2～24 字符；是可直接显示在内容页上的短标题，不得复述完整问题
- `role`
- `question`：1～96 字符
- `claim`：1～120 字符
- `evidence`：1～4 条具体证据
- `output`：1～120 字符

## Renderer boundary

禁止输出任何 renderer-owned fields，包括 IDs、coordinates、styles 或 visual payload。
禁止输出章节 ID、节点 ID、边、布局、颜色、坐标、组件名和视觉类型；这些由后端编译器与视觉规划器负责。

# CONTEXT

{context}

# PREFERENCES

{preferences}

# MODELING RULES

1. 根据课程的核心知识结构选择一个 `course_domain`，不能因为示例跨领域而选择多个值。
2. 先提出问题，再建立前提、概念或证据，随后形成机制、方法、应用和结论。
3. 每个节点必须写出短 `title`、`question`、`claim`、至少一条具体 `evidence` 和可交给后续节点的 `output`。
4. 证据可以是定义约束、可验证推导、代码行为、反例或课程材料，不能只写“教材指出”。
5. 每个节点必须属于且仅属于一个章节；数组顺序就是后端构造知识链的教学推进顺序。
6. 案例和练习只能验证已经建立的概念或方法，不能引入新的核心前提。
7. 最后一个节点必须回收第一个节点提出的问题，但不能重复前文措辞堆砌总结。
8. 所有学科使用同一套教学推进方法，课程画像只指导视觉规划，不能决定逻辑节点角色。

