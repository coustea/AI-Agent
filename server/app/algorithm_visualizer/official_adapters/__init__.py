"""Per-visualizer-type observation adapters for official template tracing.

Each adapter observes ``sys.settrace`` line/return events from a single
trusted template source file and emits semantic state snapshots through a
TraceBuilder.  Adapters use known local variable names for each registered
template family and never connect nodes by array position when the source
object has no explicit relation.
"""

from app.algorithm_visualizer.official_adapters._base import BaseAdapter
from app.algorithm_visualizer.official_adapters.arrays import (
    ArrayAdapter,
    StackQueueAdapter,
)
from app.algorithm_visualizer.official_adapters.structures import (
    LinkedListAdapter,
    TreeAdapter,
)
from app.algorithm_visualizer.official_adapters.graphs import GraphAdapter
from app.algorithm_visualizer.official_adapters.tables import DpTableAdapter

__all__ = (
    "ArrayAdapter",
    "BaseAdapter",
    "DpTableAdapter",
    "GraphAdapter",
    "LinkedListAdapter",
    "StackQueueAdapter",
    "TreeAdapter",
    "get_adapter",
)


def get_adapter(visualizer_type: str, input_data: dict[str, object]) -> BaseAdapter:
    """Return the correct adapter for a visualizer type and its validated input."""
    if visualizer_type == "array":
        return ArrayAdapter(input_data)
    if visualizer_type == "stack-queue":
        return StackQueueAdapter(input_data)
    if visualizer_type == "linked-list":
        return LinkedListAdapter(input_data)
    if visualizer_type == "tree":
        return TreeAdapter(input_data)
    if visualizer_type == "graph":
        return GraphAdapter(input_data)
    if visualizer_type == "dp-table":
        return DpTableAdapter(input_data)
    raise ValueError(f"不支持的 visualizerType: {visualizer_type}")
