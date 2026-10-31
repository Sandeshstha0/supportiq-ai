from app.db.database import SessionLocal
from app.services.product_tool import search_products


def main():
    db = SessionLocal()

    try:
        products = search_products(
            db=db,
            query="rice",
        )

        if not products:
            print("No matching products found.")
            return

        for product in products:
            print(product)

    finally:
        db.close()


if __name__ == "__main__":
    main()