#type: ignore
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage
from langgraph.graph import START, END, StateGraph
from db_config import get_pool
from llm import get_llm
from typing import TypedDict, Annotated,Sequence, List
from langgraph.graph.message import add_messages
from state import AgentState

async def sql_agent(state: AgentState) -> AgentState:
    model = get_llm()

    system_msg = SystemMessage(content=f"""
        You are an SQL Server generation agent.

        Generate a valid SQL Server SQL query that answers the user intent.

        Constraints:
        - Use ONLY the provided tables, All tables are within dbo schema
        - Use ONLY the provided schema
        - Do NOT invent tables or columns
        - Do NOT add any comments in the SQL Queries
        - Return ONLY executable SQL
        - No explanations

        Tables:
        {state["tables"]}

        Schemas:
        {state["schemas"]}
        """
    )

    response = await model.ainvoke([
        system_msg,
        state["messages"][-1]
    ])

    sql = response.content.strip()
    sql = sql.removeprefix("```sql").removesuffix("```").strip()

    return {
        "sqlQuery": sql
    }

