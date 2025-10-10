from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_tavily import TavilySearch
from typing_extensions import TypedDict
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import Annotated
from pprint import pprint
import os


load_dotenv()

groq_model = os.getenv("GROQ_MODEL")

llm = ChatGroq(model=groq_model, temperature=0.75, max_tokens=None)

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

tool = TavilySearch(max_results=2)
tools = [tool]
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile()

response = graph.invoke({"messages": [{"role": "user", "content": "What is the most popular sport in the world, and include only wikipedia sources."}]})

pprint(response)
