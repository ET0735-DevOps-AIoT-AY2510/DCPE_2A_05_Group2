from website import db, create_app
from website.models import Product, Staff

app = create_app()

with app.app_context():
    db.create_all()

    # Drink items data
    p1 = Product(name="Water Bottle", price=0.50, stock=10)
    p2 = Product(name="Coke", price=2, stock=8)
    p3 = Product(name="Sprite", price=2.00, stock=12)

    # Staff Data 
    staff1 = Staff(name="chunho", email="phangchunhoe2007@gmail.com", phone_number="87167758", password="i love devops")

    db.session.add_all([p1, p2, p3, staff1])
    db.session.commit()
    print("Sample Products and Staff Inserted Successfully")