import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv(verbose=True)



class Agent:


    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=1.2
        )

