# Purpose of this file: 
# All customer facing routes

from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from . import db
import json

directories = Blueprint('directories', __name__)

# This is for the homepage -> To see which drinks are available to buy
@directories.route('/', methods=['GET', 'POST']) 
def home():
    return render_template("home.html")

# This is for the users to view the cart
@directories.route('/cart', methods=['GET', 'POST'])
def view_cart():
    return render_template("carts.html")

# Checkout 
@directories.route('/product-details', methods=['GET', 'POST'])
def checkout():
    return render_template("product_details.html")

# Payment Success  
@directories.route('/product-details/checkout', methods=['GET', 'POST'])
def payment():
    return render_template("checkout.html")


# Payment Success  
@directories.route('/product-details/payment-success', methods=['GET', 'POST'])
def payment():
    return render_template("payment_success.html")