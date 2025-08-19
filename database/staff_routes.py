from flask import Blueprint, render_template, request, flash, Flask, redirect, url_for, current_app
from flask_login import login_required, current_user, login_user, logout_user
from . import db
from .models import Product, Staff, Order
import os
from werkzeug.utils import secure_filename
from sqlalchemy import or_



staff_directories = Blueprint('staff_directories', __name__, url_prefix='/staff')

@staff_directories.route('/add-staff', methods=['GET', 'POST'])
def add_staff():
    new_staff = None
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if the email or phone number already exists 
        existing_user = Staff.query.filter(or_(Staff.email == email, Staff.phone_number == phone_number)).first()
        if existing_user:
            flash('Email or phone number already registered!', 'error')
            return redirect(url_for('staff_directories.staff_login'))
        
        # Store password in plain text (for testing only)
        new_staff = Staff(name=name, email=email, phone_number=phone_number, password=password)
        db.session.add(new_staff)
        db.session.commit()
        flash('Account created successfully! Please log in now!', 'success')
        return redirect(url_for('staff_directories.staff_login'))

    return render_template('staff_templates/add_staff.html', staff=new_staff)


@staff_directories.route('/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        staff_phone_number = request.form.get('staff_phone_number')
        password = request.form.get('password')
        staff = Staff.query.filter_by(phone_number=staff_phone_number).first()

        if staff and staff.password == password:
            login_user(staff) # This logs the staff in
            flash('Successfully logged in!', 'success')
            return redirect(url_for('staff_directories.staff_home'))        
        
        else: 
            flash('Invalid Email or Password', 'error')
            return redirect(request.url)
        
    return render_template('staff_templates/staff_login.html')


@staff_directories.route('/home-iA#!8_92cd3vd', methods=['GET', 'POST'])
def staff_home():

    return render_template('staff_templates/staff_home.html')

@staff_directories.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        image = request.files.get('image')

        # Check if the image is a jpg image
        if image and not image.filename.lower().endswith('.jpg'):
            flash("Only .jpg images are allowed.", "danger")
            return redirect(request.url)
        # Check if product already exists
        existing_product = Product.query.filter(db.func.lower(Product.name) == name.lower()).first()
        if existing_product:
            flash(f"A product named '{name}' already exists.", "danger")
            return redirect(url_for('staff_directories.add_product'))
        
        # Save product into database
        new_product = Product(name=name, price=price, stock=stock)
        db.session.add(new_product)
        db.session.commit()

        # Save Image if uploaded
        if image:
            filename = name.lower().replace(' ', '_') + '.jpg'
            filename = secure_filename(filename)
            img_folder = os.path.join(current_app.root_path, 'static', 'images', 'drink_images')
            os.makedirs(img_folder, exist_ok=True)
            img_path = os.path.join(img_folder, filename)
            image.save(img_path)

        flash(f"{name} added successfully!", "success")
        return redirect(url_for('staff_directories.add_product'))
    

    return render_template('staff_templates/add_drink.html')

@staff_directories.route('/update-drinks', methods=['GET'])
def update_drinks():
    search_query = request.args.get('search', '').strip()

    if search_query:
        products = Product.query.filter(Product.name.ilike(f'%{search_query}')).all()

    else:
        products = Product.query.all()

    return render_template('staff_templates/update_drinks.html', products=products)

@staff_directories.route('/update-drinks/<int:product_id>', methods=['POST'])
def update_drink(product_id):
    product = Product.query.get_or_404(product_id)
    product.name = request.form.get('name')
    product.price = float(request.form.get('price'))
    product.stock = int(request.form.get('stock'))
    db.session.commit()
    flash(f"{product.name} updated successfully!", "success")

    return redirect(url_for('staff_directories.update_drinks'))


@staff_directories.route('/logout')
def logout():
    flash('You have been signed out', 'success')

    return redirect(url_for('directories.staff_login'))

@staff_directories.route('/delete-drinks/<int:product_id>', methods=['GET', 'POST'])
def delete_drinks(product_id):
    product = Product.query.get_or_404(product_id)

    img_folder = os.path.join(current_app.root_path, 'static', 'images', 'drink_images')
    filename = product.name.lower().replace(' ', '_') + '.jpg'
    img_path = os.path.join(img_folder, filename)

    if os.path.exists(img_path):
        os.remove(img_path)

    db.session.delete(product)
    db.session.commit()
    flash(f"{product.name} deleted successfully!", "success")
    return redirect(url_for('staff_directories.update_drinks'))
