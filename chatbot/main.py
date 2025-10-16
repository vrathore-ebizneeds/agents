from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_core.messages import ToolMessage
from langgraph.exceptions import GraphInterrupt
from langgraph.types import Command
from agent.agent import graph
from api import chat_api
import asyncio
import json


app = FastAPI()

app.include_router(chat_api.router)

@app.get("/")
def get_root():
    return {'message':'chatbot api is up.'}

@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "input":
                inputs = {"messages": [{"role": "user", "content": message["content"]}]}
                
                # Stream until interrupt
                try:
                    async for event in graph.astream_events(inputs, config, version="v2"):
                        if event["event"] == "on_chat_model_stream":
                            await websocket.send_json({"type": "stream", "content": event["data"]["chunk"].content or ""})
                        # No break here—let it run to interrupt
                        
                        # Optional: Send tool call detection for early UI hints
                        if "on_tool_start" in event["event"]:
                            await websocket.send_json({"type": "tool_call", "name": event["name"]})
                            
                except GraphInterrupt:
                    # Interrupt detected—get current state
                    state = graph.get_state(config)
                    # Find the last tool call (assuming single call)
                    last_ai_msg = state.values["messages"][-1]
                    tool_call_id = last_ai_msg.tool_calls[0]["id"] if last_ai_msg.tool_calls else None
                    
                    # Send interrupt payload (e.g., the query from tool args)
                    interrupt_payload = {
                        "query": last_ai_msg.tool_calls[0]["args"]["query"] if tool_call_id else "Assistance needed"
                    }
                    await websocket.send_json({"type": "interrupt", "payload": interrupt_payload})
                
                # Now wait for resume in the outer loop
            
            elif message["type"] == "resume":
                # Inject ToolMessage with human input
                state = graph.get_state(config)
                last_ai_msg = state.values["messages"][-1]
                tool_call_id = last_ai_msg.tool_calls[0]["id"] if last_ai_msg.tool_calls else None
                
                if tool_call_id:
                    tool_msg = ToolMessage(
                        content=message["content"],
                        tool_call_id=tool_call_id,
                        name="human_assistance"
                    )
                    graph.update_state(config, {"messages": [tool_msg]})
                
                # Resume streaming (continues to chatbot for final response)
                async for event in graph.astream_events(None, config, version="v2"):
                    if event["event"] == "on_chat_model_stream":
                        await websocket.send_json({"type": "stream", "content": event["data"]["chunk"].content or ""})
                    elif event["event"] == "on_chain_end":
                        # Serialize final state
                        final_state = event["data"]["output"]
                        serialized_output = {
                            "messages": [
                                {
                                    "type": msg.type,
                                    "content": msg.content,
                                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls] if hasattr(msg, "tool_calls") and msg.tool_calls else []
                                }
                                for msg in final_state["messages"]
                            ]
                        }
                        await websocket.send_json({"type": "final", "output": serialized_output})
                        break  # Done for this cycle
    
    except WebSocketDisconnect:
        print(f"Client disconnected for thread {thread_id}")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

# @app.websocket("/ws/{thread_id}")
# async def websocket_endpoint(websocket:WebSocket, thread_id:str):
#     await websocket.accept()
#     config = {'configurable':{'thread_id':thread_id}}

#     try:
#         while True:
#             data = await websocket.receive_text()
#             message = json.loads(data)
            
#             if message['type']=='input':
#                 inputs = {'messages':[{'role':'user', 'content':message['content']}]}

#                 async for event in graph.astream_events(inputs, config, version='v2'):
#                     if event['event'] == 'on_chat_model_stream':
#                         # --------------------->
#                         await websocket.send_json({'type':'stream','content':event['data']['chunk'].content})
#                     elif event['event'] == 'on_tool_end' and event['name'] == 'human_assistance':
#                         interrupt_payload = {'query':event['data']['input']['query']}
#                         await websocket.send_json({'type':'interrupt', 'payload': interrupt_payload})
#                         break
#             elif message['type'] == 'resume':
#                 resume_command = Command(resume=message['content'])
#                 async for event in graph.astream_events(None, config, version='v2'):
#                     if event['event'] == 'on_chat_model_stream':
#                         await websocket.send_json({'type':'stream', 'content':event['data']['chunk'].content})
#                     if event['event'] == 'on_chain_end':
#                         serialized_output = {
#                             'messages': [msg.model_dump() for msg in event['data']['output']['messages']]
#                         }
#                         await websocket.send_json({'type':'final', 'output': serialized_output})

#     except WebSocketDisconnect:
#         print(f'Client disconnected for thread: {thread_id}')

# @app.post("/tavily")
# def search_tavily(message: str = Body(..., embed=True)):
#     response = tavily_tool.invoke(input=message)
#     return {'response':response}