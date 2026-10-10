"""The routing workflow with one bounded review cycle: a small LangGraph graph.

    START -> router -> general_chat -> reviewer -> END
                   \\-> study_helper -> reviewer -> END
                                          |
                                          +-> improver -> reviewer   (at most once)

A node is a focused piece of work, not automatically an agent. The router is
ordinary Python. The answer nodes, reviewer and improver are small
LLM-powered specialist nodes. There are no tools and no MCP calls.
"""

from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from learning_companion.chain import (
    build_chain,
    build_improver_chain,
    build_reviewer_chain,
    build_study_helper_chain,
)
from learning_companion.config import get_settings
from learning_companion.routing import GENERAL, STUDY, choose_route

STUDY_NEEDS_QUESTION = (
    "What would you like to study? Try `/study Explain what an API is`."
)

MAX_REVISIONS = 1  # the improver may run at most this many times


class GraphState(TypedDict):
    """The shared notebook every node can read and add to."""

    user_message: str  # what the participant just asked
    messages: list[BaseMessage]  # earlier chat messages from this request
    route: str  # "general" or "study" (empty until the router has run)
    draft_answer: str  # the answer as currently written (improver replaces it)
    review_decision: str  # "approve" or "improve" (empty until reviewed)
    review_reason: str  # one short sentence explaining the decision
    revision_count: int  # rewrites so far: starts at 0, never above 1
    final_answer: str  # the reply to send (written only when finishing)


def router(state: GraphState) -> dict:
    """Ordinary Python, no model: keeps the `/study` rule from Story 3.2."""
    route, question = choose_route(state["user_message"])
    return {"route": route, "user_message": question}


def general_chat(state: GraphState) -> dict:
    chain = build_chain(get_settings())
    inputs = {"history": state["messages"], "question": state["user_message"]}
    return {"draft_answer": chain.invoke(inputs)}


def study_helper(state: GraphState) -> dict:
    if not state["user_message"]:  # bare "/study": fixed reply, no model, no review
        return {
            "draft_answer": STUDY_NEEDS_QUESTION,
            "final_answer": STUDY_NEEDS_QUESTION,
        }
    chain = build_study_helper_chain(get_settings())
    inputs = {"history": state["messages"], "question": state["user_message"]}
    return {"draft_answer": chain.invoke(inputs)}


def reviewer(state: GraphState) -> dict:
    """Approve the draft or ask for one improvement."""
    if state["revision_count"] >= MAX_REVISIONS:  # limit reached: no more model calls
        return {
            "review_decision": "approve",
            "review_reason": "revision limit reached; accepting the current draft",
            "final_answer": state["draft_answer"],
        }
    result = build_reviewer_chain(get_settings()).invoke(
        {
            "route": state["route"],
            "question": state["user_message"],
            "draft": state["draft_answer"],
        }
    )
    update = {"review_decision": result.decision, "review_reason": result.reason}
    if result.decision == "approve":
        update["final_answer"] = state["draft_answer"]
    return update


def improver(state: GraphState) -> dict:
    """Rewrite the draft once. No tools, no planning, no routing choice."""
    rewritten = build_improver_chain(get_settings()).invoke(
        {
            "route": state["route"],
            "question": state["user_message"],
            "draft": state["draft_answer"],
            "reason": state["review_reason"],
        }
    )
    return {
        "draft_answer": rewritten,
        "revision_count": state["revision_count"] + 1,
    }


def pick_route(state: GraphState) -> str:
    return state["route"]


def after_study_helper(state: GraphState) -> str:
    return "done" if state["final_answer"] else "review"


def after_review(state: GraphState) -> str:
    """Approved drafts end. Improvement is allowed only while revision_count is 0."""
    if state["review_decision"] == "improve" and state["revision_count"] == 0:
        return "improve"
    return "done"


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("router", router)
    builder.add_node("general_chat", general_chat)
    builder.add_node("study_helper", study_helper)
    builder.add_node("reviewer", reviewer)
    builder.add_node("improver", improver)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", pick_route, {GENERAL: "general_chat", STUDY: "study_helper"}
    )
    builder.add_edge("general_chat", "reviewer")
    builder.add_conditional_edges(
        "study_helper", after_study_helper, {"review": "reviewer", "done": END}
    )
    builder.add_conditional_edges(
        "reviewer", after_review, {"improve": "improver", "done": END}
    )
    builder.add_edge("improver", "reviewer")  # the one visible cycle
    return builder.compile()


GRAPH = build_graph()


def run_graph(
    messages: list[BaseMessage], user_message: str
) -> tuple[GraphState, list[str]]:
    """Run the graph once. Returns the final state and the node sequence."""
    state: GraphState = {
        "user_message": user_message,
        "messages": messages,
        "route": "",
        "draft_answer": "",
        "review_decision": "",
        "review_reason": "",
        "revision_count": 0,
        "final_answer": "",
    }
    nodes: list[str] = []
    for update in GRAPH.stream(state, stream_mode="updates"):
        for node, changes in update.items():
            nodes.append(node)
            state.update(changes)
    return state, nodes
