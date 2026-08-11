from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from professional_app.agents.explanation_agent import explanation_agent
from professional_app.agents.numerology_agent import numerology_agent
from professional_app.agents.recommendation_agent import recommendation_agent
from professional_app.agents.scoring_agent import scoring_agent
from professional_app.agents.validation_agent import validation_agent
from professional_app.agents.vastu_agent import vastu_agent
from professional_app.state import PropertyState


def build_graph():
    workflow = StateGraph(PropertyState)

    workflow.add_node("validate", validation_agent)
    workflow.add_node("vastu", vastu_agent)
    workflow.add_node("numerology", numerology_agent)
    workflow.add_node("score", scoring_agent)
    workflow.add_node("recommend", recommendation_agent)
    workflow.add_node("explain", explanation_agent)

    workflow.add_edge(START, "validate")
    workflow.add_edge("validate", "vastu")
    workflow.add_edge("vastu", "numerology")
    workflow.add_edge("numerology", "score")
    workflow.add_edge("score", "recommend")
    workflow.add_edge("recommend", "explain")
    workflow.add_edge("explain", END)

    return workflow.compile()


PROPERTY_GRAPH = build_graph()


def analyze_property(payload: dict) -> PropertyState:
    return PROPERTY_GRAPH.invoke(payload)
