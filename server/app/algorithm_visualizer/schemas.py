from pydantic import BaseModel

class AlgorithmGenerateRequest(BaseModel):
    language: str
    code: str
    input: str
