import pathlib
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

DB_PATH = pathlib.Path(__file__).parent / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    state = Column(String, nullable=False, default="online")  # online/offline

    items = relationship("Item", back_populates="category")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="items")


class CategoryOut(BaseModel):
    id: int
    name: str
    state: str

    class Config:
        orm_mode = True


class ItemOut(BaseModel):
    id: int
    name: str
    price: int
    category: CategoryOut

    class Config:
        orm_mode = True


app = FastAPI(title="Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed categories if empty
        if db.query(Category).count() == 0:
            categories = [
                Category(name="Storefronts", state="online"),
                Category(name="Carts", state="online"),
                Category(name="Bags", state="online"),
                Category(name="Logistics", state="online"),
            ]
            db.add_all(categories)
            db.flush()
            items = [
                Item(name="Shopfront", price=1200, category_id=categories[0].id),
                Item(name="Market kiosk", price=900, category_id=categories[0].id),
                Item(name="Cart outline", price=500, category_id=categories[1].id),
                Item(name="Cart filled", price=650, category_id=categories[1].id),
                Item(name="Shopping bag", price=450, category_id=categories[2].id),
                Item(name="Gift bag", price=520, category_id=categories[2].id),
                Item(name="Delivery van", price=1400, category_id=categories[3].id),
                Item(name="Package", price=300, category_id=categories[3].id),
            ]
            db.add_all(items)
            db.commit()
    finally:
        db.close()


@app.get("/items", response_model=List[ItemOut])
def list_items(
    category_id: Optional[int] = None,
    item_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = select(Item).join(Item.category)
    if category_id is not None:
        query = query.where(Item.category_id == category_id)
    if item_id is not None:
        query = query.where(Item.id == item_id)
    results = db.execute(query).scalars().all()
    return results


@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    query = select(Category).order_by(Category.id)
    return db.execute(query).scalars().all()


@app.on_event("startup")
def on_startup():
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
