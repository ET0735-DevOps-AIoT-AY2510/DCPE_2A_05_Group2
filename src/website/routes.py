# Purpose of this file: 
# All customer facing routes

from flask import Blueprint, render_template, request, flash, jsonify, Flask, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from . import db
import json
from .models import Product, User, Order
from werkzeug.security import generate_password_hash # For security
import qrcode # For QR Code generation
import os 

# For hardware implementation
from hardware_payment import scan_and_get_orders, process_order

directories = Blueprint('directories', __name__, url_prefix='/')

# Add to Cart route
@directories.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity', 1)
    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('directories.home'))
    if quantity < 1:
        flash('Invalid quantity.', 'error')
        return redirect(url_for('directories.home'))
    # Create new order
    new_order = Order(user_id=current_user.id, product_id=product.id, quantity=quantity, total_amount=product.price * quantity)
    db.session.add(new_order)
    db.session.commit()
    flash(f'Added {quantity} {product.name} to cart!', 'success')
    return redirect(url_for('directories.home'))

# Clear Cart on Payment 
@directories.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    Order.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Your cart has been cleared ', 'success')
    return redirect(url_for('directories.home'))

# Update Quantity Route
@directories.route('/cart/update-quantity', methods=['POST'])
@login_required
def update_quantity():
    order_id = request.form.get('order_id')
    action = request.form.get('action')
    order = Order.query.get(order_id)

    if not order or order.user_id != current_user.id:
        flash('Order not found.', 'error')
        return redirect(url_for('directories.view_cart'))
    
    product = Product.query.get(order.product_id)
    product_name = product.name if product else 'Item'
    
    if action == 'increase':
        order.quantity += 1
        db.session.commit()
        flash(f'Increased quantity of {product_name}!', 'success')

    elif action == 'decrease':
        if order.quantity > 0:
            order.quantity -= 1
            db.session.commit()
            flash(f'Decreased quantity of {product_name}!', 'success')

        else:
            flash('Quantity cannot be less than 1', 'error')

    elif action == 'delete':
        db.session.delete(order)
        db.session.commit()
        flash(f'Removed {product_name} from your cart!', 'success')

    return redirect(url_for('directories.view_cart'))



# This is for the homepage -> To see which drinks are available to buy
@directories.route('/', methods=['GET', 'POST']) 
def home():
    search_query = request.args.get('search', '').strip()

    if search_query:
        products = Product.query.filter(Product.name.ilike(f'%{search_query}')).all()

    else:
        products = Product.query.all()

    cart_count = 0

    if current_user.is_authenticated:
        orders = Order.query.filter_by(user_id=current_user.id).all()
        cart_count = sum(order.quantity for order in orders)
    return render_template("home.html", products=products, cart_count=cart_count, search_query=search_query)

# This is for the users to view the cart
@directories.route('/cart', methods=['GET', 'POST'])
@login_required
def view_cart():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    cart_items = []
    cart_total = 0
    for order in orders:
        product = Product.query.get(order.product_id)

        if product:
            item_total = product.price * order.quantity
            cart_items.append({
                'id': order.id,
                'name': product.name,
                'quantity': order.quantity,
                'price': product.price
            })

            cart_total += item_total
    return render_template("carts.html", cart_items=cart_items, cart_total=cart_total)

# Checkout 
@directories.route('/product-details', methods=['GET', 'POST'])
@login_required
def product_details():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    cart_items = []

    for order in orders:
        product = Product.query.get(order.product_id)
        if product:
            cart_items.append({
                'id': order.id,
                'name': product.name,
                'quantity': order.quantity,
                'price': product.price
            })
    order_total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template("product_details.html", cart_items=cart_items, order_total=order_total)

# Payment Success  
@directories.route('/product-details/checkout', methods=['GET', 'POST'])
def checkout():    
    return render_template("checkout.html")


# Payment Success  
@directories.route('/product-details/payment-success', methods=['GET', 'POST'])
def payment_success():
    # Data for QR code: user id and order ids
    orders = Order.query.filter_by(user_id=current_user.id).all()
    order_ids = [str(order.id) for order in orders]
    qr_data = str(current_user.id)

    # Ensure the qr_images folder exist 
    qr_folder = os.path.join('website', 'static', 'images', 'qr_images')
    os.makedirs(qr_folder, exist_ok=True)

    qr_filename = f"user_{current_user.id}_qr.png"
    qr_path = os.path.join(qr_folder, qr_filename)
    qrcode.make(qr_data).save(qr_path)

    # Pass the relative path from static to URL for
    qr_url = f"images/qr_images/{qr_filename}"

    # order_list = scan_and_get_orders()

    # process_order(order_list)

    return render_template("payment_success.html", qr_filename=qr_url)

@directories.route('/product-details/payment-success/qr_scanning', methods=['GET', 'POST'])
def qr_scan():

    order_list = scan_and_get_orders()

    process_order(order_list)

    return redirect(url_for('directories.home'))




# Login Information
@directories.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user) # This logs the users in
            flash('Successfully logged in!', 'success')
            return redirect(url_for('directories.home'))        
        else: 
            flash('Invalid Email or Password', 'error')
            return redirect(request.url)
        
    return render_template("login.html", user=current_user)

# Login Information
@directories.route('/login/new-accounts', methods=['GET', 'POST'])
def new_accounts():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if the email already exists 
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return redirect(url_for('directories.login'))
        
        # Store password in plain text (for testing only)
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Accounts created successfully! Please log in now!', 'success')
        return redirect(url_for('directories.login'))


    return render_template("new_accounts.html", user=current_user)

# Log Out 
@directories.route('/logout')
def logout():
    logout_user()
    flash('You have been signed out', 'success')

    return redirect(url_for('directories.home'))

