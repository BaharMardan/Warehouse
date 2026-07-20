from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name_kala: str = Field(min_length=1)
    unite: str | None = None


class ItemUpdate(BaseModel):
    name_kala: str = Field(min_length=1)
    unite: str | None = None