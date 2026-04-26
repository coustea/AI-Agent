"""资源生成模块专用异常类。

定义了多智能体资源生成系统中可能出现的各种异常情况，
提供清晰的错误类型和上下文信息。
"""


class ResourceAgentError(Exception):
    """资源生成 Agent 基础异常类"""

    def __init__(self, message: str, agent_name: str = "", context: dict | None = None):
        # 把 agent 名直接嵌进错误文本，日志里一眼就能知道是哪一层抛出来的。
        self.agent_name = agent_name
        self.context = context or {}
        super().__init__(f"[{agent_name}] {message}" if agent_name else message)


class PlanningError(ResourceAgentError):
    """任务规划阶段异常

    当 Planner 无法解析需求、生成非法 JSON 或规划失败时抛出。
    """

    def __init__(self, message: str, raw_output: str = ""):
        super().__init__(message, agent_name="Coordinator")
        # 原始输出保留给后续排查 Planner 非法 JSON 或 prompt 漂移问题。
        self.raw_output = raw_output


# 已删除未使用的异常类：
# - KnowledgeBaseError（知识库检索异常，从未使用）
# - AgentExecutionError（Agent 执行异常，从未使用）
# - ValidationError（输出校验异常，从未使用）
# - RetryExhaustedError（重试次数耗尽异常，从未使用）
# 如需恢复，请参考 git history。