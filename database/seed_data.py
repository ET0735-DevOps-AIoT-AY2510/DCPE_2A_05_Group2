# database/seed_data.py

from database.__init__ import db, create_app
from database.models import Product, Staff
from database.products import Vending_Drinks  # dict of 1..9 -> {name, price, stock}

app = create_app()

def seed():
    with app.app_context():
        # 1) Always create tables first
        db.create_all()

        # 2) Seed products if empty
        if Product.query.first() is None:
            # Ensure IDs match 1..9 so keypad choices line up
            rows = []
            for pid in sorted(Vending_Drinks.keys()):
                d = Vending_Drinks[pid]
                rows.append(Product(
                    id=pid,
                    name=d["name"],
                    price=d["price"],
                    stock=d["stock"],
                ))
            db.session.add_all(rows)
            print(f"Inserted {len(rows)} products")

        # 3) Seed staff if empty
        if Staff.query.first() is None:
            s1 = Staff(
                name="chunho",
                email="phangchunhoe2007@gmail.com",
                phone_number="87167758",
                password="i love devops",   # consider hashing later
            )
            s2 = Staff(
                name="titus",
                email="titussohpx@gmail.com",
                phone_number="93637080",
                password="livelaughlove",
            )
            db.session.add_all([s1, s2])
            print("Inserted 2 staff")

        db.session.commit()
        print("DB ready & seeded (if empty).")

if __name__ == "__main__":
    seed()
