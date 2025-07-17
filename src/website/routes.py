# Purpose of this file: 
# All customer facing routes

from flask import Blueprint, render_template, request, flash, jsonify, Flask
from flask_login import login_required, current_user
from . import db
import json
from .models import Product, User
from werkzeug.security import generate_password_hash


directories = Blueprint('directories', __name__)

# This is for the homepage -> To see which drinks are available to buy
@directories.route('/', methods=['GET', 'POST']) 
def home():
    products = Product.query.all() # Gets all the product from the database
    return render_template("home.html", products=products)

# This is for the users to view the cart
@directories.route('/cart', methods=['GET', 'POST'])
def view_cart():
    return render_template("carts.html")

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
    return render_template("login.html", user=current_user)

# Login Information
@directories.route('/login/new-accounts', methods=['GET', 'POST'])
def new_accounts():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

    # Validate Passwords one more time
    if password 


    return render_template("new_accounts.html", user=current_user)
