from website import db, create_app
from .models import Product

app = create_app()

with app.app_context():
    db.create_all()
    p1 = Product(name="Water Bottle", price=0.50,image_file="database_images/mineral_water.jpg", stock=10)
    p2 = Product(name="Coke", price=2,image_file="database_images/coke.jpg", stock=8)
    p3 = Product(name="Sprite", price=2.00,image_file="database_images/sprite.png", stock=12)

    db.session.add_all([p1, p2, p3])
    db.session.commit()
    print("Sample Products Inserted Successfully")