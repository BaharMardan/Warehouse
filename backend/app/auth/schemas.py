from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    is_admin: str
    permissions: list[str] = []
    must_change_password: bool = False

class PasswordChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)
