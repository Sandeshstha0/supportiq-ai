from sqlalchemy import select

from app.db.database import Base, SessionLocal, engine
from app.models.product import ProductDB


SAMPLE_PRODUCTS = [
    {
        "name": "Basmati Rice",
        "category": "Grocery",
        "price": 180.00,
        "unit": "kg",
        "stock": 75,
        "description": "Premium long-grain basmati rice.",
        "brand": "Lasata Select",
    },
    {
        "name": "Jeera Masino Rice",
        "category": "Grocery",
        "price": 120.00,
        "unit": "kg",
        "stock": 40,
        "description": "Traditional Nepali jeera masino rice.",
        "brand": "Lasata Select",
    },
    {
        "name": "Sunflower Cooking Oil",
        "category": "Grocery",
        "price": 250.00,
        "unit": "liter",
        "stock": 30,
        "description": "Refined sunflower oil for everyday cooking.",
        "brand": "Golden Harvest",
    },
    {
        "name": "Milk Chocolate",
        "category": "Snacks",
        "price": 100.00,
        "unit": "pack",
        "stock": 50,
        "description": "Creamy milk chocolate.",
        "brand": "Sweet Treats",
    },
    {
        "name": "Potato Chips",
        "category": "Snacks",
        "price": 50.00,
        "unit": "pack",
        "stock": 0,
        "description": "Crispy salted potato chips.",
        "brand": "Crunchy",
    },
    {
        "name": "Laundry Detergent",
        "category": "Household",
        "price": 220.00,
        "unit": "pack",
        "stock": 25,
        "description": "Detergent for everyday laundry.",
        "brand": "Clean Home",
    },
]


def seed_products():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_names = set(
            db.scalars(select(ProductDB.name)).all()
        )

        new_products = [
            ProductDB(**product)
            for product in SAMPLE_PRODUCTS
            if product["name"] not in existing_names
        ]

        if not new_products:
            print("Sample products already exist.")
            return

        db.add_all(new_products)
        db.commit()

        print(f"Inserted {len(new_products)} sample products.")


if __name__ == "__main__":
    seed_products()