# # type: ignore
# from typing import TypedDict, Sequence, Annotated
# import json
# from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
# from langchain_core.tools import tool
# from langgraph.graph import START, StateGraph, END
# from langgraph.prebuilt import ToolNode, tools_condition
# from langgraph.graph.message import add_messages
# from llm import get_llm
# from db_config import get_pool
# from state import AgentState
# import asyncio


# async def fetch_tables() -> dict:
#     """Return all table names from employees schema."""
#     pool = await get_pool()
#     async with pool.acquire() as conn:
#         rows = await conn.fetch(
#             """
#              SELECT
#     t.name AS table_name
# FROM sys.tables t
# JOIN sys.schemas s
#     ON t.schema_id = s.schema_id
# WHERE s.name = 'dbo'
#   AND t.is_ms_shipped = 0
# ORDER BY t.name;
#             """
#         )
#     return {"table_names": [r["table_name"] for r in rows]}

# # async def fetch_table_schema(table_names: list[str]) -> dict:
# #     """Return columns, primary keys, and foreign keys for given tables."""
# #     if not table_names:
# #         return {}

# #     pool = await get_pool()
# #     async with pool.acquire() as conn:

# #         # Columns
# #         columns = await conn.fetch(
# #             f"""
# #             SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'employees' AND table_name = ANY($1) ORDER BY table_name, ordinal_position;
# #             """,
# #             table_names,
# #         )

# #         # Primary Keys
# #         pks = await conn.fetch(
# #             """
# #             SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc
# #             JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
# #             WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'employees'
# #               AND tc.table_name = ANY($1);
# #             """,
# #             table_names,
# #         )

# #         # Foreign Keys
# #         fks = await conn.fetch(
# #             """
# #             SELECT
# #                 tc.table_name, kcu.column_name,
# #                 ccu.table_name AS foreign_table,
# #                 ccu.column_name AS foreign_column
# #             FROM information_schema.table_constraints tc
# #             JOIN information_schema.key_column_usage kcu
# #               ON tc.constraint_name = kcu.constraint_name
# #             JOIN information_schema.constraint_column_usage ccu
# #               ON ccu.constraint_name = tc.constraint_name
# #             WHERE tc.constraint_type = 'FOREIGN KEY'
# #               AND tc.table_schema = 'employees'
# #               AND tc.table_name = ANY($1);
# #             """,
# #             table_names,
# #         )

# #     schema: dict = {}

# #     for row in columns:
# #         schema.setdefault(row["table_name"], {}).setdefault(
# #             "columns", {}
# #         )[row["column_name"]] = row["data_type"]

# #     for row in pks:
# #         schema.setdefault(row["table_name"], {}).setdefault(
# #             "primary_keys", []
# #         ).append(row["column_name"])

# #     for row in fks:
# #         schema.setdefault(row["table_name"], {}).setdefault(
# #             "foreign_keys", []
# #         ).append({
# #             "column": row["column_name"],
# #             "references": f"{row['foreign_table']}.{row['foreign_column']}"
# #         })

# #     return schema
# def _sql_in_list(values: list[str]) -> str:
#     return ", ".join(f"'{v}'" for v in values)
 
# async def fetch_table_schema(table_names: list[str]) -> dict:
#     """Return columns, primary keys, and foreign keys for given tables (Azure SQL)."""
#     if not table_names:
#         return {}
 
#     table_list = _sql_in_list(table_names)
 
#     pool = await get_pool()
#     async with pool.acquire() as conn:
 
#         # Columns
#         columns = await conn.fetch(f"""
#             SELECT
#                 t.name  AS table_name,
#                 c.name  AS column_name,
#                 ty.name AS data_type
#             FROM sys.tables t
#             JOIN sys.schemas s ON t.schema_id = s.schema_id
#             JOIN sys.columns c ON t.object_id = c.object_id
#             JOIN sys.types ty ON c.user_type_id = ty.user_type_id
#             WHERE s.name = 'dbo'
#               AND t.name IN ({table_list})
#             ORDER BY t.name, c.column_id;
#         """)
 
#         # Primary Keys
#         pks = await conn.fetch(f"""
#             SELECT
#                 t.name AS table_name,
#                 c.name AS column_name
#             FROM sys.tables t
#             JOIN sys.schemas s ON t.schema_id = s.schema_id
#             JOIN sys.indexes i
#                 ON i.object_id = t.object_id AND i.is_primary_key = 1
#             JOIN sys.index_columns ic
#                 ON ic.object_id = t.object_id AND ic.index_id = i.index_id
#             JOIN sys.columns c
#                 ON c.object_id = t.object_id AND c.column_id = ic.column_id
#             WHERE s.name = 'dbo'
#               AND t.name IN ({table_list})
#             ORDER BY t.name, ic.key_ordinal;
#         """)
 
#         # Foreign Keys
#         fks = await conn.fetch(f"""
#             SELECT
#                 pt.name AS table_name,
#                 pc.name AS column_name,
#                 rt.name AS foreign_table,
#                 rc.name AS foreign_column
#             FROM sys.foreign_keys fk
#             JOIN sys.foreign_key_columns fkc
#                 ON fk.object_id = fkc.constraint_object_id
#             JOIN sys.tables pt
#                 ON pt.object_id = fk.parent_object_id
#             JOIN sys.schemas ps
#                 ON ps.schema_id = pt.schema_id
#             JOIN sys.columns pc
#                 ON pc.object_id = pt.object_id
#                AND pc.column_id = fkc.parent_column_id
#             JOIN sys.tables rt
#                 ON rt.object_id = fk.referenced_object_id
#             JOIN sys.columns rc
#                 ON rc.object_id = rt.object_id
#                AND rc.column_id = fkc.referenced_column_id
#             WHERE ps.name = 'dbo'
#               AND pt.name IN ({table_list})
#             ORDER BY pt.name, fkc.constraint_column_id;
#         """)
 
#     schema: dict = {}
 
#     for row in columns:
#         schema.setdefault(row["table_name"], {}).setdefault(
#             "columns", {}
#         )[row["column_name"]] = row["data_type"]
 
#     for row in pks:
#         schema.setdefault(row["table_name"], {}).setdefault(
#             "primary_keys", []
#         ).append(row["column_name"])
 
#     for row in fks:
#         schema.setdefault(row["table_name"], {}).setdefault(
#             "foreign_keys", []
#         ).append({
#             "column": row["column_name"],
#             "references": f"{row['foreign_table']}.{row['foreign_column']}"
#         })
 
#     return schema

# async def table_agent(state: AgentState) -> AgentState:
#     model = get_llm()

#     fullTableList = await fetch_tables()
#     table_names = set(fullTableList["table_names"])

#     table_list_str = "\n".join(f"- {t}" for t in table_names)

#     system_message = SystemMessage(content=f"""
#         You are a Table Selection Agent.

#         Available tables:
#         {table_list_str}

#         Rules:
#         - Select only tables that are strictly necessary
#         - Select tables only from the list above
#         - Do NOT invent table names
#         - Do NOT include explanations

#         Final output MUST be valid JSON:
#         {{ "tables": ["table1", "table2"] }}
#         """)

#     user_message = state["messages"][0]

#     response = await model.ainvoke([system_message, user_message])

#     try:
#         tables = json.loads(response.content)["tables"]
#     except Exception as e:
#         raise ValueError(
#             f"Table agent failed to parse JSON.\nLLM output:\n{response.content}"
#         ) from e

#     if not tables:
#         raise ValueError("Table agent returned no tables.")
#     invalid = [t for t in tables if t not in table_names]
#     if invalid:
#         raise ValueError(f"Invalid tables selected: {invalid}")
#     tables = [t for t in tables if t in table_names]
#     schemas = await fetch_table_schema(tables)

#     return {
#         "tables": tables,
#         "schemas": schemas
#     }



# type: ignore
from typing import TypedDict, Sequence, Annotated
import json
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from llm import get_llm
from db_config import get_pool  # we continue to use your pooled aioodbc connection
from state import AgentState
import asyncio


# ---------- Small helper: run a query and return list[dict] ----------
async def _query_dicts(sql: str, params: Sequence = ()) -> list[dict]:
    """
    Execute a SELECT and return rows as list of dicts (col->value).
    Uses aioodbc's cursor API (pyodbc underneath).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in rows]


async def fetch_tables() -> dict:
    """Return all user table names from dbo schema (SQL Server/Azure SQL)."""
    rows = await _query_dicts(
        """
        SELECT t.name AS table_name
        FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE s.name = 'dbo'
          AND t.is_ms_shipped = 0
        ORDER BY t.name;
        """
    )
    return {"table_names": [r["table_name"] for r in rows]}


def _placeholders(n: int) -> str:
    # e.g., n=3 -> "?, ?, ?"
    return ", ".join("?" for _ in range(n))


async def fetch_table_schema(table_names: list[str]) -> dict:
    """Return columns, primary keys, and foreign keys for given tables (Azure SQL)."""
    if not table_names:
        return {}

    ph = _placeholders(len(table_names))
    params = tuple(table_names)

    # Columns
    columns = await _query_dicts(
        f"""
        SELECT
            t.name  AS table_name,
            c.name  AS column_name,
            ty.name AS data_type
        FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        JOIN sys.columns c ON t.object_id = c.object_id
        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        WHERE s.name = 'dbo'
          AND t.name IN ({ph})
        ORDER BY t.name, c.column_id;
        """,
        params,
    )

    # Primary Keys
    pks = await _query_dicts(
        f"""
        SELECT
            t.name AS table_name,
            c.name AS column_name
        FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        JOIN sys.indexes i
            ON i.object_id = t.object_id AND i.is_primary_key = 1
        JOIN sys.index_columns ic
            ON ic.object_id = t.object_id AND ic.index_id = i.index_id
        JOIN sys.columns c
            ON c.object_id = t.object_id AND c.column_id = ic.column_id
        WHERE s.name = 'dbo'
          AND t.name IN ({ph})
        ORDER BY t.name, ic.key_ordinal;
        """,
        params,
    )

    # Foreign Keys
    fks = await _query_dicts(
        f"""
        SELECT
            pt.name AS table_name,
            pc.name AS column_name,
            rt.name AS foreign_table,
            rc.name AS foreign_column
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc
            ON fk.object_id = fkc.constraint_object_id
        JOIN sys.tables pt
            ON pt.object_id = fk.parent_object_id
        JOIN sys.schemas ps
            ON ps.schema_id = pt.schema_id
        JOIN sys.columns pc
            ON pc.object_id = pt.object_id
           AND pc.column_id = fkc.parent_column_id
        JOIN sys.tables rt
            ON rt.object_id = fk.referenced_object_id
        JOIN sys.columns rc
            ON rc.object_id = rt.object_id
           AND rc.column_id = fkc.referenced_column_id
        WHERE ps.name = 'dbo'
          AND pt.name IN ({ph})
        ORDER BY pt.name, fkc.constraint_column_id;
        """,
        params,
    )

    schema: dict = {}

    for row in columns:
        schema.setdefault(row["table_name"], {}).setdefault("columns", {})[
            row["column_name"]
        ] = row["data_type"]

    for row in pks:
        schema.setdefault(row["table_name"], {}).setdefault("primary_keys", []).append(
            row["column_name"]
        )

    for row in fks:
        schema.setdefault(row["table_name"], {}).setdefault("foreign_keys", []).append(
            {
                "column": row["column_name"],
                "references": f"{row['foreign_table']}.{row['foreign_column']}",
            }
        )

    return schema


async def table_agent(state: AgentState) -> AgentState:
    model = get_llm()

    fullTableList = await fetch_tables()
    table_names = set(fullTableList["table_names"])

    table_list_str = "\n".join(f"- {t}" for t in table_names)

    system_message = SystemMessage(
        content=f"""
        You are a Table Selection Agent.

        Available tables:
        {table_list_str}

        Rules:
        - Select only tables that are strictly necessary
        - Select tables only from the list above
        - Do NOT invent table names
        - Do NOT include explanations

        Final output MUST be valid JSON:
        {{ "tables": ["table1", "table2"] }}
        """
    )

    user_message = state["messages"][0]
    response = await model.ainvoke([system_message, user_message])

    try:
        tables = json.loads(response.content)["tables"]
    except Exception as e:
        raise ValueError(
            f"Table agent failed to parse JSON.\nLLM output:\n{response.content}"
        ) from e

    if not tables:
        raise ValueError("Table agent returned no tables.")

    invalid = [t for t in tables if t not in table_names]
    if invalid:
        raise ValueError(f"Invalid tables selected: {invalid}")

    tables = [t for t in tables if t in table_names]
    schemas = await fetch_table_schema(tables)

    return {
        "tables": tables,
        "schemas": schemas,
    }
