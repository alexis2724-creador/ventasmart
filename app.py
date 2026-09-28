from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "ventasmart_super_secreto"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventasmart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DE BASE DE DATOS ---
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_compra = db.Column(db.Float, nullable=False)
    precio_venta = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    ventas = db.relationship('Venta', backref='producto', lazy=True, cascade="all, delete-orphan")

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)
    ingreso = db.Column(db.Float, nullable=False)
    utilidad = db.Column(db.Float, nullable=False)

# --- CREACIÓN AUTOMÁTICA DE TABLAS Y DATOS DE EJEMPLO ---
with app.app_context():
    db.create_all()
    if not Producto.query.first():
        p1 = Producto(nombre='Takis Mini', precio_compra=6.35, precio_venta=10.0, cantidad=25)
        p2 = Producto(nombre='Zumba Goma', precio_compra=3.86, precio_venta=5.0, cantidad=20)
        db.session.add_all([p1, p2])
        db.session.commit()

# --- RUTAS ---
@app.route('/')
def index():
    productos = Producto.query.all()
    ventas = Venta.query.all()
    
    capital_invertido = sum(p.precio_compra * p.cantidad for p in productos)
    ingresos_totales = sum(v.ingreso for v in ventas)
    ganancias_totales = sum(v.utilidad for v in ventas)
    
    productos_disponibles = len([p for p in productos if p.cantidad > 0])
    productos_agotados = len([p for p in productos if p.cantidad == 0])
    
    # Producto más vendido
    ventas_por_producto = {}
    for v in ventas:
        ventas_por_producto[v.producto.nombre] = ventas_por_producto.get(v.producto.nombre, 0) + v.cantidad
    
    producto_mas_vendido = max(ventas_por_producto, key=ventas_por_producto.get) if ventas_por_producto else "Ninguno"
    
    return render_template('index.html', 
                           capital_invertido=capital_invertido,
                           ingresos_totales=ingresos_totales,
                           ganancias_totales=ganancias_totales,
                           productos_disponibles=productos_disponibles,
                           productos_agotados=productos_agotados,
                           producto_mas_vendido=producto_mas_vendido)

@app.route('/inventario', methods=['GET', 'POST'])
def inventario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        compra = float(request.form['precio_compra'])
        venta = float(request.form['precio_venta'])
        cantidad = int(request.form['cantidad'])
        
        nuevo = Producto(nombre=nombre, precio_compra=compra, precio_venta=venta, cantidad=cantidad)
        db.session.add(nuevo)
        db.session.commit()
        flash('Producto agregado correctamente', 'success')
        return redirect(url_for('inventario'))
        
    productos = Producto.query.all()
    return render_template('inventario.html', productos=productos)

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado', 'danger')
    return redirect(url_for('inventario'))

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad_vendida = int(request.form['cantidad'])
        
        producto = Producto.query.get(producto_id)
        
        if producto.cantidad >= cantidad_vendida:
            ingreso = producto.precio_venta * cantidad_vendida
            utilidad = (producto.precio_venta - producto.precio_compra) * cantidad_vendida
            
            # Descontar inventario
            producto.cantidad -= cantidad_vendida
            
            # Registrar venta
            nueva_venta = Venta(producto_id=producto.id, cantidad=cantidad_vendida, ingreso=ingreso, utilidad=utilidad)
            db.session.add(nueva_venta)
            db.session.commit()
            flash('Venta registrada con éxito', 'success')
        else:
            flash('Stock insuficiente', 'error')
            
        return redirect(url_for('ventas'))
        
    productos = Producto.query.filter(Producto.cantidad > 0).all()
    historial = Venta.query.order_by(Venta.fecha.desc()).limit(10).all()
    return render_template('ventas.html', productos=productos, historial=historial)

@app.route('/reportes')
def reportes():
    ventas = Venta.query.all()
    hoy = datetime.now()
    
    ganancia_diaria = sum(v.utilidad for v in ventas if v.fecha.date() == hoy.date())
    
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    ganancia_semanal = sum(v.utilidad for v in ventas if v.fecha >= inicio_semana)
    
    ganancia_mensual = sum(v.utilidad for v in ventas if v.fecha.month == hoy.month and v.fecha.year == hoy.year)
    
    # Total vendido y rentabilidad por producto
    stats_productos = {}
    for v in ventas:
        nombre = v.producto.nombre
        if nombre not in stats_productos:
            stats_productos[nombre] = {'cantidad': 0, 'utilidad': 0}
        stats_productos[nombre]['cantidad'] += v.cantidad
        stats_productos[nombre]['utilidad'] += v.utilidad
        
    producto_rentable = max(stats_productos.items(), key=lambda x: x[1]['utilidad'])[0] if stats_productos else "Ninguno"
    
    return render_template('reportes.html',
                           ganancia_diaria=ganancia_diaria,
                           ganancia_semanal=ganancia_semanal,
                           ganancia_mensual=ganancia_mensual,
                           stats_productos=stats_productos,
                           producto_rentable=producto_rentable)

if __name__ == '__main__':
    app.run(debug=True)