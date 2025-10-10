from typing import Annotated, TypedDict
from pydantic import BaseModel
from langgraph.graph.message import add_messages


class Chatbot(BaseModel):
    message: str

class State(TypedDict):
    messages: Annotated[list, add_messages]