"""Schema untuk API key (BYOK)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.api_key import Provider


class ApiKeyCreate(BaseModel):
    provider: Provider
    api_key: str = Field(min_length=8, max_length=512)


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: Provider
    hint: str
    created_at: datetime
