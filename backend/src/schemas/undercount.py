from pydantic import BaseModel, Field
class CapsInput(BaseModel):
    caps: dict[str, int] = Field(default_factory=dict, max_length=5000)
    batch_cap: int = Field(ge=0, le=1_000_000)
class UndercountCreate(CapsInput):
    name: str = Field(min_length=2, max_length=160)
    dataset_id: int
    zone: str = Field(default='全部', max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=80)
class CapsUpdate(CapsInput):
    base_revision: int = Field(ge=1)
class ApproveInput(BaseModel):
    revision: int = Field(ge=1)
