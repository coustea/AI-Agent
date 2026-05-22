# Python 现代开发规范指南

本指南旨在提供一套适用于现代 Python 项目开发的标准规范，注重代码的可读性、可维护性，并充分利用现代 Python（3.8+）的优秀特性。

## 1. 命名规范

变量、函数、类的命名应简洁明了，做到见名知意，避免使用无意义、过短或含糊不清的名称。

### 1.1 变量命名
变量名应使用小写字母加下划线的形式，即 `snake_case`。

```python
# 推荐
user_name = "Tom"
student_score = 95
file_path = "/data/test.txt"
is_login = True

# 不推荐
a = "Tom"
lst = ["Tom", "Jack", "Lucy"]
flag = True
```

### 1.2 函数命名
函数名同样使用 `snake_case`，通常采用动词或动宾结构，表示函数的具体行为。

```python
# 推荐
def get_user_info(): pass
def calculate_total_score(): pass
def check_user_permission(): pass

# 不推荐
def info(): pass
def check(): pass
```

### 1.3 类命名
类名应使用大驼峰命名法，即 `PascalCase`，每个单词首字母大写。类名通常使用名词或名词短语。

```python
# 推荐
class UserService: pass
class FileProcessor: pass

# 不推荐
class user_service: pass
class fileProcessor: pass
```

### 1.4 常量命名
常量名应使用全大写字母，多个单词之间使用下划线连接。

```python
# 推荐
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 不推荐
maxRetryCount = 3
```

### 1.5 命名注意事项
1. 避免使用拼音命名，统一使用英文。
2. 避免使用无意义缩写。
3. 严禁使用 Python 内置关键字或内置函数名作为变量名（如 `list`, `str`, `dict`, `sum` 等）。

---

## 2. 类型注解 (Type Hinting) - 🌟 现代核心

现代 Python 强烈推荐使用类型注解，这能极大提升代码的可读性，并配合 IDE 提供强大的自动补全和静态检查能力。

### 2.1 函数类型注解
必须为所有公共函数的参数和返回值添加类型注解。

```python
# 推荐
def calculate_score(chinese: float, math: float) -> float:
    return chinese + math

def get_user(user_id: int) -> dict | None:  # Python 3.10+ 写法，等同于 Optional[dict]
    if user_id <= 0:
        return None
    return {"id": user_id, "name": "Tom"}
```

### 2.2 复杂类型注解
对于列表、字典等容器，应注明内部元素的类型。

```python
from typing import List, Dict

# 推荐
def process_users(users: list[str], scores: dict[str, int]) -> None:
    pass
```

---

## 3. Pythonic 编程风格 - 🌟 进阶技巧

### 3.1 上下文管理器 (Context Manager)
处理文件、网络连接、数据库连接等资源时，**必须**使用 `with` 语句，确保资源自动释放，避免内存泄漏。

```python
# 推荐
with open("data.txt", "r", encoding="utf-8") as file:
    content = file.read()

# 不推荐（容易忘记 file.close()）
file = open("data.txt", "r", encoding="utf-8")
content = file.read()
file.close()
```

### 3.2 字符串格式化
**优先使用 f-string** 进行字符串拼接，它比 `%` 或 `.format()` 更直观、运行速度更快。

```python
# 推荐
name = "Tom"
age = 18
message = f"My name is {name}, and I am {age} years old."

# 不推荐
message = "My name is %s, and I am %d years old." % (name, age)
message = "My name is {}, and I am {} years old.".format(name, age)
```

### 3.3 推导式 (Comprehensions)
在创建简单的列表、字典或集合时，推荐使用推导式，代码更简洁。

```python
# 推荐
squares = [x * x for x in range(10)]
user_map = {user.id: user.name for user in users}

# 不推荐
squares = []
for x in range(10):
    squares.append(x * x)
```

### 3.4 路径处理
推荐使用面向对象的 `pathlib.Path` 替代传统的 `os.path` 进行路径操作。

```python
from pathlib import Path

# 推荐
base_dir = Path("/data")
file_path = base_dir / "test.txt"
if file_path.exists():
    text = file_path.read_text(encoding="utf-8")
```

---

## 4. 代码格式与自动化工具

### 4.1 基本格式规范
- **缩进**：统一使用 4 个空格，**严禁**使用 Tab。
- **空行**：顶级函数和类定义之间留两个空行，类内部方法之间留一个空行。
- **空格**：二元运算符两边加一个空格，逗号后加一个空格。

### 4.2 引入自动化工具
人为规定容易出错，强烈推荐在项目中配置并强制使用以下工具：
- **格式化工具**：`Ruff` 或 `Black`（保证团队代码风格绝对统一）。
- **静态类型检查**：`Mypy` 或 `Pyright`。
- **依赖管理**：推荐使用 `uv`, `Poetry` 或标准 `requirements.txt`。

---

## 5. 注释与文档规范

### 5.1 基本注释
- 单行注释使用 `#`，并且在 `#` 后留一个空格。
- **注释应解释“为什么这样做 (Why)”，而不是解释“代码在做什么 (What)”**。代码本身应尽量做到自解释。

### 5.2 文档字符串 (Docstring)
公共模块、类和复杂的函数，必须包含 Docstring。推荐使用 `Google Style` 或 `Sphinx Style`。

```python
# 推荐 (Google Style)
def fetch_data(url: str, timeout: int = 10) -> dict:
    """
    从指定 URL 获取 JSON 数据。

    Args:
        url (str): 目标 API 的完整 URL 地址。
        timeout (int, optional): 请求超时时间（秒）. Defaults to 10.

    Returns:
        dict: 解析后的 JSON 数据字典。

    Raises:
        ConnectionError: 网络请求失败时抛出。
    """
    pass
```

---

## 6. 函数与类设计

### 6.1 单一职责原则
一个函数或类只负责完成一件明确的事情。避免出现上百行的“上帝函数”或“上帝类”。

### 6.2 成员变量与访问控制
Python 没有真正的私有修饰符，通常依靠命名约定来表明可见性：
- **公共属性 (Public)**：正常的 `snake_case` 命名，外部可以直接访问。
- **内部/私有属性 (Private/Protected)**：以单下划线 `_` 开头（如 `_internal_state`），表示这是内部实现，**外部不应直接访问或修改**。
- **避免使用双下划线 `__`**：除非为了避免子类命名冲突（Name Mangling），一般开发中优先使用单下划线。

```python
class Account:
    def __init__(self, balance: float):
        self.balance = balance       # 公共属性
        self._password = "123"       # 内部属性，外部不应直接调用
```

### 6.3 属性访问 (Getter / Setter)
**严禁**像 Java 那样无脑编写 `get_name()` 和 `set_name()`。直接暴露属性即可；当需要控制赋值逻辑或动态计算属性时，使用 `@property` 装饰器。

```python
# 推荐
class User:
    def __init__(self, age: int):
        self._age = age

    @property
    def age(self) -> int:
        return self._age

    @age.setter
    def age(self, value: int):
        if value < 0:
            raise ValueError("年龄不能为负数")
        self._age = value

# 严禁 (不要写 Java 风格的代码)
class UserBad:
    def get_age(self): return self._age
    def set_age(self, value): self._age = value
```

### 6.4 方法类型选择
正确区分和使用实例方法、类方法和静态方法：
- **实例方法**：第一个参数必须是 `self`，需要访问对象状态时使用。
- **类方法 (`@classmethod`)**：第一个参数必须是 `cls`，通常用于实现备用构造函数（工厂方法）或修改类级别的状态。
- **静态方法 (`@staticmethod`)**：不需要 `self` 也不需要 `cls`，相当于放置在类命名空间内的普通函数。

```python
class DateUtils:
    @classmethod
    def from_string(cls, date_str: str) -> "DateUtils":
        # 常用作工厂方法
        pass

    @staticmethod
    def is_valid_format(date_str: str) -> bool:
        # 不依赖类状态的纯函数，只与输入参数有关
        return len(date_str) == 10
```

### 6.5 参数设计
- 函数参数不宜过多（通常不超过 4-5 个）。
- 如果参数过多，应考虑将其封装为 `dataclass` (数据类) 或 `Pydantic` 模型。

```python
from dataclasses import dataclass

@dataclass
class UserConfig:
    name: str
    age: int
    gender: str
    phone: str

# 推荐
def create_user(config: UserConfig): pass
```

---

## 7. 异常处理规范

### 7.1 精准捕获异常
**严禁**使用裸露的 `except:`，必须明确捕获具体的异常类型。

```python
# 推荐
try:
    result = 10 / number
except ZeroDivisionError:
    print("除数不能为 0")

# 严禁
try:
    result = 10 / number
except Exception:  # 或 except:
    pass # 吞掉所有异常，导致极难排查 bug
```

### 7.2 避免异常滥用
不要用异常处理来替代常规的业务逻辑判断（如可以用 `if file.exists()` 检查，就不要依赖捕获 `FileNotFoundError` 作为主逻辑，除非遇到竞态条件）。

---

## 8. 异步编程规范 (Async/Await)

在使用 `asyncio` 或异步框架（如 FastAPI、AIOHTTP）时，需严格遵守以下规则：
1. **区分同步与异步**：在 `async def` 定义的异步函数内，**绝对禁止**调用同步阻塞型 I/O 库（如 `requests`, `time.sleep()`, 同步文件读写）。
2. **替代方案**：使用 `httpx` 或 `aiohttp` 替代 `requests`，使用 `asyncio.sleep()` 替代 `time.sleep()`，使用 `aiofiles` 进行异步文件操作。

```python
import asyncio
import httpx

# 推荐
async def fetch_user_async():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/user")
        return response.json()
```

---

## 9. 模块与导入规范

### 9.1 文件命名
Python 文件和模块名应使用简短的小写字母及下划线：`user_service.py`。

### 9.2 导入顺序
导入语句应分组放置，遵循以下顺序，各组之间空一行：
1. 标准库导入 (`os`, `sys`, `json` 等)
2. 第三方库导入 (`requests`, `pydantic` 等)
3. 本地项目模块导入 (`from src.utils import xxx`)

### 9.3 避免通配符导入
严禁使用 `from module import *`，这会污染当前命名空间，且无法静态分析依赖来源。

---

## 10. 代码可读性原则

1. **避免魔法数字 (Magic Numbers)**：禁止直接在代码里硬编码意义不明的数字。
    ```python
    # 不推荐
    if status == 2: pass
    
    # 推荐
    STATUS_SUCCESS = 2
    if status == STATUS_SUCCESS: pass
    ```
2. **DRY 原则 (Don't Repeat Yourself)**：消除重复代码。
3. **提前返回 (Early Return)**：利用卫语句 (Guard Clauses) 提前返回，减少 if/else 的嵌套层级。
    ```python
    # 推荐
    def process_order(order):
        if not order:
            return
        if order.is_paid:
            return
        # 执行正常处理逻辑...
    ```

---

## 11. 项目分层与 ORM 开发规范

现代 Python Web 开发普遍使用 ORM 框架（如 SQLAlchemy, SQLModel, Tortoise ORM 等）。良好的分层架构能避免代码耦合，提升可维护性和可测试性。

### 11.1 标准分层架构模式
对于中大型项目，推荐采用经典的 路由-服务-数据访问 三层架构（Controller-Service-Repository）：

1. **路由/视图层 (API / Router)**：只负责处理 HTTP 请求与响应、参数校验、鉴权。**严禁**在这一层直接编写 ORM 查询代码。
2. **业务逻辑层 (Service)**：负责核心业务规则的实现。这一层调用数据访问层获取数据，并进行业务组装。
3. **数据访问层 (Repository / DAO)**：专门负责与数据库打交道，封装所有的 ORM 查询、插入、更新等逻辑。

> **💡 务实建议 (关于是否有必要写 Repo 层)**：
> 严格来说，像 SQLAlchemy 这样的高级 ORM 本身就已经实现了 Repository 和 Unit of Work 模式。
> - **对于简单的增删改查项目**：允许直接在 Service 层调用 ORM（即两层架构 Router -> Service），避免过度设计。
> - **对于复杂/企业级项目**：依然强烈建议保留 Repo 层。这主要是为了**方便单元测试**（Mock ORM 的链式调用极其痛苦，而 Mock Repo 接口非常简单）、**复用复杂查询逻辑**以及**方便后续统一接入缓存（如 Redis）**。

### 11.2 模型隔离 (Model vs Schema)
在使用 ORM 时，必须严格区分**数据库模型**和**数据传输模型**：
- **ORM 模型 (Models)**：对应数据库表结构。应尽量限制在 Repository 和 Service 层内部流通。
- **数据传输对象 (DTOs / Schemas)**：用于 API 的输入验证和输出格式化（通常使用 `Pydantic` 模型）。
- **绝对避免**直接将 ORM 模型对象当作 API 返回值抛出给客户端。这不仅会导致密码等敏感数据意外泄露，还可能在 JSON 序列化时触发未加载的延迟关系（Lazy Loading）异常。

```python
# 推荐的分层代码结构示例：

# 1. repository.py (数据访问层 - 只处理 ORM)
class UserRepository:
    def __init__(self, session):
        self.session = session
        
    def get_by_id(self, user_id: int) -> User:  # 返回 ORM 模型
        return self.session.query(User).filter(User.id == user_id).first()

# 2. service.py (业务逻辑层 - 处理规则与模型转换)
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        
    def get_user_profile(self, user_id: int) -> UserResponse: # 返回 Pydantic Schema
        user = self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        # 将 ORM 模型转换为 Pydantic Schema 后返回
        return UserResponse(id=user.id, name=user.name)

# 3. api.py (路由层 - 极简主义)
@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, service: UserService = Depends(get_user_service)):
    # 路由层非常薄，不做任何数据库查询
    return service.get_user_profile(user_id)
```

### 11.3 会话 (Session) 管理原则
- **依赖注入**：数据库会话（Session）应该在请求的生命周期开始时被创建，结束时关闭。应通过依赖注入传递给底层的 Repository 或 Service。
- **避免全局 Session**：**严禁**在文件顶部创建一个全局的 `session` 实例并在各处复用，这在多线程或协程（如 FastAPI）环境下会导致严重的数据错乱和状态共享问题。

---

## 12. AI 与 Agent 架构分层规范 (AI-Native Architecture)

在开发涉及到大语言模型（LLM）或智能体（Agent）的项目时，由于 Prompt 拼接、模型非确定性输出和长时延等特性，代码极易变得难以维护。因此，必须将**大模型决策层**与传统的**业务服务层、数据库操作**严格解耦。

### 12.1 智能体四层架构模型
在经典的“路由-服务-数据”三层之上，引入专门的**智能体层 (Agent Layer)**：

1. **路由层 (API / Router)**：接收用户请求（如 WebSockets 或 RESTful 聊天接口）。
2. **编排/服务层 (Service / Orchestrator)**：作为系统的“双手”。
   - **核心职责**：调用 Repository 获取历史上下文数据 -> 将纯数据传入 Agent 层获取决策 -> 根据决策结果调用 Repository 写库或返回给用户。
3. **决策/智能体层 (Agent / LLM Layer)**：作为系统的“大脑”。
   - **核心职责**：管理 Prompt 模板、组装记忆上下文、调用外部大模型 API、解析模型输出（如强制 JSON 输出解析）。
   - **绝对禁区**：**严禁在这一层直接导入数据库 Session 或进行任何 CRUD 操作。** 该层的输入输出必须是纯粹的 Pydantic 模型或基础数据类型。
4. **数据访问层 (Repository / DAO)**：负责对关系型数据库、向量数据库（Vector DB）或图数据库的存取操作。

### 12.2 解耦的核心优势
- **安全沙箱化**：Agent 处理的输入往往来自不可控的外部用户（存在 Prompt Injection 风险）。剥离其数据库访问权限，可以防止模型失控导致的数据破坏。
- **评估与测试 (Eval & Testing)**：大模型逻辑具有非确定性，需要频繁进行 Prompt 调优。将 Agent 层独立后，可以仅用内存假数据对其进行大批量的离线测试和效果评估（Evals），无需依赖真实数据库。

### 12.3 工具调用 (Tool Calling) 的边界原则
当 Agent 具备调用外部工具（Tools / Functions）的能力时，需遵循严格的职责边界：
- **Agent 层的作用**：仅负责根据上下文推理出**“应该调用哪个工具，以及传递什么参数”**。
- **Tool 执行的落地**：Agent 将工具调用意图返回给 **Service 层**。由 Service 层去具体执行该函数（如修改数据库状态），然后将执行结果作为新一轮上下文喂回给 Agent。Agent 层本身绝不应该“亲自动手”去执行会改变系统状态的危险操作。
