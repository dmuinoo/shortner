# short/schemas.py


from pydantic import AnyUrl, Field, BaseModel, ConfigDict
from typing import Optional


class URLBase(BaseModel):
    target_url: AnyUrl
    custom_key: Optional[str] = Field(
        default=None,
        description="Alias opcional. Si lo dejas vacio, se genera automaticamente.",
        examples=[None],
    )


class URL(URLBase):
    is_active: bool
    clicks: int

    model_config = ConfigDict(from_attributes=True)


class URLInfo(URL):
    url: str
    admin_url: str

    model_config = ConfigDict(from_attributes=True)
