from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_ventasmart'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventasmart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Modelos de Base de Datos
class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(150), unique=True, nullable=False)
  password = db.Column(db.String(150), nullable=False)


class Product(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  nombre = db.Column(db.String(100), nullable=False)
  costo_paquete = db.Column(db.Float, nullable=False)
  costo_unitario = db.Column(db.Float, nullable=False)
  precio = db.Column(db.Float, nullable=False)
  cantidad = db.Column(db.Integer, nullable=False)
  inversion = db.Column(db.Float, nullable=False)
  ganancias = db.Column(db.Float, nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Sale(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  producto_nombre = db.Column(db.String(100), nullable=False)
  cantidad = db.Column(db.Integer, nullable=False)
  ingreso = db.Column(db.Float, nullable=False)
  ganancia = db.Column(db.Float, nullable=False)
  fecha = db.Column(db.DateTime, default=datetime.utcnow)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# BORRA Y CREA LAS TABLAS NUEVAS DESDE CÓDIGO
with app.app_context():
  db.drop_all()
  db.create_all()


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


# Rutas de Autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
      login_user(user)
      return redirect(url_for('index'))
    flash('Usuario o contraseña incorrectos')
  return render_template('login.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    user_exist = User.query.filter_by(username=username).first()
    if user_exist:
      flash('El usuario ya existe')
      return redirect(url_for('registro'))
    hashed_password = generate_password_hash(password, method='scrypt')
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))
  return render_template('registro.html')


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))


# Dashboard / Inicio
@app.route('/')
@login_required
def index():
  productos = Product.query.filter_by(user_id=current_user.id).all()

  total_inversion = sum(p.inversion for p in productos)
  total_productos = len(productos)
  productos_disponibles = sum(p.cantidad for p in productos)

  ventas = Sale.query.filter_by(user_id=current_user.id).all()
  total_ganancias = sum(v.ganancia for v in ventas)

  return render_template(
      'index.html',
      total_inversion=total_inversion,
      total_ganancias=total_ganancias,
      total_productos=total_productos,
      productos_disponibles=productos_disponibles,
  )


# Inventario
@app.route('/inventario', methods=['GET', 'POST'])
@login_required
def inventario():
  if request.method == 'POST':
    nombre = request.form.get('nombre')
    costo_paquete = float(request.form.get('costo'))
    precio = float(request.form.get('precio'))
    cantidad = int(request.form.get('cantidad'))

    # Cálculo exacto por pieza (Ej: 158.80 / 25 = 6.35)
    costo_unitario = (
        round(costo_paquete / cantidad, 2) if cantidad > 0 else costo_paquete
    )
    inversion = round(
        costo_paquete, 2
    )  # La inversión total es el costo del paquete
    ganancias = round(
        (precio * cantidad) - costo_paquete, 2
    )  # Ganancia total esperada

    nuevo_producto = Product(
        nombre=nombre,
        costo_paquete=costo_paquete,
        costo_unitario=costo_unitario,
        precio=precio,
        cantidad=cantidad,
        inversion=inversion,
        ganancias=ganancias,
        user_id=current_user.id,
    )
    db.session.add(nuevo_producto)
    db.session.commit()
    return redirect(url_for('inventario'))

  productos = Product.query.filter_by(user_id=current_user.id).all()
  return render_template('inventario.html', productos=productos)


# Editar Producto
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
  producto = Product.query.get_or_404(id)
  if producto.user_id != current_user.id:
    return redirect(url_for('inventario'))

  if request.method == 'POST':
    producto.nombre = request.form.get('nombre')
    producto.costo_paquete = float(request.form.get('costo'))
    producto.precio = float(request.form.get('precio'))
    producto.cantidad = int(request.form.get('cantidad'))

    producto.costo_unitario = (
        round(producto.costo_paquete / producto.cantidad, 2)
        if producto.cantidad > 0
        else producto.costo_paquete
    )
    producto.inversion = round(producto.costo_paquete, 2)
    producto.ganancias = round(
        (producto.precio * producto.cantidad) - producto.costo_paquete, 2
    )

    db.session.commit()
    return redirect(url_for('inventario'))

  return render_template('editar.html', producto=producto)


# Eliminar Producto
@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
  producto = Product.query.get_or_404(id)
  if producto.user_id == current_user.id:
    db.session.delete(producto)
    db.session.commit()
  return redirect(url_for('inventario'))


# Ventas / Punto de Venta
@app.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
  if request.method == 'POST':
    producto_id = request.form.get('producto_id')
    cantidad_vendida = int(request.form.get('cantidad'))

    producto = Product.query.get_or_404(producto_id)
    if producto.user_id != current_user.id:
      flash('No autorizado')
      return redirect(url_for('ventas'))

    if producto.cantidad >= cantidad_vendida:
      ingreso = round(producto.precio * cantidad_vendida, 2)
      costo_total_lote = producto.costo_unitario * cantidad_vendida
      ganancia = round(ingreso - costo_total_lote, 2)

      producto.cantidad -= cantidad_vendida

      nueva_venta = Sale(
          producto_nombre=producto.nombre,
          cantidad=cantidad_vendida,
          ingreso=ingreso,
          ganancia=ganancia,
          fecha=datetime.now(),
          user_id=current_user.id,
      )
      db.session.add(nueva_venta)
      db.session.commit()
      flash('Venta registrada con éxito')
    else:
      flash('No hay suficiente stock disponible')

    return redirect(url_for('ventas'))

  productos = Product.query.filter_by(user_id=current_user.id).all()
  ventas_realizadas = Sale.query.filter_by(user_id=current_user.id).all()
  return render_template(
      'ventas.html', productos=productos, ventas=ventas_realizadas
  )

# Estadísticas
@app.route('/estadisticas')
@login_required
def estadisticas():
  ventas = Sale.query.filter_by(user_id=current_user.id).all()

  ganancia_diaria = round(sum(v.ganancia for v in ventas), 2)
  ganancia_semanal = round(sum(v.ganancia for v in ventas), 2)
  ganancia_mensual = round(sum(v.ganancia for v in ventas), 2)

  # Calculamos el ingreso total de todas las ventas realizadas
  ingreso_total = round(sum(v.ingreso for v in ventas), 2)

  producto_rentable = None
  if ventas:
    from collections import defaultdict

    rentabilidad_productos = defaultdict(float)
    for v in ventas:
      rentabilidad_productos[v.producto_nombre] += v.ganancia

    mejor_nombre = max(
        rentabilidad_productos, key=rentabilidad_productos.get
    )
    mejor_ganancia = round(rentabilidad_productos[mejor_nombre], 2)

    class ProductoRentableMock:

      def __init__(self, nombre, ganancias):
        self.nombre = nombre
        self.ganancias = ganancias

    producto_rentable = ProductoRentableMock(mejor_nombre, mejor_ganancia)

  return render_template(
      'estadisticas.html',
      ganancia_diaria=ganancia_diaria,
      ganancia_semanal=ganancia_semanal,
      ganancia_mensual=ganancia_mensual,
      ingreso_total=ingreso_total,
      producto_rentable=producto_rentable,
  )

if __name__ == '__main__':
  app.run(debug=True)