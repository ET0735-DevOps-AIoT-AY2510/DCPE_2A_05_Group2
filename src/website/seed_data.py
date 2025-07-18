from website import db, create_app
from website.models import Product

app = create_app()

with app.app_context():
    db.create_all()
    p1 = Product(name="Water Bottle", price=0.50, stock=10)
    p2 = Product(name="Coke", price=2, stock=8)
    p3 = Product(name="Sprite", price=2.00, stock=12)

    db.session.add_all([p1, p2, p3])
    db.session.commit()
    print("Sample Products Inserted Successfully")