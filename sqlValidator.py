# type: ignore
from llm import get_json_llm
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from typing import TypedDict, List, Annotated, Sequence
import json
from state import AgentState


async def validator_agent(state: AgentState) -> AgentState:
    # model = get_llm()
    model = get_json_llm()
    system_msg = SystemMessage(content="""
        You are an SQL Server Validator Agent acting as an impartial judge.
        Evaluate the SQL Server query against the user request and schema.
        The tables are within the dbo schema
        Check if the query logically answer the user question

        Return STRICT JSON only in this format:
        {
        "valid": true | false,
        "suggestions": []
        }

        Rules:
        - "valid" MUST be a boolean
        - "suggestions" MUST be a list of strings
        - Do NOT include explanations outside JSON
        """
    )

    # Always validate against the ORIGINAL user query
    user_msg = HumanMessage(content=f"""
User Query:
{state["messages"][0].content}

Available Tables:
{state["tables"]}

Schemas:
{state["schemas"]}

SQL Query:
{state["sqlQuery"]}
""")

    response = await model.ainvoke([system_msg, user_msg])

    try:
        validation = json.loads(response.content)

        if not isinstance(validation, dict):
            raise ValueError("Validation output is not a JSON object")

        if not isinstance(validation.get("valid"), bool):
            raise ValueError("'valid' must be a boolean")

        if not isinstance(validation.get("suggestions"), list):
            raise ValueError("'suggestions' must be a list")

    except Exception as e:
        raise ValueError(
            f"Validator returned invalid JSON:\n{response.content}"
        ) from e
    return {
        "validation": validation
    }