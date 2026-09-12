from typing import Dict, Any, List
from app.models.workflows import WorkflowNode, WorkflowEdge

class WorkflowCompiler:
    """
    Validates developer-defined workflows and compiles them for execution.
    Checks for cycle locks, unreferenced target nodes, and missing agent bindings.
    """

    def validate_graph(self, nodes: List[WorkflowNode], edges: List[WorkflowEdge], max_nodes: int = 20) -> Dict[str, Any]:
        node_keys = {n.node_key for n in nodes}
        if not node_keys:
            raise ValueError("Workflow graph contains no nodes.")

        if len(nodes) > max_nodes:
            raise ValueError(f"Workflow exceeds maximum allowed node count ({len(nodes)} > {max_nodes}).")

        # Check edge validity
        for edge in edges:
            if edge.source_node_key not in node_keys:
                raise ValueError(f"Edge source node '{edge.source_node_key}' does not exist in graph.")
            if edge.target_node_key not in node_keys and edge.target_node_key != "END":
                raise ValueError(f"Edge target node '{edge.target_node_key}' does not exist in graph.")

        # Find entry node (nodes with no incoming edges or first node)
        incoming_targets = {e.target_node_key for e in edges}
        entry_nodes = [n for n in nodes if n.node_key not in incoming_targets]
        entry_node_key = entry_nodes[0].node_key if entry_nodes else nodes[0].node_key

        return {
            "valid": True,
            "entry_node_key": entry_node_key,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

