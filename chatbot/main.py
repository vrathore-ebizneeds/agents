from fastapi import FastAPI
from api import chat_api


app = FastAPI()

app.include_router(chat_api.router)

@app.get("/")
def get_root():
    return {'message':'chatbot api is up.'}

# @app.post("/tavily")
# def search_tavily(message: str = Body(..., embed=True)):
#     response = tavily_tool.invoke(input=message)
#     return {'response':response}