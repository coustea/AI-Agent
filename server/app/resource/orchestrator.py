"""
资源生成编排器。

职责：
- CoordinatorAgent: 对外入口，协调所有组件
- MasterAgent: 逐层规划（每次只生成一层）
- LayerOrchestrator: 执行当前层 Agent

禁止：
- 手写循环控制（必须用 LangGraph condition edge）
- 规划时依赖未完成的 Agent
"""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.schemas import LayerPlan, WorkflowState, WorkerState
from app.resource.registry import registry, ensure_initialized
from app.resource.worker_agents import (
    ContentAgent,
    MindmapAgent,
    QuizAgent,
    CodeAgent,
    ReadingAgent,
    PptAgent,
)
from app.resource.utils import (
    update_agent_status,
    load_profile_snapshot,
    init_workspace,
    read_manifest,
)

logger = get_logger(__name__)

# 最大层数限制
MAX_LAYERS = 10


class CoordinatorAgent:
    """协调器 Agent — 对外唯一入口。"""

    def __init__(self, emitter: AgentEventEmitter, resource_store: Any):
        self.emitter = emitter
        self.resource_store = resource_store

    async def run(
        self,
        user_id: int,
        task: dict[str, Any],
        selected_resources: list[str] | None = None,
    ) -> dict[str, Any]:
        """执行资源生成工作流。"""
        logger.info(
            "[Coordinator] 开始执行: user_id=%s course=%r selected=%s",
            user_id,
            task.get("course", ""),
            selected_resources,
        )

        graph = ResourceWorkflow(
            emitter=self.emitter,
            resource_store=self.resource_store,
        )

        result = await graph.run(
            user_id=user_id,
            task=task,
            selected_resources=selected_resources,
        )

        logger.info(
            "[Coordinator] 执行完成: user_id=%s success=%s",
            user_id,
            result.get("success", False),
        )

        return result


class MasterAgent:
    """主控规划 Agent — 逐层规划，不执行。"""

    def __init__(self):
        self.llm_manager = get_llm_manager()
        ensure_initialized()

    def _get_all_agents(self) -> list[str]:
        return registry.get_names()

    def _get_dependencies(self, agent: str) -> list[str]:
        return registry.get_dependencies(agent)

    def _get_execution_layer(self, agent: str) -> int:
        return registry.get_execution_layer(agent)

    def _expand_requested_agents(self, selected_resources: list[str] | None) -> list[str]:
        """展开用户选择的 Agent，补齐依赖闭包，并按注册顺序返回。"""
        all_agents = self._get_all_agents()
        if not selected_resources:
            return all_agents

        seed = [a for a in selected_resources if a in all_agents]
        closure: set[str] = set()
        stack = list(seed)
        while stack:
            agent = stack.pop()
            if agent in closure:
                continue
            closure.add(agent)
            stack.extend(self._get_dependencies(agent))

        return [a for a in all_agents if a in closure]

    async def plan_next_layer(
        self,
        state: WorkflowState,
        completed_agents: list[str],
        artifact_manifest: dict[str, Any],
    ) -> LayerPlan | None:
        """规划下一层执行计划。返回 None 表示结束。"""
        layer_index = state.layer_index

        if layer_index >= MAX_LAYERS:
            logger.info("[MasterAgent] 达到最大层数限制: %s", MAX_LAYERS)
            return None

        # 尝试 LLM 规划
        try:
            plan = await self._llm_plan(state, completed_agents, artifact_manifest)
            if plan:
                logger.info("[MasterAgent] LLM 规划成功: layer=%s agents=%s", plan.layer_index, plan.agents)
                return plan
        except Exception as exc:
            logger.warning("[MasterAgent] LLM 规划失败，使用 fallback: %s", exc)

        # Fallback：基于规则的规划
        plan = self._fallback_plan(state, completed_agents)
        if plan:
            logger.info("[MasterAgent] Fallback 规划: layer=%s agents=%s", plan.layer_index, plan.agents)
        return plan

    async def _llm_plan(
        self,
        state: WorkflowState,
        completed_agents: list[str],
        artifact_manifest: dict[str, Any],
    ) -> LayerPlan | None:
        """使用 LLM 规划下一层。"""
        requested_agents = self._expand_requested_agents(state.task.get("selected_resources"))
        visible_agents = state.task.get("selected_resources") or requested_agents
        remaining = [a for a in requested_agents if a not in completed_agents]

        if not remaining:
            return None

        prompt = self._build_planning_prompt(state, completed_agents, remaining, artifact_manifest)

        response = await self.llm_manager.ainvoke(
            "deepseek",
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请输出下一层的执行计划（JSON 格式）。"),
            ],
            model_kwargs={"temperature": 0.3},
        )

        from app.shared.json_utils import parse_first_json_object

        content = response.content if hasattr(response, "content") else str(response)
        plan_data = parse_first_json_object(content)

        if not plan_data:
            raise ValueError("LLM 未返回有效 JSON")

        planned_agents = [a for a in plan_data.get("agents", []) if a in requested_agents]
        executable_agents = [
            a
            for a in planned_agents
            if all(dep in completed_agents for dep in self._get_dependencies(a))
        ]

        return LayerPlan(
            layer_index=state.layer_index,
            reason=plan_data.get("reason", ""),
            agents=executable_agents,
            dependencies={a: self._get_dependencies(a) for a in executable_agents},
            agent_parameters=plan_data.get("agent_parameters", {}),
            expected_outputs=plan_data.get("expected_outputs", {}),
            visible_agents=[a for a in executable_agents if a in visible_agents],
            hidden_dependency_agents=[a for a in executable_agents if a not in visible_agents],
            failure_policy=plan_data.get("failure_policy", {}),
            stop_after_this_layer=plan_data.get("stop_after_this_layer", False),
        )

    def _build_planning_prompt(
        self,
        state: WorkflowState,
        completed_agents: list[str],
        remaining: list[str],
        artifact_manifest: dict[str, Any],
    ) -> str:
        """构建规划 prompt。"""
        return f"""你是一个资源生成规划器。请根据当前状态规划下一层要执行的 Agent。

## 当前状态
- 层索引: {state.layer_index}
- 已完成 Agent: {completed_agents}
- 剩余待执行 Agent: {remaining}
- 用户任务: {state.task}

## 已完成产物
{artifact_manifest}

## 规划规则
1. 每次只规划一层
2. 同一层 Agent 之间不能互相依赖
3. 依赖必须来自已完成 Agent
4. 必须说明为什么执行这一层（reason）
5. 必须说明每个 Agent 要做什么（expected_outputs）

## 输出格式
```json
{{
  "reason": "为什么执行这一层",
  "agents": ["agent1", "agent2"],
  "agent_parameters": {{"agent1": {{"param": "value"}}}},
  "expected_outputs": {{"agent1": "输出描述"}},
  "stop_after_this_layer": false
}}
```

请输出下一层的执行计划。"""

    def _fallback_plan(
        self,
        state: WorkflowState,
        completed_agents: list[str],
    ) -> LayerPlan | None:
        """基于规则的 fallback 规划。"""
        requested_agents = self._expand_requested_agents(state.task.get("selected_resources"))
        visible_agents = state.task.get("selected_resources") or requested_agents

        layer_agents = []
        for agent in all_agents:
            if agent in requested_agents and agent not in completed_agents:
                deps = self._get_dependencies(agent)
                if all(d in completed_agents for d in deps):
                    layer_agents.append(agent)

        if not layer_agents:
            return None

        min_layer = min(self._get_execution_layer(a) for a in layer_agents)
        current_layer_agents = [a for a in layer_agents if self._get_execution_layer(a) == min_layer]

        return LayerPlan(
            layer_index=state.layer_index,
            reason=f"Fallback 规划：执行第 {min_layer} 层 Agent",
            agents=current_layer_agents,
            dependencies={a: self._get_dependencies(a) for a in current_layer_agents},
            agent_parameters={},
            expected_outputs={a: f"生成 {a} 产物" for a in current_layer_agents},
            visible_agents=[a for a in current_layer_agents if a in visible_agents],
            hidden_dependency_agents=[a for a in current_layer_agents if a not in visible_agents],
            failure_policy={},
            stop_after_this_layer=False,
        )


class LayerOrchestrator:
    """分层执行调度器 — 执行当前层，不规划。"""

    def __init__(
        self,
        user_id: int,
        resource_id: int,
        emitter: AgentEventEmitter,
    ):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter

    async def execute_layer(
        self,
        layer_plan: LayerPlan,
        state: WorkflowState,
    ) -> dict[str, dict[str, Any]]:
        """执行单个层。"""
        results: dict[str, dict[str, Any]] = {}
        agents = layer_plan.agents

        if not agents:
            logger.info("[LayerOrchestrator] 当前层无 Agent，跳过")
            return results

        layer_index = layer_plan.layer_index
        logger.info("[LayerOrchestrator] 开始执行层 %s: agents=%s", layer_index, agents)

        # 校验依赖合法性
        validation_errors = self._validate_dependencies(layer_plan, state.completed_agents)
        if validation_errors:
            logger.error("[LayerOrchestrator] 依赖校验失败: %s", validation_errors)
            for agent_name in agents:
                results[agent_name] = {
                    "success": False,
                    "error": f"依赖校验失败: {validation_errors.get(agent_name, 'unknown')}",
                }
            return results

        # 并行执行同层 Agent
        futures = [self._execute_agent(agent_name, layer_plan, state) for agent_name in agents]

        for future in asyncio.as_completed(futures):
            agent_name, result = await future
            results[agent_name] = result

            await update_agent_status(
                user_id=self.user_id,
                resource_id=self.resource_id,
                agent_name=agent_name,
                status="completed" if result.get("success") else "failed",
                artifact_path=result.get("artifact_path"),
                error=result.get("error"),
            )

        logger.info("[LayerOrchestrator] 层 %s 执行完成: success=%d failed=%d",
                   layer_index,
                   sum(1 for r in results.values() if r.get("success")),
                   sum(1 for r in results.values() if not r.get("success")))

        return results

    def _validate_dependencies(
        self,
        layer_plan: LayerPlan,
        completed_agents: list[str],
    ) -> dict[str, str]:
        """校验依赖合法性。"""
        errors: dict[str, str] = {}
        completed_set = set(completed_agents)

        for agent_name in layer_plan.agents:
            deps = layer_plan.dependencies.get(agent_name, [])
            missing = [d for d in deps if d not in completed_set]
            if missing:
                errors[agent_name] = f"缺少依赖: {missing}"

        return errors

    async def _execute_agent(
        self,
        agent_name: str,
        layer_plan: LayerPlan,
        state: WorkflowState,
    ) -> tuple[str, dict[str, Any]]:
        """执行单个 Agent。"""
        layer_index = layer_plan.layer_index
        params = layer_plan.agent_parameters.get(agent_name, {})
        deps = layer_plan.dependencies.get(agent_name, [])

        logger.info("[LayerOrchestrator] Agent 启动: %s layer=%s deps=%s", agent_name, layer_index, deps)

        await self.emitter.emit_agent_status(
            agent_name,
            "running",
            f"Agent {agent_name} 正在执行",
            layer_index=layer_index,
        )

        try:
            worker = self._create_worker(agent_name)

            # Agent 自己负责读取依赖报告
            worker_state = WorkerState(
                agent_name=agent_name,
                task=state.task,
                profile=state.learner_profile,
                parameters=params,
                dependencies=deps,
                dependency_artifacts={},  # 不再由 orchestrator 加载
                layer_index=layer_index,
            )

            result = await worker.run(worker_state)

            if result.success:
                logger.info("[LayerOrchestrator] Agent 成功: %s artifact=%s", agent_name, result.artifact_path)
            else:
                logger.error("[LayerOrchestrator] Agent 失败: %s error=%s", agent_name, result.error)

            return agent_name, result.model_dump()

        except Exception as exc:
            logger.exception("[LayerOrchestrator] Agent 执行异常: %s", agent_name)
            error_msg = str(exc)
            return agent_name, {"success": False, "error": error_msg}

    def _create_worker(self, agent_name: str):
        """创建 Worker Agent 实例。"""
        ensure_initialized()

        agent_classes = {
            "content": ContentAgent,
            "mindmap": MindmapAgent,
            "quiz": QuizAgent,
            "code": CodeAgent,
            "reading": ReadingAgent,
            "ppt": PptAgent,
        }

        agent_cls = agent_classes.get(agent_name)
        if agent_cls:
            return agent_cls(self.user_id, self.resource_id)

        raise ValueError(f"未知的 Agent 类型: {agent_name}")


class GraphState(TypedDict):
    """LangGraph 状态。"""

    workflow_state: WorkflowState
    current_layer_plan: LayerPlan | None
    layer_results: dict[str, dict[str, Any]]
    should_continue: bool
    error: str | None


class ResourceWorkflow:
    """资源生成工作流 — LangGraph 编排。"""

    def __init__(
        self,
        emitter: AgentEventEmitter,
        resource_store: Any,
    ):
        self.emitter = emitter
        self.resource_store = resource_store
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 主流程。"""
        graph = StateGraph(GraphState)

        graph.add_node("load_profile", self._load_profile)
        graph.add_node("create_resource", self._create_resource)
        graph.add_node("plan_next_layer", self._plan_next_layer)
        graph.add_node("execute_layer", self._execute_layer)
        graph.add_node("update_state", self._update_state)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("load_profile")
        graph.add_edge("load_profile", "create_resource")
        graph.add_edge("create_resource", "plan_next_layer")
        graph.add_edge("plan_next_layer", "execute_layer")
        graph.add_edge("execute_layer", "update_state")

        graph.add_conditional_edges(
            "update_state",
            self._decide_continue,
            {
                True: "plan_next_layer",
                False: "finalize",
            },
        )

        graph.add_edge("finalize", END)

        return graph.compile()

    async def run(
        self,
        user_id: int,
        task: dict[str, Any],
        selected_resources: list[str] | None = None,
    ) -> dict[str, Any]:
        """执行资源生成工作流。"""
        initial_state: GraphState = {
            "workflow_state": WorkflowState(
                user_id=user_id,
                task={**task, "selected_resources": selected_resources},
            ),
            "current_layer_plan": None,
            "layer_results": {},
            "should_continue": True,
            "error": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            return {
                "success": final_state.get("error") is None,
                "results": final_state["workflow_state"].results,
                "error": final_state.get("error"),
            }
        except Exception as exc:
            logger.exception("[Workflow] 执行失败")
            return {
                "success": False,
                "results": {},
                "error": str(exc),
            }

    async def _load_profile(self, state: GraphState) -> dict[str, Any]:
        """加载学习者画像。"""
        workflow_state = state["workflow_state"]
        user_id = workflow_state.user_id

        logger.info("[Workflow] 加载画像: user_id=%s", user_id)

        try:
            snapshot = await load_profile_snapshot(user_id)
            workflow_state.learner_profile = snapshot.as_agent_profile()

            await init_workspace(user_id, 0)

            logger.info("[Workflow] 画像加载完成: user_id=%s", user_id)
            return {"workflow_state": workflow_state}
        except Exception as exc:
            logger.exception("[Workflow] 加载画像失败")
            return {"workflow_state": workflow_state, "error": str(exc)}

    async def _create_resource(self, state: GraphState) -> dict[str, Any]:
        """创建资源记录。"""
        workflow_state = state["workflow_state"]

        logger.info("[Workflow] 创建资源记录")

        try:
            task = workflow_state.task
            resource_record = await self.resource_store.create_resource(
                user_id=workflow_state.user_id,
                course=task.get("course", ""),
                gap=task.get("gap", ""),
                need=task.get("need", "review"),
                request_extra=task.get("extra", ""),
            )

            workflow_state.resource_id = resource_record.id
            await init_workspace(workflow_state.user_id, resource_record.id)

            logger.info("[Workflow] 资源记录创建完成: resource_id=%s", resource_record.id)
            return {"workflow_state": workflow_state}
        except Exception as exc:
            logger.exception("[Workflow] 创建资源记录失败")
            return {"workflow_state": workflow_state, "error": str(exc)}

    async def _plan_next_layer(self, state: GraphState) -> dict[str, Any]:
        """规划下一层。"""
        workflow_state = state["workflow_state"]
        logger.info("[Workflow] 规划层: layer_index=%s", workflow_state.layer_index)

        try:
            master_agent = MasterAgent()
            layer_plan = await master_agent.plan_next_layer(
                state=workflow_state,
                completed_agents=workflow_state.completed_agents,
                artifact_manifest=workflow_state.manifest,
            )

            if layer_plan:
                workflow_state.current_layer_plan = layer_plan
                workflow_state.layer_history.append(layer_plan)
                logger.info("[Workflow] 层规划完成: layer=%s agents=%s", layer_plan.layer_index, layer_plan.agents)
                return {
                    "workflow_state": workflow_state,
                    "current_layer_plan": layer_plan,
                    "should_continue": True,
                }

            logger.info("[Workflow] 无更多层需要执行")
            return {
                "workflow_state": workflow_state,
                "current_layer_plan": None,
                "should_continue": False,
            }
        except Exception as exc:
            logger.exception("[Workflow] 规划失败")
            return {
                "workflow_state": workflow_state,
                "error": str(exc),
                "should_continue": False,
            }

    async def _execute_layer(self, state: GraphState) -> dict[str, Any]:
        """执行当前层。"""
        workflow_state = state["workflow_state"]
        layer_plan = state["current_layer_plan"]

        if not layer_plan:
            return {"workflow_state": workflow_state, "layer_results": {}}

        logger.info("[Workflow] 执行层: layer_index=%s agents=%s", layer_plan.layer_index, layer_plan.agents)

        try:
            user_id = workflow_state.user_id
            resource_id = workflow_state.resource_id or 0

            layer_orchestrator = LayerOrchestrator(user_id, resource_id, self.emitter)
            results = await layer_orchestrator.execute_layer(layer_plan, workflow_state)

            return {"workflow_state": workflow_state, "layer_results": results}
        except Exception as exc:
            logger.exception("[Workflow] 执行层失败")
            return {
                "workflow_state": workflow_state,
                "layer_results": {},
                "error": str(exc),
            }

    async def _update_state(self, state: GraphState) -> dict[str, Any]:
        """更新工作流状态。"""
        workflow_state = state["workflow_state"]
        layer_results = state["layer_results"]

        for agent_name, result in layer_results.items():
            if result.get("success"):
                workflow_state.completed_agents.append(agent_name)
            workflow_state.results[agent_name] = result

        workflow_state.layer_index += 1
        workflow_state.manifest = await read_manifest(workflow_state.user_id, workflow_state.resource_id or 0)

        logger.info("[Workflow] 状态更新: layer_index=%s completed=%s", workflow_state.layer_index, workflow_state.completed_agents)
        return {"workflow_state": workflow_state}

    def _decide_continue(self, state: GraphState) -> bool:
        """条件判断：是否继续执行下一层。"""
        workflow_state = state["workflow_state"]
        layer_plan = state["current_layer_plan"]

        if state.get("error"):
            logger.info("[Workflow] 停止：有错误")
            return False
        if workflow_state.layer_index >= MAX_LAYERS:
            logger.info("[Workflow] 停止：达到最大层数")
            return False
        if layer_plan and layer_plan.stop_after_this_layer:
            logger.info("[Workflow] 停止：层计划标记停止")
            return False
        if not layer_plan or not layer_plan.agents:
            logger.info("[Workflow] 停止：无更多 Agent")
            return False
        return True

    async def _finalize(self, state: GraphState) -> dict[str, Any]:
        """完成处理。"""
        workflow_state = state["workflow_state"]

        logger.info("[Workflow] 完成: resource_id=%s completed_agents=%s", workflow_state.resource_id, workflow_state.completed_agents)

        if workflow_state.resource_id:
            if workflow_state.results and hasattr(self.resource_store, "persist_all_results"):
                await self.resource_store.persist_all_results(
                    resource_id=workflow_state.resource_id,
                    results=workflow_state.results,
                )
            await self.resource_store.update_resource_status(
                resource_id=workflow_state.resource_id,
                status="completed" if state.get("error") is None else "failed",
            )

        await self.emitter.emit_done("资源生成完成")
        return state
