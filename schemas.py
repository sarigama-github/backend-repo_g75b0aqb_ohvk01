from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# Collection: vendor
class Vendor(BaseModel):
    name: str = Field(..., description="Vendor display name")
    bio: Optional[str] = Field(None, description="Short description about the vendor")
    rating: Optional[float] = Field(default=4.5, ge=0, le=5)
    verified: bool = Field(default=True)
    logo: Optional[str] = Field(None, description="Logo image URL")
    categories: Optional[List[str]] = Field(default=None)
    location: Optional[str] = Field(default=None)

# Collection: product
class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    category: str
    in_stock: bool = True
    images: Optional[List[str]] = None
    vendor_id: Optional[str] = None

# Collection: subscriber (for newsletter)
class Subscriber(BaseModel):
    email: EmailStr
