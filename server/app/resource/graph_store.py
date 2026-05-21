"""Neo4j-backed knowledge graph persistence."""

from __future__ import annotations

from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app import config


RELATION_TYPE_MAP: dict[str, str] = {
    "prerequisite": "PREREQUISITE_OF",
    "extends": "EXTENDS",
    "includes": "INCLUDES",
    "related": "RELATED_TO",
}


VALID_RELATION_TYPES = frozenset(RELATION_TYPE_MAP.values())

# 模块级单例，避免每次调用创建新实例（driver 懒加载复用）
_graph_store: Neo4jGraphStore | None = None


def get_graph_store() -> Neo4jGraphStore:
    """获取 Neo4jGraphStore 单例。"""
    global _graph_store
    if _graph_store is None:
        _graph_store = Neo4jGraphStore()
    return _graph_store


class Neo4jGraphStore:
    """Stores normalized learning graphs in Neo4j when configured."""

    def __init__(
        self,
        *,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._uri = uri if uri is not None else config.NEO4J_URI
        self._user = user if user is not None else config.NEO4J_USER
        self._password = password if password is not None else config.NEO4J_PASSWORD
        self.database = database if database is not None else config.NEO4J_DATABASE
        self.enabled = bool(config.NEO4J_ENABLED if enabled is None else enabled)
        self._driver: AsyncDriver | None = None

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
        return self._driver

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def upsert_graph(
        self,
        *,
        user_id: int,
        resource_id: int | str | None,
        agent_id: str,
        graph: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert graph nodes and relationships, returning storage metadata."""
        if not self.enabled or not self._uri or not self._user or not self._password:
            return {"stored": False, "reason": "neo4j_not_configured"}

        graph_id = f"{agent_id}-{user_id}-{resource_id or 'chat'}"
        async with self.driver.session(database=self.database) as session:
            await session.execute_write(self._upsert_nodes, graph_id, user_id, resource_id, graph)
            await session.execute_write(self._upsert_edges, graph_id, graph)

        return {
            "stored": True,
            "graph_id": graph_id,
            "node_count": len(graph.get("nodes") or []),
            "edge_count": len(graph.get("edges") or []),
        }

    @staticmethod
    async def _upsert_nodes(tx, graph_id: str, user_id: int, resource_id: int | str | None, graph: dict[str, Any]) -> None:
        await tx.run(
            """
            MERGE (g:LearningGraph {graph_id: $graph_id})
            SET g.topic = $topic,
                g.summary = $summary,
                g.user_id = $user_id,
                g.resource_id = $resource_id,
                g.updated_at = datetime()
            """,
            graph_id=graph_id,
            topic=graph.get("topic") or "",
            summary=graph.get("summary") or "",
            user_id=user_id,
            resource_id=str(resource_id or ""),
        )
        for node in graph.get("nodes") or []:
            await tx.run(
                """
                MATCH (g:LearningGraph {graph_id: $graph_id})
                MERGE (n:KnowledgePoint {graph_id: $graph_id, id: $id})
                SET n.label = $label,
                    n.description = $description,
                    n.category = $category,
                    n.difficulty = $difficulty,
                    n.importance = $importance,
                    n.is_weak = $is_weak,
                    n.level = $level,
                    n.updated_at = datetime()
                MERGE (g)-[:HAS_POINT]->(n)
                """,
                graph_id=graph_id,
                id=node.get("id"),
                label=node.get("label") or node.get("name") or "",
                description=node.get("description") or "",
                category=node.get("category") or "important",
                difficulty=node.get("difficulty") or "",
                importance=node.get("importance") or "",
                is_weak=bool(node.get("is_weak")),
                level=int(node.get("level") or 0),
            )

    @staticmethod
    async def _upsert_edges(tx, graph_id: str, graph: dict[str, Any]) -> None:
        for edge in graph.get("edges") or []:
            relation = RELATION_TYPE_MAP.get(str(edge.get("relation_type") or "related"), "RELATED_TO")
            if relation not in VALID_RELATION_TYPES:
                relation = "RELATED_TO"
            await tx.run(
                f"""
                MATCH (source:KnowledgePoint {{graph_id: $graph_id, id: $source}})
                MATCH (target:KnowledgePoint {{graph_id: $graph_id, id: $target}})
                MERGE (source)-[r:{relation} {{graph_id: $graph_id}}]->(target)
                SET r.label = $label,
                    r.updated_at = datetime()
                """,
                graph_id=graph_id,
                source=edge.get("source"),
                target=edge.get("target"),
                label=edge.get("label") or "",
            )
