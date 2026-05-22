"""Knowledge graph resource agent."""

from __future__ import annotations

import json
from typing import Any

from app import config
from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.graph_store import get_graph_store
from app.resource.utils.graph_utils import RELATION_LABELS, normalize_render_graph
from app.resource.schemas import KnowledgeGraph, KnowledgePoint, WorkerResult, WorkerState

logger = get_logger(__name__)


class KnowledgeGraphAgent:
    """Builds a renderable/storable graph from the shared execution plan."""

    def __init__(self, emitter: AgentEventEmitter) -> None:
        self.emitter = emitter

    async def run(self, state: WorkerState) -> WorkerResult:
        agent_cfg = state.agent_config or {}
        graph = self._build_graph(state.knowledge_graph, state, agent_cfg)
        neo4j_meta = await self._store_graph(state=state, graph=graph, enabled=bool(agent_cfg.get("store_neo4j", config.NEO4J_ENABLED)))
        graph["neo4j"] = neo4j_meta

        node_count = len(graph["nodes"])
        edge_count = len(graph["edges"])
        return WorkerResult(
            success=True,
            content=json.dumps(graph, ensure_ascii=False),
            file_type="json",
            title=f"{graph['topic']} 知识图谱",
            summary=f"已生成 {node_count} 个知识点、{edge_count} 条关系的知识图谱。",
            summary_data={
                "node_count": node_count,
                "edge_count": edge_count,
                "layout_mode": graph["layout_mode"],
                "neo4j_stored": bool(neo4j_meta.get("stored")),
            },
            metadata={
                "agent_id": "knowledge_graph",
                "neo4j": neo4j_meta,
            },
        )

    def _build_graph(
        self,
        knowledge_graph: KnowledgeGraph | None,
        state: WorkerState,
        agent_cfg: dict[str, Any],
    ) -> dict[str, Any]:
        source = knowledge_graph or KnowledgeGraph(topic=state.learning_need, summary="")
        max_nodes = int(agent_cfg.get("max_nodes") or config.NEO4J_MAX_NODES)
        include_orphans = bool(agent_cfg.get("include_orphan_points", config.NEO4J_INCLUDE_ORPHAN_POINTS))

        points = list(source.points)
        if not points:
            points = [
                KnowledgePoint(
                    id="kp_root",
                    name=source.topic or state.learning_need or "学习主题",
                    description=source.summary or state.learning_need,
                    importance="core",
                )
            ]

        selected_points = points[:max_nodes]
        selected_ids = {point.id for point in selected_points}

        connected_ids = {
            relation.source
            for relation in source.relations
            if relation.source in selected_ids and relation.target in selected_ids
        } | {
            relation.target
            for relation in source.relations
            if relation.source in selected_ids and relation.target in selected_ids
        }

        nodes = [
            self._to_node(point)
            for point in selected_points
            if include_orphans or point.id in connected_ids or point.importance == "core"
        ]
        node_ids = {node["id"] for node in nodes}
        edges = [
            {
                "source": relation.source,
                "target": relation.target,
                "relation_type": relation.relation_type,
                "label": RELATION_LABELS.get(relation.relation_type, "相关"),
            }
            for relation in source.relations
            if relation.source in node_ids and relation.target in node_ids
        ]

        return normalize_render_graph(
            {
                "topic": source.topic or state.learning_need,
                "summary": source.summary,
                "highlight_mode": agent_cfg.get("highlight_mode") or "key_points",
                "focus_areas": list(source.focus_areas),
                "nodes": nodes,
                "edges": edges,
            },
            layout_mode=str(agent_cfg.get("layout_mode") or "force"),
            relation_depth=int(agent_cfg.get("relation_depth") or config.NEO4J_RELATION_DEPTH),
        )

    @staticmethod
    def _to_node(point: KnowledgePoint) -> dict[str, Any]:
        return {
            "id": point.id,
            "label": point.name,
            "description": point.description,
            "category": "weak" if point.is_weak else point.importance,
            "difficulty": point.difficulty,
            "importance": point.importance,
            "is_weak": point.is_weak,
            "prerequisites": list(point.prerequisites),
        }

    async def _store_graph(self, *, state: WorkerState, graph: dict[str, Any], enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"stored": False, "reason": "disabled_by_frontend_config"}
        user_id = self._resolve_user_id(state.profile)
        try:
            return await get_graph_store().upsert_graph(
                user_id=user_id,
                resource_id=state.resource_id,
                agent_id="knowledge_graph",
                graph=graph,
            )
        except Exception as exc:
            logger.exception("[KnowledgeGraphAgent] Neo4j 存储失败")
            return {"stored": False, "error": str(exc)}

    @staticmethod
    def _resolve_user_id(profile: dict[str, Any]) -> int:
        user_data = profile.get("user_data") if isinstance(profile, dict) else None
        if isinstance(user_data, dict):
            value = user_data.get("user_id") or user_data.get("id")
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0
        return 0
