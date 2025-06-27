from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter
from flask import Response
import csv
from io import StringIO
from models import Load 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loadpilot.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    truck_number = db.Column(db.String(50))
    phone = db.Column(db.String(20))

class Load(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pickup = db.Column(db.String(100))
    drop = db.Column(db.String(100))
    date = db.Column(db.String(20))
    status = db.Column(db.String(50))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))

# Authentication
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return redirect(url_for('dashboard'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        db.session.add(User(username=username, password=password))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    drivers = Driver.query.all()
    loads = Load.query.all()

    status_filter = request.args.get("status", "All")
    search_query = request.args.get("search", "")

    if status_filter != "All":
        loads = [l for l in loads if l.status == status_filter]

    if search_query:
        loads = [l for l in loads if search_query.lower() in l.pickup.lower() or search_query.lower() in l.drop.lower()]

    status_counts = Counter([l.status for l in loads])

    return render_template("dashboard.html",
                           drivers=drivers,
                           loads=loads,
                           status_counts=status_counts,
                           status_filter=status_filter,
                           search_query=search_query)

# CRUD for Drivers
@app.route('/add_driver', methods=['GET', 'POST'])
@login_required
def add_driver():
    if request.method == 'POST':
        new_driver = Driver(
            name=request.form['name'],
            truck_number=request.form['truck_number'],
            phone=request.form['phone']
        )
        db.session.add(new_driver)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_driver.html')

@app.route('/edit_driver/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def edit_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    if request.method == 'POST':
        driver.name = request.form['name']
        driver.truck_number = request.form['truck_number']
        driver.phone = request.form['phone']
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_driver.html', driver=driver)

@app.route('/delete_driver/<int:driver_id>')
@login_required
def delete_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    db.session.delete(driver)
    db.session.commit()
    return redirect(url_for('dashboard'))

# CRUD for Loads
@app.route('/add_load', methods=['GET', 'POST'])
@login_required
def add_load():
    drivers = Driver.query.all()
    if request.method == 'POST':
        new_load = Load(
            pickup=request.form['pickup'],
            drop=request.form['drop'],
            date=request.form['date'],
            status=request.form['status'],
            driver_id=request.form.get('driver_id') or None
        )
        db.session.add(new_load)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_load.html', drivers=drivers)

@app.route('/edit_load/<int:load_id>', methods=['GET', 'POST'])
@login_required
def edit_load(load_id):
    load = Load.query.get_or_404(load_id)
    drivers = Driver.query.all()
    if request.method == 'POST':
        load.pickup = request.form['pickup']
        load.drop = request.form['drop']
        load.date = request.form['date']
        load.status = request.form['status']
        load.driver_id = request.form.get('driver_id') or None
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_load.html', load=load, drivers=drivers)

@app.route('/delete_load/<int:load_id>')
@login_required
def delete_load(load_id):
    load = Load.query.get_or_404(load_id)
    db.session.delete(load)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export_loads')
def export_loads():
    # Query all load records using SQLAlchemy
    loads = Load.query.all()

    # Prepare CSV in memory
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Driver ID', 'Pickup', 'Drop', 'Date', 'Status'])  # Header row

    for load in loads:
        cw.writerow([load.id, load.driver_id, load.pickup, load.drop, load.date, load.status])

    output = si.getvalue()
    response = Response(output, mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=loads.csv"
    return response


# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
