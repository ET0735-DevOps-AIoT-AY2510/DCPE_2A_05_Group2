from database.models import Product, db
from database.seed_data import app

def load_products_from_db():
    with app.app_context():
        products = Product.query.order_by(Product.id).all()
        return {product.id: {
                    "name": product.name,
                    "price": product.price,
                    "stock": product.stock
                } for product in products}

def update_stock_in_db(product_id):
    with app.app_context():
        product = Product.query.get(product_id)
        if product and product.stock > 0:
            product.stock -= 1
            db.session.commit()
            return True
        return False

def change_stock_in_db(product_id, add_min, quantity):
    with app.app_context():
        product = Product.query.get(product_id)
        if add_min == True:
            product.stock += quantity
        elif add_min == False:
            if product.stock < quantity:
                print("Not Enough Stock to remove, exiting program.")
                return
            else:
                product.stock -= quantity
        db.session.commit()
        return
        