# Purpose of this file: 
# Inventory, Staff Login info, name infos

from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=db.func.now())
    total_amount = db.Column(db.Float)