# short/schemas.py


from pydantic import AnyUrl, Field, BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class URLBase(BaseModel):
    target_url: AnyUrl
    custom_key: Optional[str] = Field(
        default=None,
        description="Alias opcional. Si lo dejas vacio, se genera automaticamente.",
        examples=[None],
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=3650,
        description="Caducidad opcional en días. Si no se indica, se usa el valor por defecto de settings.",
    ) 

class URL(URLBase):
    is_active: bool
    clicks: int

    expires_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None  # <-- CAMBIO: exponer marca de desactivación en responses
    created_at: Optional[datetime] = None   
    
    state: str 
 
    model_config = ConfigDict(from_attributes=True)


class URLInfo(URL):
    url: str
    admin_url: str

    state: str = Field(description="active | expired | disabled")  # <-- CAMBIO: estado calculado para admin/UI

    model_config = ConfigDict(from_attributes=True)
