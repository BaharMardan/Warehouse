from pydantic import BaseModel


class ItemCreate(BaseModel):
    name_kala: str | None = None
    unite: str | None = None


class ItemUpdate(BaseModel):
    name_kala: str | None = None
    unite: str | None = None
