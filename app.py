from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ventassmart_secret_0727'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventasmart.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==========================================
# MODELOS DE LA BASE DE DATOS
# ==========================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    costo = db.Column(db.Float, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    inversion = db.Column(db.Float, nullable=False)
    ganancias = db.Column(db.Float, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    ingreso = db.Column(db.Float, nullable=False)
    ganancia = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# CREACIÓN AUTOMÁTICA DE TABLAS
# ==========================================
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================
@app.route('/')
@login_required
def index():
    # Calculamos los totales para que no falte ninguna variable en el HTML
    productos = Product.query.all()
    ventas = Sale.query.all()
    
    total_inventario = sum(p.cantidad for p in productos)
    total_inversion = sum(p.inversion for p in productos)
    total_ganancias = sum(v.ganancia for v in ventas)
    
    return render_template('index.html', 
                           total_inventario=total_inventario, 
                           total_inversion=total_inversion, 
                           total_ganancias=total_ganancias,
                           productos=productos,
                           ventas=ventas)

@app.route('/inventario')
@login_required
def inventario():
    productos = Product.query.all()
    return render_template('inventario.html', productos=productos)

@app.route('/ventas')
@login_required
def ventas():
    ventas_realizadas = Sale.query.all()
    return render_template('ventas.html', ventas=ventas_realizadas)

@app.route('/estadisticas')
@login_required
def estadisticas():
    return render_template('estadisticas.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El usuario ya existe')
            return redirect(url_for('registro'))
            
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)