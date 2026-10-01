from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ventassmart_secret_0727'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventasmart.db'

db = SQLAlchemy(app)

# CREAR LAS TABLAS AUTOMÁTICAMENTE AL ARANCAR EL SERVIDOR
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos de la Base de Datos
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    productos = Product.query.all()
    total_productos = len(productos)
    total_inversion = sum(p.inversion for p in productos)
    total_ganancias = sum(p.ganancias for p in productos)
    
    producto_estrella = max(productos, key=lambda p: p.ganancias) if productos else None
    
    return render_template('index.html', 
                           total_productos=total_productos, 
                           total_inversion=total_inversion,
                           total_ganancias=total_ganancias,
                           producto_estrella=producto_estrella)

@app.route('/inventario', methods=['GET', 'POST'])
@login_required
def inventario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        costo = float(request.form.get('costo', 0))
        precio = float(request.form.get('precio', 0))
        cantidad = int(request.form.get('cantidad', 0))
        
        inversion = costo * cantidad
        ganancias = (precio * cantidad) - inversion
        
        nuevo_producto = Product(
            nombre=nombre, 
            costo=costo, 
            precio=precio, 
            cantidad=cantidad, 
            inversion=inversion, 
            ganancias=ganancias
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return redirect(url_for('inventario'))
        
    productos = Product.query.all()
    return render_template('inventario.html', productos=productos)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    producto = Product.query.get_or_404(id)
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        producto.costo = float(request.form.get('costo', 0))
        producto.precio = float(request.form.get('precio', 0))
        producto.cantidad = int(request.form.get('cantidad', 0))
        
        producto.inversion = producto.costo * producto.cantidad
        producto.ganancias = (producto.precio * producto.cantidad) - producto.inversion
        
        db.session.commit()
        return redirect(url_for('inventario'))
        
    return render_template('editar.html', producto=producto)

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    producto = Product.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for('inventario'))

@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    productos = Product.query.all()
    historial = Sale.query.order_by(Sale.fecha.desc()).all()
    
    if request.method == 'POST':
        producto_id = int(request.form.get('producto_id'))
        cantidad_vendida = int(request.form.get('cantidad', 0))
        
        producto = Product.query.get_or_404(producto_id)
        
        if producto.cantidad >= cantidad_vendida:
            producto.cantidad -= cantidad_vendida
            producto.inversion = producto.costo * producto.cantidad
            producto.ganancias = (producto.precio * producto.cantidad) - producto.inversion
            
            # Registrar historial de venta
            ingreso_venta = producto.precio * cantidad_vendida
            ganancia_venta = (producto.precio - producto.costo) * cantidad_vendida
            
            nueva_venta = Sale(
                producto_nombre=producto.nombre,
                cantidad=cantidad_vendida,
                ingreso=ingreso_venta,
                ganancia=ganancia_venta
            )
            db.session.add(nueva_venta)
            db.session.commit()
            return redirect(url_for('ventas'))
        else:
            flash('Stock insuficiente para realizar la venta.')

    return render_template('ventas.html', productos=productos, historial=historial)

@app.route('/estadisticas')
@login_required
def estadisticas():
    ahora = datetime.utcnow()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana_inicio = ahora - timedelta(days=7)
    mes_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Cálculos por periodo basados en el modelo Sale
    ventas_hoy = Sale.query.filter(Sale.fecha >= hoy_inicio).all()
    ventas_semana = Sale.query.filter(Sale.fecha >= semana_inicio).all()
    ventas_mes = Sale.query.filter(Sale.fecha >= mes_inicio).all()
    
    ganancia_diaria = sum(v.ganancia for v in ventas_hoy)
    ganancia_semanal = sum(v.ganancia for v in ventas_semana)
    ganancia_mensual = sum(v.ganancia for v in ventas_mes)
    
    productos = Product.query.all()
    producto_rentable = max(productos, key=lambda p: p.ganancias) if productos else None

    return render_template('estadisticas.html', 
                           ganancia_diaria=ganancia_diaria,
                           ganancia_semanal=ganancia_semanal,
                           ganancia_mensual=ganancia_mensual,
                           producto_rentable=producto_rentable)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        flash('Credenciales inválidas')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nuevo_usuario = User(username=username, password=password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
