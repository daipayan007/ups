# type: ignore
from typing import TypedDict, Sequence
import asyncio
from dotenv import load_dotenv
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage
)
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from llm import get_llm
from db_config import get_pool

load_dotenv()

AGENT_APP = None

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]


def clean_messages(messages):
    return [m for m in messages if m.type != "tool"]


@tool
async def fetchTables() -> dict:
    """Return all table names from employees schema."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'employees'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """
        )
    return {"table_names": [r["table_name"] for r in rows]}

@tool
async def fetchTableSchema(table_names: list[str]) -> dict:
    """Return schema for given tables."""
    if not table_names:
        return {}

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'employees'
              AND table_name = ANY($1)
            ORDER BY table_name, ordinal_position;
            """,
            table_names,
        )

    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row["table_name"], []).append(
            f"{row['column_name']} {row['data_type']}"
        )

    return {k: ", ".join(v) for k, v in result.items()}

async def table_selector_agent(state: AgentState) -> AgentState:
    """
    ReAct agent:
    - Calls fetchTables
    - Selects relevant tables
    """
    model = get_llm(tools=[fetchTables])

    system = SystemMessage(
        content="""
You are a ReAct-style Table Selector.

Steps:
1. Call fetchTables only once.
2. Choose ONLY tables needed to answer the user query.
3. Do NOT invent table names.
4. Clearly state the selected tables.
"""
    )

    response = await model.ainvoke(
        [system, *clean_messages(state["messages"])]
    )

    print("TableSelector", response)
    return {"messages": add_messages(state["messages"], response)}

async def schema_agent(state: AgentState) -> AgentState:
    """
    ReAct agent:
    - Reads selected tables from prior messages
    - Calls fetchTableSchema
    """
    model = get_llm(tools=[fetchTableSchema])

    system = SystemMessage(
        content="""
You are a ReAct-style Schema Agent.

Rules:
- Identify the table names selected earlier.
- Call fetchTableSchema exactly once.
- Do NOT invent or modify table names.
- Return the schema as-is.
"""
    )

    response = await model.ainvoke(
        [system, *clean_messages(state["messages"])]
    )
    print("SchemaAgent", response)
    return {"messages": add_messages(state["messages"], response)}

def get_agent_app():
    global AGENT_APP

    if AGENT_APP is None:
        graph = StateGraph(AgentState)
        graph.add_node("TableSelector", table_selector_agent)
        graph.add_node("SchemaAgent", schema_agent)
        graph.add_node("TableSelectorTools", ToolNode([fetchTables]))
        graph.add_node("SchemaTools", ToolNode([fetchTableSchema]))
        graph.add_edge(START, "TableSelector")
        graph.add_conditional_edges(
            "TableSelector",
            tools_condition,
            {
                "tools": "TableSelectorTools",
                "__end__": "SchemaAgent",
            },
        )
        graph.add_edge("TableSelectorTools", "TableSelector")
        graph.add_conditional_edges(
            "SchemaAgent",
            tools_condition,
            {
                "tools": "SchemaTools",
                "__end__": END,
            },
        )
        graph.add_edge("SchemaTools", "SchemaAgent")
        AGENT_APP = graph.compile()
    return AGENT_APP

async def main():
    app = get_agent_app()

    result = await app.ainvoke({
        "messages": [
            HumanMessage(content="Find me details of all employees")
        ]
    })

    for msg in result["messages"]:
        print(type(msg).__name__)
        print(msg.content)
        print("-" * 40)

asyncio.run(main())