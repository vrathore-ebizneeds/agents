from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START
from langchain_tavily import TavilySearch
from schemas.chatbot_schema import State
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pprint import pprint
import os



load_dotenv()
# ------------------------ LLM ---------------------------------------
groq_model = os.getenv("GROQ_MODEL")

llm = ChatGroq(model=groq_model, temperature=0.75, max_tokens=None)
# --------------------------------------------------------------------

graph_builder = StateGraph(State)

# ------------Human in the loop---------------------------
@tool
def human_assistance(query:str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({'query':query})
    return human_response['data']
# --------------------------------------------------------

tavily_search_tool = TavilySearch(max_results=2)

memory = InMemorySaver()

tools = [tavily_search_tool, human_assistance]
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    message = llm_with_tools.invoke(state["messages"])
    assert len(message.tool_calls) <= 1
    return {"messages": [message]}

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)

graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile(checkpointer=memory, interrupt_after=['tools'])

# response = graph.invoke({"messages": [{"role": "user", "content": "What is the most popular sport in the world, and include only wikipedia sources."}]})

# pprint(response)

user_input = "I need some expert guidance for building AI agent. Could you request assistance for me"
config = {'configurable':{'thread_id':'1'}}


events = graph.stream(
    {'messages':[{'role':'user', 'content':user_input}]},
    config=config,
    stream_mode='values'
)

for event in events:
    if 'messages' in event:
        event['messages'][-1].pretty_print()

human_response = {'Hello, Im the expert here, please use crew ai, follow their documentations!'}

human_command = Command(resume={'data':human_response})

events = graph.stream(
    human_command,
    config=config,
    stream_mode='values'
)

for event in events:
    if 'messages' in event:
        event['messages'][-1].pretty_print()