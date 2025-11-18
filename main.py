import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Multivendor Ecommerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------
# Helpers
# ----------------------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


def serialize_doc(doc: Dict[str, Any]):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    # Convert ObjectId refs if present
    if "vendor_id" in doc and isinstance(doc["vendor_id"], ObjectId):
        doc["vendor_id"] = str(doc["vendor_id"])
    return doc


# ----------------------
# Schemas (request models)
# ----------------------
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    category: str
    in_stock: bool = True
    images: Optional[List[str]] = None
    vendor_id: Optional[str] = None


class VendorIn(BaseModel):
    name: str
    bio: Optional[str] = None
    rating: Optional[float] = Field(default=4.5, ge=0, le=5)
    verified: bool = True
    logo: Optional[str] = None
    categories: Optional[List[str]] = None
    location: Optional[str] = None


# ----------------------
# Root & health
# ----------------------
@app.get("/")
def read_root():
    return {"message": "Multivendor Ecommerce API running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ----------------------
# Seed demo data (idempotent)
# ----------------------
@app.post("/api/seed")
def seed_demo():
    """Seed a small set of vendors and products if collections are empty"""
    if db is None:
        return {"status": "error", "message": "Database not configured"}

    vendors_count = db["vendor"].count_documents({})
    products_count = db["product"].count_documents({})

    if vendors_count == 0:
        vendors = [
            {"name": "Urban Outfitters", "bio": "Trendy apparel and accessories.", "verified": True, "rating": 4.6, "logo": "https://i.pravatar.cc/100?img=12", "categories": ["Fashion", "Accessories"], "location": "NY, USA"},
            {"name": "GreenLeaf Organics", "bio": "Organic groceries and produce.", "verified": True, "rating": 4.8, "logo": "https://i.pravatar.cc/100?img=32", "categories": ["Groceries"], "location": "CA, USA"},
            {"name": "TechNest", "bio": "Latest gadgets and electronics.", "verified": True, "rating": 4.7, "logo": "https://i.pravatar.cc/100?img=5", "categories": ["Electronics"], "location": "Remote"},
            {"name": "Crafted Co.", "bio": "Handmade goods from local artisans.", "verified": True, "rating": 4.9, "logo": "https://i.pravatar.cc/100?img=20", "categories": ["Home", "Gifts"], "location": "TX, USA"},
        ]
        db["vendor"].insert_many(vendors)

    if products_count == 0:
        vendors_list = list(db["vendor"].find({}))
        v_ids = [v["_id"] for v in vendors_list]
        sample_products = [
            {"title": "Vintage Denim Jacket", "description": "Classic fit, durable fabric.", "price": 79.99, "category": "Fashion", "in_stock": True, "images": ["https://images.unsplash.com/photo-1516826957135-700dedea698c?w=800"], "vendor_id": v_ids[0] if v_ids else None},
            {"title": "Organic Avocado Pack", "description": "Fresh and creamy.", "price": 9.99, "category": "Groceries", "in_stock": True, "images": ["https://images.unsplash.com/photo-1550258987-190a2d41a8ba?w=800"], "vendor_id": v_ids[1] if len(v_ids) > 1 else None},
            {"title": "Wireless Noise-Canceling Headphones", "description": "Immersive sound.", "price": 199.99, "category": "Electronics", "in_stock": True, "images": ["https://images.unsplash.com/photo-1518443871564-5acaed0c972e?w=800"], "vendor_id": v_ids[2] if len(v_ids) > 2 else None},
            {"title": "Handmade Ceramic Mug", "description": "Perfect for your morning coffee.", "price": 24.5, "category": "Home", "in_stock": True, "images": ["https://images.unsplash.com/photo-1516826957135-700dedea698c?w=800"], "vendor_id": v_ids[3] if len(v_ids) > 3 else None},
            {"title": "Silk Scarf", "description": "Soft and elegant.", "price": 34.0, "category": "Accessories", "in_stock": True, "images": ["https://images.unsplash.com/photo-1520975916090-3105956dac38?w=800"], "vendor_id": v_ids[0] if v_ids else None},
        ]
        db["product"].insert_many(sample_products)

    return {"status": "ok", "vendors": db["vendor"].count_documents({}), "products": db["product"].count_documents({})}


# ----------------------
# Products endpoints
# ----------------------
@app.get("/api/products")
def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category: Optional[str] = None,
    q: Optional[str] = Query(None, description="Search in title/description"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    in_stock: Optional[bool] = None,
):
    if db is None:
        return {"items": [], "page": page, "pages": 0, "total": 0}

    filter_q: Dict[str, Any] = {}
    if category:
        filter_q["category"] = category
    if in_stock is not None:
        filter_q["in_stock"] = in_stock
    if q:
        filter_q["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if min_price is not None or max_price is not None:
        price_filter: Dict[str, Any] = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filter_q["price"] = price_filter

    total = db["product"].count_documents(filter_q)
    skip = (page - 1) * limit

    cursor = db["product"].find(filter_q).skip(skip).limit(limit)
    items = [serialize_doc(d) for d in cursor]

    pages = (total + limit - 1) // limit if limit else 1

    return {"items": items, "page": page, "pages": pages, "total": total}


@app.get("/api/products/categories")
def list_categories():
    if db is None:
        return []
    cats = db["product"].distinct("category")
    return sorted([c for c in cats if isinstance(c, str)])


# ----------------------
# Vendors endpoints
# ----------------------
@app.get("/api/vendors")
def list_vendors(
    verified: bool = Query(True),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    if db is None:
        return {"items": [], "page": page, "pages": 0, "total": 0}

    filter_q: Dict[str, Any] = {}
    if verified is not None:
        filter_q["verified"] = verified

    total = db["vendor"].count_documents(filter_q)
    skip = (page - 1) * limit

    cursor = db["vendor"].find(filter_q).skip(skip).limit(limit)
    items = [serialize_doc(d) for d in cursor]

    pages = (total + limit - 1) // limit if limit else 1

    return {"items": items, "page": page, "pages": pages, "total": total}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
