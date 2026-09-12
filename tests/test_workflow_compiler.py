import pytest
from app.models.workflows import WorkflowNode, WorkflowEdge
from app.runtime.workflow_compiler import WorkflowCompiler

def test_validate_graph_empty_nodes():
    compiler = WorkflowCompiler()
    with pytest.raises(ValueError, match="Workflow graph contains no nodes."):
        compiler.validate_graph([], [])

def test_validate_graph_invalid_source_edge():
    compiler = WorkflowCompiler()
    nodes = [WorkflowNode(node_key="node1", node_type="agent")]
    edges = [WorkflowEdge(source_node_key="non_existent", target_node_key="node1")]
    with pytest.raises(ValueError, match="Edge source node 'non_existent' does not exist in graph."):
        compiler.validate_graph(nodes, edges)

def test_validate_graph_invalid_target_edge():
    compiler = WorkflowCompiler()
    nodes = [WorkflowNode(node_key="node1", node_type="agent")]
    edges = [WorkflowEdge(source_node_key="node1", target_node_key="non_existent")]
    with pytest.raises(ValueError, match="Edge target node 'non_existent' does not exist in graph."):
        compiler.validate_graph(nodes, edges)

def test_validate_graph_success():
    compiler = WorkflowCompiler()
    nodes = [
        WorkflowNode(node_key="start", node_type="agent"),
        WorkflowNode(node_key="review", node_type="agent")
    ]
    edges = [
        WorkflowEdge(source_node_key="start", target_node_key="review"),
        WorkflowEdge(source_node_key="review", target_node_key="END")
    ]
    res = compiler.validate_graph(nodes, edges)
    assert res["valid"] is True
    assert res["entry_node_key"] == "start"
    assert res["node_count"] == 2
    assert res["edge_count"] == 2
