# Python 项目代码规范（给 Claude Code 使用）

> 本规范参考 Google Python Style Guide 与 PEP 8，并结合工程项目实践整理。Claude Code 在修改、生成、重构 Python 代码时，必须优先遵循本文档。若项目已有更严格的本地规则，以项目规则为准。

## 1. 总体原则

### 1.1 代码目标

Python 代码必须做到：

1. **清晰优先**：代码要让人容易读懂，而不是追求炫技。
2. **命名准确**：变量、函数、类、模块名必须表达真实含义。
3. **结构简单**：不要过度封装，不要为了设计模式而设计模式。
4. **职责单一**：一个函数只做一件明确的事情。
5. **可测试**：核心逻辑应能通过单元测试验证。
6. **可维护**：避免隐藏副作用，避免难以追踪的数据流。
7. **类型明确**：公共函数、核心业务函数必须写类型注解。

### 1.2 Claude Code 执行要求

Claude Code 修改项目时必须遵守：

- 不要为了兼容旧代码保留无意义的重复逻辑。
- 允许直接重构不合理的命名、结构和函数拆分。
- 不要生成过长、过深、过抽象的代码。
- 不要写“看起来很高级但实际难维护”的代码。
- 不要把简单逻辑拆成大量碎片函数。
- 不要引入项目中没有使用的复杂依赖。
- 修改后要保证代码可以运行、类型清晰、命名统一。

## 2. 文件与模块规范

### 2.1 文件命名

Python 文件名使用小写字母和下划线：

```text
user_service.py
resource_agent.py
learning_profile.py
llm_manager.py
```

不要使用：

```text
UserService.py
resourceAgent.py
learning-profile.py
utils2.py
new_code.py
```

### 2.2 模块职责

一个模块只放一类相关逻辑。

推荐结构：

```text
app/
  api/              # 接口层
  core/             # 配置、常量、基础设施
  models/           # 数据库模型
  schemas/          # Pydantic 请求/响应模型
  services/         # 业务服务
  agents/           # 智能体逻辑
  repositories/     # 数据访问
  utils/            # 通用工具
  tests/            # 测试代码
```

避免：

- 一个文件超过 800 行仍然继续堆逻辑。
- `utils.py` 中放入大量无关函数。
- API 路由中直接写复杂业务逻辑。
- 数据库操作、LLM 调用、业务判断混在同一个函数中。

## 3. 命名规范

### 3.1 通用命名规则

命名必须表达业务含义，不要使用无意义缩写。

推荐：

```python
user_profile
learning_need
resource_id
generate_quiz
load_user_profile
```

避免：

```python
up
ln
rid
gen_qz
handle_data
process_info
```

### 3.2 变量命名

变量使用 `snake_case`。

```python
user_id = 1001
learning_goal = "掌握 Python 异步编程"
selected_agents = ["content", "quiz"]
```

布尔变量要体现真假含义：

```python
is_active = True
has_profile = False
should_retry = True
can_generate = True
```

避免：

```python
active = True
flag = False
status = True
ok = True
```

### 3.3 函数命名

函数使用动词或动宾结构，表达“做什么”。

推荐：

```python
def load_user_profile(user_id: int) -> UserProfile:
    ...


def generate_resource_plan(context: PlanningContext) -> ResourcePlan:
    ...


def save_agent_result(result: AgentResult) -> None:
    ...
```

避免：

```python
def user_profile(user_id):
    ...


def handle(context):
    ...


def do(result):
    ...
```

### 3.4 类命名

类名使用 `PascalCase`，表示明确实体或职责。

```python
class UserService:
    ...


class ResourceAgent:
    ...


class PlanningContext:
    ...
```

避免万能类：

```python
class Manager:
    ...


class Processor:
    ...


class Handler:
    ...
```

除非业务含义非常明确，例如 `LlmManager`、`EventHandler`。

### 3.5 常量命名

常量使用全大写和下划线：

```python
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT_SECONDS = 30
SUPPORTED_RESOURCE_TYPES = {"content", "quiz", "mindmap"}
```

### 3.6 私有成员命名

模块内部函数、类内部辅助方法使用单下划线：

```python
def _normalize_agent_name(name: str) -> str:
    ...


class ResourceService:
    def _build_resource_title(self, learning_need: str) -> str:
        ...
```

不要滥用双下划线。

## 4. 代码格式规范

### 4.1 缩进

统一使用 4 个空格缩进，不使用 Tab。

### 4.2 行长度

建议最大行长度为 88 或 100。项目如果使用 Black，优先遵循 Black 默认规则。

过长表达式要换行：

```python
result = await agent.generate(
    user_id=user_id,
    learning_need=learning_need,
    context=context,
)
```

### 4.3 import 顺序

导入顺序分三组：

1. 标准库
2. 第三方库
3. 项目内部模块

```python
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.user_service import UserService
from app.schemas.user import UserProfileResponse
```

不要在同一行导入多个不相关模块：

```python
# 不推荐
import os, sys, json
```

推荐：

```python
import json
import os
import sys
```

### 4.4 字符串格式化

优先使用 f-string：

```python
message = f"用户 {user_id} 的资源生成完成"
```

不要使用复杂的字符串拼接：

```python
# 不推荐
message = "用户 " + str(user_id) + " 的资源生成完成"
```

## 5. 类型注解规范

### 5.1 必须写类型注解的场景

以下位置必须写类型注解：

- 公共函数
- 业务服务函数
- 智能体输入输出函数
- 数据库访问函数
- API 层请求和响应
- 复杂数据结构

```python
def get_resource(resource_id: int) -> ResourceDetail:
    ...


async def generate_quiz(context: QuizContext) -> QuizResult:
    ...
```

### 5.2 可省略类型注解的场景

非常简单的局部变量可以不写：

```python
count = 0
name = user.name
```

复杂结构建议写清楚：

```python
agent_results: dict[str, AgentResult] = {}
resource_types: list[str] = ["content", "quiz"]
```

### 5.3 不要使用过宽泛的类型

避免：

```python
def generate(data: dict) -> dict:
    ...
```

推荐：

```python
def generate(request: ResourceGenerateRequest) -> ResourceGenerateResponse:
    ...
```

如果确实需要动态结构，使用：

```python
from typing import Any

metadata: dict[str, Any]
```

## 6. 函数设计规范

### 6.1 函数长度

函数建议控制在 30 到 60 行以内。

如果函数过长，优先按业务步骤拆分：

```python
def generate_resources(request: GenerateRequest) -> ResourceBundle:
    profile = load_profile(request.user_id)
    plan = build_plan(request, profile)
    results = run_agents(plan)
    return assemble_bundle(results)
```

### 6.2 函数参数

参数不要过多。超过 5 个参数时，优先使用数据对象封装。

避免：

```python
def generate(user_id, major, grade, course, need, style, count):
    ...
```

推荐：

```python
def generate(request: GenerateResourceRequest) -> ResourceBundle:
    ...
```

### 6.3 函数返回值

返回值要稳定，不要有时返回对象、有时返回 `None`、有时返回字符串。

避免：

```python
def get_user(user_id: int):
    if not user_id:
        return "error"
    if not found:
        return None
    return user
```

推荐：

```python
def get_user(user_id: int) -> User | None:
    ...
```

或者抛出明确异常：

```python
def require_user(user_id: int) -> User:
    if user is None:
        raise UserNotFoundError(user_id)
    return user
```

## 7. 类设计规范

### 7.1 类的职责

一个类只负责一类事情。

推荐：

```python
class UserService:
    """处理用户相关业务。"""


class ResourceRepository:
    """处理资源数据读写。"""


class QuizAgent:
    """生成练习题资源。"""
```

避免：

```python
class SystemManager:
    """既处理用户，又处理资源，又调用模型，又写数据库。"""
```

### 7.2 不要滥用继承

优先使用组合，而不是复杂继承。

推荐：

```python
class ResourceService:
    def __init__(self, repository: ResourceRepository, agent_runner: AgentRunner):
        self.repository = repository
        self.agent_runner = agent_runner
```

避免创建多层抽象父类，除非多个子类确实有稳定的一致行为。

## 8. 注释规范

### 8.1 注释写“为什么”，不是重复“做什么”

避免：

```python
# 遍历用户列表
for user in users:
    ...
```

推荐：

```python
# 这里先过滤未初始化画像的用户，避免后续资源推荐出现空画像误判。
active_users = [user for user in users if user.profile_ready]
```

### 8.2 中文项目可以使用中文注释

如果项目主要面向中文开发者，可以使用中文注释。注释要简短、准确、有用。

推荐：

```python
# 星火接口偶发 busy，短暂重试可以提高生成成功率。
await retry_llm_call(request)
```

避免：

```python
# 调用函数
await retry_llm_call(request)
```

### 8.3 不要保留废弃注释代码

禁止提交：

```python
# old_result = run_old_agent(data)
# print(old_result)
# TODO: maybe use this later
```

不用的代码直接删除。

## 9. Docstring 规范

### 9.1 模块 Docstring

复杂模块顶部应说明模块职责：

```python
"""资源生成服务。

负责接收学习需求，调用多智能体生成资源，并将结果保存到数据库。
"""
```

### 9.2 类 Docstring

公共类需要写明职责：

```python
class ResourceService:
    """编排学习资源生成、保存和查询的业务服务。"""
```

### 9.3 函数 Docstring

复杂公共函数应使用 Google 风格 Docstring：

```python
def build_learning_plan(
    profile: UserProfile,
    resources: list[LearningResource],
) -> LearningPlan:
    """根据用户画像和资源列表生成学习路径。

    Args:
        profile: 用户学习画像。
        resources: 已生成的学习资源列表。

    Returns:
        适合当前用户的学习路径。

    Raises:
        ValueError: 当资源列表为空时抛出。
    """
```

### 9.4 简单函数不必强行写 Docstring

简单函数可以不写 Docstring，但命名必须清晰：

```python
def is_empty_text(text: str | None) -> bool:
    return text is None or not text.strip()
```

## 10. 异常处理规范

### 10.1 捕获具体异常

避免：

```python
try:
    result = await llm.ainvoke(prompt)
except Exception:
    return None
```

推荐：

```python
try:
    result = await llm.ainvoke(prompt)
except TimeoutError as exc:
    raise LlmTimeoutError("模型调用超时") from exc
```

### 10.2 不要吞异常

禁止无声失败：

```python
try:
    save_result(result)
except Exception:
    pass
```

至少记录日志，或转换成业务异常：

```python
try:
    save_result(result)
except DatabaseError as exc:
    logger.exception("保存智能体结果失败: resource_id=%s", result.resource_id)
    raise ResourceSaveError("保存资源失败") from exc
```

### 10.3 自定义异常命名

业务异常使用清晰名称：

```python
class UserNotFoundError(Exception):
    """用户不存在。"""


class ResourceGenerationError(Exception):
    """学习资源生成失败。"""
```

## 11. 日志规范

### 11.1 使用 logger，不使用 print

禁止在业务代码中使用 `print()`。

推荐：

```python
logger.info("开始生成资源: user_id=%s, request_id=%s", user_id, request_id)
logger.warning("用户画像不存在，使用默认画像: user_id=%s", user_id)
logger.exception("资源生成失败: user_id=%s", user_id)
```

### 11.2 日志要包含关键上下文

日志中应包含：

- user_id
- request_id
- resource_id
- agent_name
- task_id
- elapsed_time

避免只有：

```python
logger.info("success")
logger.error("failed")
```

## 12. API 层规范

### 12.1 API 层只做请求处理

API 路由只负责：

1. 接收参数
2. 调用 service
3. 返回响应

不要在 API 中写复杂业务逻辑。

```python
@router.post("/resources", response_model=ResourceResponse)
async def create_resource(
    request: ResourceCreateRequest,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    return await service.create_resource(request)
```

### 12.2 请求和响应必须使用 Schema

不要直接返回数据库模型。

推荐：

```python
class ResourceCreateRequest(BaseModel):
    learning_need: str
    resource_types: list[str]


class ResourceResponse(BaseModel):
    id: int
    title: str
    status: str
```

## 13. 数据库代码规范

### 13.1 数据访问放在 Repository

不要在 service 中散落 SQL 查询。

```python
class ResourceRepository:
    async def get_by_id(self, resource_id: int) -> Resource | None:
        ...

    async def save(self, resource: Resource) -> Resource:
        ...
```

### 13.2 事务边界清晰

涉及多个写操作时，必须明确事务边界。

```python
async with session.begin():
    await repository.save_resource(resource)
    await repository.save_agent_results(results)
```

## 14. LLM / Agent 代码规范

### 14.1 Prompt 与业务逻辑分离

不要把很长的 prompt 直接塞在业务函数中。

推荐：

```text
app/agents/prompts/resource_planner.md
app/agents/prompts/quiz_agent.md
```

Python 中只负责加载和填充：

```python
prompt = prompt_loader.render(
    "quiz_agent.md",
    learning_need=request.learning_need,
    profile=profile,
)
```

### 14.2 Agent 输入输出必须结构化

Agent 输出优先使用 Pydantic 或明确 JSON Schema。

```python
class QuizResult(BaseModel):
    title: str
    questions: list[QuizQuestion]
```

不要让下游解析不稳定的自然语言文本。

### 14.3 Agent 命名统一

Agent 类名：

```python
ContentAgent
MindmapAgent
DiagramAgent
CodeAgent
QuizAgent
ReadingAgent
VideoAgent
```

Agent 标识：

```python
content
mindmap
diagram
code
quiz
reading
video
```

不要混用：

```python
content_agent
Content
contentAgent
CONTENT_AGENT
```

## 15. 测试规范

### 15.1 测试文件命名

```text
test_user_service.py
test_resource_agent.py
test_learning_plan.py
```

### 15.2 测试函数命名

测试函数使用明确行为描述：

```python
def test_generate_quiz_returns_requested_question_count():
    ...


def test_load_profile_returns_default_when_profile_missing():
    ...
```

### 15.3 优先测试核心业务逻辑

必须优先覆盖：

- 资源规划逻辑
- Agent 输出校验
- 数据保存逻辑
- 异常处理逻辑
- SSE 事件状态转换
- 用户画像初始化逻辑

## 16. 工具与自动检查

### 16.1 推荐工具

建议项目使用：

```text
ruff        # lint 和部分格式检查
black       # 自动格式化
mypy        # 类型检查
pytest      # 单元测试
```

### 16.2 推荐命令

```bash
ruff check .
black .
mypy app
pytest
```

如果项目使用 `pyproject.toml`，建议统一配置格式化、lint、测试规则。

## 17. 禁止行为清单

Claude Code 不允许生成以下代码：

```python
# 1. 无意义命名
x = get_data()
res = do_stuff(x)

# 2. 裸 except
try:
    run()
except:
    pass

# 3. 大量 print
print("debug")

# 4. 超长函数
async def generate_everything(...):
    # 几百行逻辑
    ...

# 5. 混乱返回类型
def get_result():
    if error:
        return False
    if empty:
        return None
    return {"data": data}

# 6. 无意义注释
# 调用函数
call_function()

# 7. 魔法数字
if retry_count > 7:
    ...
```

应该改成：

```python
MAX_RETRY_COUNT = 7

if retry_count > MAX_RETRY_COUNT:
    ...
```

## 18. Claude Code 修改代码时的最终检查清单

每次修改后，Claude Code 必须检查：

- [ ] 命名是否清晰，是否见名知意。
- [ ] 函数是否过长，是否承担过多职责。
- [ ] 是否有无意义兼容旧代码。
- [ ] 是否有重复逻辑可以合并。
- [ ] 是否有裸 `except` 或吞异常。
- [ ] 是否使用了类型注解。
- [ ] 是否存在无意义注释或废弃注释代码。
- [ ] 是否使用 logger 而不是 print。
- [ ] API 层是否只负责请求和响应。
- [ ] Service、Repository、Agent 职责是否清晰。
- [ ] LLM 输出是否结构化。
- [ ] 修改后是否能通过格式化、lint、类型检查和测试。

## 19. 推荐给 Claude Code 的执行提示词

可以把下面这段放进 Claude Code：

```text
请严格遵循项目根目录的 PYTHON_CODE_STYLE.md 修改代码。

修改要求：
1. 命名必须简洁、准确、见名知意。
2. 函数职责必须单一，不要写超长函数。
3. 允许直接重构不合理代码，不需要兼容旧实现。
4. 删除无用代码、重复代码、废弃注释和无意义抽象。
5. 公共函数、业务函数、Agent 输入输出必须写类型注解。
6. 注释只解释关键原因和复杂逻辑，不要重复代码含义。
7. 异常必须明确处理，不允许裸 except 和 pass 吞异常。
8. 业务代码使用 logger，不要使用 print。
9. API、Service、Repository、Agent 分层要清晰。
10. 修改完成后运行格式化、lint、类型检查和测试，并修复发现的问题。
```

