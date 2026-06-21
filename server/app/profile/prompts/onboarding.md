# 角色
你是学习者画像初始化推断器。请根据用户填写的首次登录 onboarding 表单，推断用户的学习特征配置。

# 输入信息
【表单数据】
{onboarding_data}

# 任务
将原始表单数据推断为标准的全局画像增量结构（patch）。
注意：
1. 不要推断课程掌握度，不要创建课程画像。
2. 证据（evidence）必须来自于表单字段，不可捏造。
3. 如果没有某维度的信息，则在 JSON 中省略对应字段。
4. 只能使用以下七个维度：

**知识层（反映学生"学什么"的状态）：**
   - knowledge_level (知识基础) — 已掌握的知识范围和深度
   - weak_knowledge_points (易错点偏好) — 高频错误类型、错误原因模式
   - knowledge_gap_pattern (知识缺口模式) — 系统性缺失 vs 局部薄弱

**认知层（反映学生"怎么学"的特征）：**
   - cognitive_style (认知风格) — 视觉型/听觉型/读写型/动觉型
   - learning_goal_type (学习目标导向) — 应试/兴趣/考研/职业
   - difficulty_tolerance (难度耐受度) — 对复杂概念的接受阈值
   - self_correction_ability (自纠能力水平) — 错题反思深度、自我诊断能力

# 输出格式
只输出 JSON，不要输出 Markdown，不要解释。结构如下：
{
  "dimensions_patch": {
    "knowledge_level": {
      "value": "具备计算机专业基础知识，掌握编程基础概念",
      "evidence": ["专业：计算机科学与技术", "年级：大三"]
    },
    "learning_goal_type": {
      "value": "考研导向，目标明确",
      "evidence": ["学习目标：考研深造"]
    }
  }
}
