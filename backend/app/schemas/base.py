from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Reusable base for all API response models."""

    model_config = ConfigDict(from_attributes=True)
