# OUTPUT CONTRACT

输出符合当前分段动态 Schema 的 JSON。顶层只有 `slides`，并严格保持输入页面数量与顺序。

每个 `slides[]` 只允许以下字段：

- `lead`：0～72 字符的本页核心讲解句
- `points`：0～3 项；每项只含 `label`（1～12 字符）和 `detail`（1～48 字符）
- `speaker_notes`：0～600 字符的教师讲稿

`lead` 与 `points` 至少有一个非空。禁止输出标题、页面 ID、视觉类型、布局、代码、公式、坐标、样式或其他字段。

# LESSON CONTEXT

{lesson_context}

# PREFERENCES

{preferences}

# NEIGHBOR CONTEXT

{neighbor_context}

# ASSIGNED SECTION

{section}

# COMPOSITION RULES

1. 按输入顺序逐页写作，不得新增、删除、合并或重排页面。
2. `lead` 直接回答当前页问题；`points` 补充边界、证据或操作步骤，不能复述标题。
3. 页面之间使用 `bridge` 保持承接，但不要在可见文案中机械重复“上一页/下一页”。
4. 封面、路线和总结页也使用同一文案字段，不输出视觉内容；它们的结构由后端渲染器负责。
5. `speaker_notes` 可以补充课堂提问、易错点和口头解释，但不能引入与课程材料冲突的新事实。
