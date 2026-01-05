"""
LangGraph Workflow Definition - DIGOT AI Recruitment Orchestrator

Implements a Supervisor Architecture where a central Supervisor node
routes execution to specialized agents (Evaluate, Draft, Send).

The graph uses conditional edges based on the 'next_destination' state variable,
allowing for dynamic, state-aware workflow orchestration.
"""

from langgraph.graph import StateGraph, END
from agent.state import WorkflowState
from agent.nodes import (
    analyze_query_node,
    generate_candidates_node,
    evaluate_candidates_node, 
    generate_outreach_node, 
    deliver_outreach_node,
    supervisor_node
)

def initialize_recruitment_workflow():
    """
    Compiles the directed acyclic graph (DAG) using a Supervisor Architecture.
    The Supervisor decides which agent should act next.
    """
    # Initialize the state graph
    workflow_builder = StateGraph(WorkflowState)
    
    # 1. Register All Nodes
    workflow_builder.add_node("supervisor", supervisor_node)
    workflow_builder.add_node("analyze_query", analyze_query_node)
    workflow_builder.add_node("generate_candidates", generate_candidates_node)
    workflow_builder.add_node("evaluate_candidates", evaluate_candidates_node)
    workflow_builder.add_node("generate_outreach", generate_outreach_node)
    workflow_builder.add_node("send_outreach", deliver_outreach_node)
    
    # 2. Define Entry Point
    workflow_builder.set_entry_point("supervisor")
    
    # 3. Define Supervisor Routing (Conditional Edges)
    workflow_builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next_destination"],
        {
            "analyze_query": "analyze_query",
            "generate_candidates": "generate_candidates",
            "evaluate_candidates": "evaluate_candidates",
            "generate_outreach": "generate_outreach",
            "send_outreach": "send_outreach",
            "FINISH": END
        }
    )
    
    # 4. Define Agent Loops (Back to Supervisor)
    workflow_builder.add_edge("analyze_query", "supervisor")
    workflow_builder.add_edge("generate_candidates", "supervisor")
    workflow_builder.add_edge("evaluate_candidates", "supervisor")
    workflow_builder.add_edge("generate_outreach", "supervisor")
    workflow_builder.add_edge("send_outreach", "supervisor")
    
    # 5. Compile the graph
    return workflow_builder.compile()
