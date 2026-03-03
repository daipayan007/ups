from typing import TypedDict, Sequence, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    tables: List[str] | None
    schemas: dict | None
    sqlQuery: str | None
    validation: dict | None
    retry_count: int
    max_retries: int