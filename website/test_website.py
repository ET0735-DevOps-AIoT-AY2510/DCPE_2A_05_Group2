    import pytest
    from werkzeug.security import generate_password_hash
    from website import create_app, db
    from website.models import User, Product, Order

    @pytest.fixture
    def app():
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
        yield app
        with app.app_context():
            db.drop_all()

    @pytest.fixture
    def client(app):
        return app.test_client()

    @pytest.fixture
    def init_database(app):
        # Create a test user
        user = User(name="Test User", email="test@example.com", password=generate_password_hash("testpassword"))
        db.session.add(user)
        
        # Create a test product
        product = Product(name="Test Product", price=10.0, stock=5)
        db.session.add(product)

        db.session.commit()  # Commit the user and product to the DB

        # Create a test order (now that user and product are committed)
        order = Order(user_id=user.id, product_id=product.id, quantity=2, total_amount=20.0)
        db.session.add(order)
        db.session.commit()  # Commit the order to the DB

        return user

    def test_clear_cart(client, init_database):
        # Log in the test user
        with client:
            response = client.post('/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            })
            assert response.status_code == 302  # Check if login was successful

            # Check that the order exists before clearing the cart
            orders_before = Order.query.filter_by(user_id=init_database.id).all()
            print("Orders before clearing cart:", orders_before)  # Debugging output
            assert len(orders_before) == 1  # Expect 1 order before clearing

            # Clear the cart
            response = client.post('/cart/clear')
            assert response.status_code == 302  # Expect a redirect after clearing the cart

            # Check that the cart is cleared
            orders_after = Order.query.filter_by(user_id=init_database.id).all()
            print("Orders after clearing cart:", orders_after)  # Debugging output
            assert len(orders_after) == 0  # After clearing, expect 0 orders