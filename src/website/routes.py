# Purpose of this file: 
# All customer facing routes

from flask import Blueprint, render_template, request, flash, jsonify, Flask, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from . import db
import json
from .models import Product, User, Order
from werkzeug.security import generate_password_hash

from flask_login import login_required, current_user

directories = Blueprint('directories', __name__)

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



# This is for the homepage -> To see which drinks are available to buy
@directories.route('/', methods=['GET', 'POST']) 
def home():
    products = Product.query.all() # Gets all the product from the database
    return render_template("home.html", products=products)

# This is for the users to view the cart
@directories.route('/cart', methods=['GET', 'POST'])
@login_required
def view_cart():
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
    return render_template("carts.html", cart_items=cart_items)

# Checkout 
@directories.route('/product-details', methods=['GET', 'POST'])
def product_details():
    return render_template("product_details.html")

# Payment Success  
@directories.route('/product-details/checkout', methods=['GET', 'POST'])
def checkout():
    return render_template("checkout.html")


# Payment Success  
@directories.route('/product-details/payment-success', methods=['GET', 'POST'])
def payment_success():
    return render_template("payment_success.html")

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

