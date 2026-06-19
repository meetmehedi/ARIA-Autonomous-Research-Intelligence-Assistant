from pydantic import BaseModel, Field

class GeneratedFile(BaseModel):
    content: str

class AgentResponse(BaseModel):
    agent_name: str
    description: str
    files: dict[str, str]

print(AgentResponse.model_json_schema())
