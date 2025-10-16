from schemas.chatbot_schema import Chatbot
from fastapi import APIRouter
from agent.agent import graph

router = APIRouter()

config = {"configurable":{"thread_id":"1"}}

@router.post("/chat")
def chat_with_agent(message:Chatbot):
    # print(message)
    response = graph.invoke(
        {
            'messages':[
                {
                    'role':'user', 
                    'content':message.message
                }
            ]
        },
        config=config
    )
    return {'response':response['messages'][-1].content}

