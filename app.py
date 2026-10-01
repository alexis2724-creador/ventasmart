from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_super_segura_para_renta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventasmart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    productos = db.relationship('Product', backref='owner', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    costo = db.Column(db.Float, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    inversion = db.Column(db.Float, nullable=False)
    ganancias = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return render_template('registro.html', error="Todos los campos son obligatorios")
        if User.query.filter_by(username=username).first():
            return render_template('registro.html', error="El usuario ya existe")
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        nuevo_usuario = User(username=username, password=hashed_password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Usuario o contraseña incorrectos")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Ruta de Inicio / Dashboard Principal
@app.route('/index')
@login_required
def index():
    productos = Product.query.filter_by(user_id=current_user.id).all()
    
    total_inversion = sum(p.inversion for p in productos)
    total_ganancias = sum(p.ganancias for p in productos)
    productos_disponibles = sum(p.cantidad for p in productos)
    
    return render_template('index.html', 
                           total_inversion=total_inversion, 
                           total_ganancias=total_ganancias,
                           productos_disponibles=productos_disponibles,
                           total_productos=len(productos))

# Ruta de Inventario y Gestión de Productos
@app.route('/inventario', methods=['GET', 'POST'])
@login_required
def inventario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        costo = float(request.form.get('costo', 0))
        precio = float(request.form.get('precio', 0))
        cantidad = int(request.form.get('cantidad', 0))
        
        inversion = costo * cantidad
        ganancias = (precio - costo) * cantidad
        
        nuevo_producto = Product(
            nombre=nombre,
            costo=costo,
            precio=precio,
            cantidad=cantidad,
            inversion=inversion,
            ganancias=ganancias,
            user_id=current_user.id
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return redirect(url_for('inventario'))
        
    productos = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('inventario.html', productos=productos)

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    producto = Product.query.get_or_404(id)
    if producto.user_id == current_user.id:
        db.session.delete(producto)
        db.session.commit()
    return redirect(url_for('inventario'))

with app.app_context():
    db.create_all()
if __name__ == '__main__':
    app.run(debug=True)
