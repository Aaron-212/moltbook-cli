from uuid import UUID

from pydantic import BaseModel


class RegisterAgent(BaseModel):
    api_key: str
    claim_url: str
    verification_code: str


class RegisterResponse(BaseModel):
    agent: RegisterAgent


class Agent(BaseModel):
    id: UUID
    name: str


class Status(BaseModel):
    success: bool
    status: str
    agent: Agent
