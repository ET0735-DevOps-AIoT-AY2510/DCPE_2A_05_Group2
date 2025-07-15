from . import db, create_app
from .models import Product

app = create_app()

with app.app_context():
    p1 = Product(name="Water Bottle", price=0.50,image_filename="", stock=10)
    p2 = Product(name="Coke", price=2,image_filename="", stock=8)
    p3 = Product(name="Sprite", price=2.00,image_filename="", stock=12)

    db.session.add_all([p1, p2, p3])
    db.session.commit()
    print("Sample Products Inserted Successfully")