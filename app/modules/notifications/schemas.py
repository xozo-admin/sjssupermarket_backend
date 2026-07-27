from pydantic import BaseModel, Field


class DeviceRegistration(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern="^(android|ios|web)$")
