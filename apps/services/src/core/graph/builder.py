from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from src.core.checkpoint import get_postgres_checkpointer
from src.core.graph.nodes.intent_parser import intent_parser_node
from src.core.graph.nodes.rag_index import rag_index_node
from src.core.graph.nodes.report_builder import report_builder_node
from src.core.graph.nodes.research_fanout import research_fanout_node
from src.core.graph.nodes.strategy_engine import strategy_engine_node
from src.core.graph.nodes.task_planner import task_planner_node
from src.core.schemas import GraphState

logger = logging.getLogger(__name__)


def build_graph():
    """Assembles the linear pipeline as an explicit LangGraph state machine.

    Checkpointing is opt-in through ENABLE_POSTGRES_CHECKPOINTS because local
    development and CI should not require a running Postgres/libpq stack.
    """
    logger.info("Building research graph")
    graph = StateGraph(GraphState)

    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("task_planner", task_planner_node)
    graph.add_node("research_fanout", research_fanout_node)
    graph.add_node("rag_index", rag_index_node)
    graph.add_node("strategy_engine", strategy_engine_node)
    graph.add_node("report_builder", report_builder_node)

    graph.set_entry_point("intent_parser")
    graph.add_edge("intent_parser", "task_planner")
    graph.add_edge("task_planner", "research_fanout")
    graph.add_edge("research_fanout", "rag_index")
    graph.add_edge("rag_index", "strategy_engine")
    graph.add_edge("strategy_engine", "report_builder")
    graph.add_edge("report_builder", END)

    checkpointer = get_postgres_checkpointer()
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
