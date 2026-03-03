# # type: ignore
# import asyncio
# from langchain_core.messages import HumanMessage, SystemMessage
# from langgraph.graph import START, END, StateGraph
# from langgraph.graph.message import add_messages
# from typing import List, Dict
# from state import AgentState
# from tableAgent import table_agent
# from sqlAgent import sql_agent
# from sqlValidator import validator_agent
# from db_config import close_pool, execute_sql
# import re
# from llm import get_llm
# AGENT_ORCHESTRATOR_APP = None

# def orchestrator_router(state: AgentState):
#     if state.get("validation") and state["validation"].get("valid") is True:
#         return END

#     if state["tables"] is None:
#         return "TABLE_AGENT"

#     if state["sqlQuery"] is None:
#         return "SQL_AGENT"

#     if state["validation"] is None:
#         return "VALIDATOR_AGENT"

#     if state["retry_count"] < state["max_retries"]:
#         return "SQL_AGENT"

#     return END

# def orchestrator_node(state: AgentState) -> AgentState:
#     # Only act when validation failed
#     if state["validation"] and state["validation"].get("valid") is False:
#         return {
#             "retry_count": state["retry_count"] + 1,
#             "validation": None,
#             "messages": add_messages(
#                 state["messages"],
#                 HumanMessage(
#                     content=f"""
# The previous SQL was invalid.

# Validator feedback:
# {state["validation"].get("suggestions", [])}

# Fix the SQL accordingly.
# """
#                 ),
#             ),
#         }
    
#     # print(state)
#     return {}

# def construct_app():
#     global AGENT_ORCHESTRATOR_APP

#     if AGENT_ORCHESTRATOR_APP is None:
#         graph = StateGraph(AgentState)

#         graph.add_node("ORCHESTRATOR", orchestrator_node)
#         graph.add_node("TABLE_AGENT", table_agent)
#         graph.add_node("SQL_AGENT", sql_agent)
#         graph.add_node("VALIDATOR_AGENT", validator_agent)

#         graph.add_edge(START, "ORCHESTRATOR")

#         graph.add_conditional_edges(
#             "ORCHESTRATOR",
#             orchestrator_router,
#             {
#                 "TABLE_AGENT": "TABLE_AGENT",
#                 "SQL_AGENT": "SQL_AGENT",
#                 "VALIDATOR_AGENT": "VALIDATOR_AGENT",
#                 END: END,
#             },
#         )

#         # All workers return control to orchestrator
#         graph.add_edge("TABLE_AGENT", "ORCHESTRATOR")
#         graph.add_edge("SQL_AGENT", "ORCHESTRATOR")
#         graph.add_edge("VALIDATOR_AGENT", "ORCHESTRATOR")

#         AGENT_ORCHESTRATOR_APP = graph.compile()

#     return AGENT_ORCHESTRATOR_APP

# def normalize_sql(sql: str) -> str:
#     sql = sql.replace("\n", " ")
#     sql = re.sub(r"\s+", " ", sql)
#     return sql.strip()

# async def run_orchestrator_agent(user_query: str) -> dict:
#     app = construct_app()

#     result = await app.ainvoke(
#         {
#             "messages": [HumanMessage(content=user_query)],
#             "tables": None,
#             "schemas": None,
#             "sqlQuery": None,
#             "validation": None,
#             "retry_count": 0,
#             "max_retries": 3,
#         }
#     )
#     sql= normalize_sql(result["sqlQuery"])
#     print('sql query is',sql)
#     query_result= await(execute_sql(sql))
#     nlp_answer= await(natural_answer_llm(query_result))
#     return {
#         "tables": result["tables"],
#         "schemas": result["schemas"],
#         "sqlQuery": sql,
#         "validation": result["validation"],
#         "retry_count": result["retry_count"],
#         "max_retries": result["max_retries"],
#         "Result": query_result,
#         "Agent_answer": nlp_answer
#     }

# async def natural_answer_llm(query_result):
#     model = get_llm()
#     system_message= SystemMessage(content=f"""
#         You are a data analyst. Given a user question and the query results (as JSON records),
# write a clear, faithful, and concise natural-language answer.
# query result -> {query_result}
# Guidelines:
# - Use numbers with context (totals, averages, counts).
# - Summarize trends instead of listing many rows.
# - If the result is empty, say so and suggest a next step (e.g., adjust filters).
# - Do not invent data beyond the records provided.
#         """)
#     response = await model.ainvoke([
#         system_message
#     ])
#     return response.content

# async def main():
#     response = await run_orchestrator_agent(
#         "What is the total billed amount for all LTL shipments?"
#     )
#     print(response)
#     await close_pool()


# if __name__ == "__main__":
#     asyncio.run(main())


# type: ignore
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from typing import List, Dict, Any, Optional
from state import AgentState
from tableAgent import table_agent
from sqlAgent import sql_agent
from sqlValidator import validator_agent
from db_config import close_pool, execute_sql
import re
from llm import get_llm

# --- NEW: FastAPI imports ---
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
try:
    from fastapi.middleware.cors import CORSMiddleware
except Exception:
    CORSMiddleware = None  # Optional CORS

import uvicorn

AGENT_ORCHESTRATOR_APP = None

def orchestrator_router(state: AgentState):
    if state.get("validation") and state["validation"].get("valid") is True:
        return END

    if state["tables"] is None:
        return "TABLE_AGENT"

    if state["sqlQuery"] is None:
        return "SQL_AGENT"

    if state["validation"] is None:
        return "VALIDATOR_AGENT"

    if state["retry_count"] < state["max_retries"]:
        return "SQL_AGENT"

    return END

def orchestrator_node(state: AgentState) -> AgentState:
    # Only act when validation failed
    if state["validation"] and state["validation"].get("valid") is False:
        return {
            "retry_count": state["retry_count"] + 1,
            "validation": None,
            "messages": add_messages(
                state["messages"],
                HumanMessage(
                    content=f"""
The previous SQL was invalid.

Validator feedback:
{state["validation"].get("suggestions", [])}

Fix the SQL accordingly.
"""
                ),
            ),
        }
    
    # print(state)
    return {}

def construct_app():
    global AGENT_ORCHESTRATOR_APP

    if AGENT_ORCHESTRATOR_APP is None:
        graph = StateGraph(AgentState)

        graph.add_node("ORCHESTRATOR", orchestrator_node)
        graph.add_node("TABLE_AGENT", table_agent)
        graph.add_node("SQL_AGENT", sql_agent)
        graph.add_node("VALIDATOR_AGENT", validator_agent)

        graph.add_edge(START, "ORCHESTRATOR")

        graph.add_conditional_edges(
            "ORCHESTRATOR",
            orchestrator_router,
            {
                "TABLE_AGENT": "TABLE_AGENT",
                "SQL_AGENT": "SQL_AGENT",
                "VALIDATOR_AGENT": "VALIDATOR_AGENT",
                END: END,
            },
        )

        # All workers return control to orchestrator
        graph.add_edge("TABLE_AGENT", "ORCHESTRATOR")
        graph.add_edge("SQL_AGENT", "ORCHESTRATOR")
        graph.add_edge("VALIDATOR_AGENT", "ORCHESTRATOR")

        AGENT_ORCHESTRATOR_APP = graph.compile()

    return AGENT_ORCHESTRATOR_APP

def normalize_sql(sql: str) -> str:
    sql = sql.replace("\n", " ")
    sql = re.sub(r"\s+", " ", sql)
    return sql.strip()

async def run_orchestrator_agent(user_query: str) -> dict:
    app = construct_app()

    result = await app.ainvoke(
        {
            "messages": [HumanMessage(content=user_query)],
            "tables": None,
            "schemas": None,
            "sqlQuery": None,
            "validation": None,
            "retry_count": 0,
            "max_retries": 3,
        }
    )
    sql = normalize_sql(result["sqlQuery"])
    print('sql query is', sql)
    query_result = await execute_sql(sql)
    nlp_answer = await natural_answer_llm(query_result)
    return {
        "tables": result["tables"],
        "schemas": result["schemas"],
        "sqlQuery": sql,
        "validation": result["validation"],
        "retry_count": result["retry_count"],
        "max_retries": result["max_retries"],
        "Result": query_result,
        "Agent_answer": nlp_answer
    }

async def natural_answer_llm(query_result):
    model = get_llm()
    system_message = SystemMessage(content=f"""
        You are a data analyst. Given a user question and the query results (as JSON records),
write a clear, faithful, and concise natural-language answer.
query result -> {query_result}
Guidelines:
- Use numbers with context (totals, averages, counts).
- Summarize trends instead of listing many rows.
- If the result is empty, say so and suggest a next step (e.g., adjust filters).
- Do not invent data beyond the records provided.
        """)
    response = await model.ainvoke([
        system_message
    ])
    return response.content

# -----------------------------
# NEW: FastAPI app + endpoint
# -----------------------------
app = FastAPI(
    title="Agent Orchestrator API",
    version="1.0.0",
    description="Ask your SQL agent orchestration layer questions via an HTTP endpoint."
)

# Optional CORS (safe defaults; restrict in prod)
if CORSMiddleware is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class AskAgentRequest(BaseModel):
    user_query: str

class AskAgentResponse(BaseModel):
    tables: Optional[Any] = None
    schemas: Optional[Any] = None
    sqlQuery: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    retry_count: int
    max_retries: int
    Result: Optional[Any] = None
    Agent_answer: Optional[str] = None

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/ask_agent", response_model=AskAgentResponse)
async def ask_agent(payload: AskAgentRequest):
    """
    Accepts a user query and returns the same structure your `main()` printed,
    by calling `run_orchestrator_agent`.
    """
    try:
        result = await run_orchestrator_agent(payload.user_query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await close_pool()
    except Exception:
        pass

# -----------------------------
# Replace the old CLI main with API server run
# -----------------------------
if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run("YOUR_MODULE_NAME:app", host="0.0.0.0", port=8000, reload=True)
    # ^^^ IMPORTANT: Replace YOUR_MODULE_NAME with the current filename (without .py)