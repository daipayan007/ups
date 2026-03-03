# type: ignore
from typing import TypedDict, Sequence, Annotated, List
import json
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from llm import get_llm
from db_config import get_pool, close_pool
import asyncio

async def fetch_table_schema(table_names: list[str]) -> dict:
    """Return columns, primary keys, and foreign keys for given tables."""
    if not table_names:
        return {}

    pool = await get_pool()
    async with pool.acquire() as conn:

        # Columns
        columns = await conn.fetch(
            """
            SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'employees' AND table_name = ANY($1) ORDER BY table_name, ordinal_position;
            """,
            table_names,
        )

        # Primary Keys
        pks = await conn.fetch(
            """
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'employees'
              AND tc.table_name = ANY($1);
            """,
            table_names,
        )

        # Foreign Keys
        fks = await conn.fetch(
            """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'employees'
              AND tc.table_name = ANY($1);
            """,
            table_names,
        )

    schema: dict = {}

    for row in columns:
        schema.setdefault(row["table_name"], {}).setdefault(
            "columns", {}
        )[row["column_name"]] = row["data_type"]

    for row in pks:
        schema.setdefault(row["table_name"], {}).setdefault(
            "primary_keys", []
        ).append(row["column_name"])

    for row in fks:
        schema.setdefault(row["table_name"], {}).setdefault(
            "foreign_keys", []
        ).append({
            "column": row["column_name"],
            "references": f"{row['foreign_table']}.{row['foreign_column']}"
        })

    return schema


async def schema_agent(state: AgentState) -> AgentState:
    model = get_llm(tools=[fetch_table_schema])
    schemaDetails = await fetch_table_schema(state["tables"])
    system_message = SystemMessage(content=f"""
    You are a Schema Extraction Agent.

    

    Your responsibilities:
    2. Do NOT invent columns or relationships
    3. Do NOT explain anything

    Return ONLY valid JSON in this exact format:
    {{
    "schemas": {{
        "table_name": {{
        "columns": {{ "column": "type" }},
        "primary_keys": ["column"],
        "foreign_keys": [
            {{ "column": "column", "references": "other_table.other_column" }}
        ]
        }}
    }}
    }}
    """)

    response = await model.ainvoke([
        system_message,
        *state["messages"]
    ])

    schemas = None
    try:
        schemas = json.loads(response.content)["schemas"]
    except Exception:
        schemas = None

    return {
        "messages": add_messages(state["messages"], response),
        "schemas": schemas
    }

def generate_schema_agent():
    global SCHEMA_AGENT_APP

    if SCHEMA_AGENT_APP is None:
        graph = StateGraph(AgentState)

        graph.add_node("SchemaAgent", schema_agent)
        graph.add_node("Tools", ToolNode([fetch_table_schema]))

        graph.add_edge(START, "SchemaAgent")

        graph.add_conditional_edges(
            "SchemaAgent",
            tools_condition,
            {
                "tools": "Tools",
                END: END
            }
        )

        graph.add_edge("Tools", "SchemaAgent")

        SCHEMA_AGENT_APP = graph.compile()

    return SCHEMA_AGENT_APP

async def run_schema_agent(tablesList: List[str]) -> dict | None:
    app = generate_schema_agent()

    result = await app.ainvoke({
        "messages": [
            SystemMessage(content="Extract schema for the provided tables.")
        ],
        "tables": tablesList,
        "schemas": None
    })

    return result["schemas"]

# async def main():
#     response = await run_schema_agent(['employee', 'department_employee', 'department', 'department_manager'])
#     print(response)

# asyncio.run(main())

# SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'employees' AND table_name = ANY(ARRAY['employees', 'departments']) ORDER BY table_name, ordinal_position;