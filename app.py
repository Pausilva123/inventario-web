from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images/productos'

# Asegurarse de que la carpeta exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Conexión a SQLite y creación de tabla
def init_db():
    with sqlite3.connect('inventario.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio REAL NOT NULL,
                imagen TEXT
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def index():
    return redirect(url_for('registrar_producto'))

@app.route('/registrar', methods=['GET', 'POST'])
def registrar_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])

        imagen = request.files['imagen']
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagen_path = f'static/images/productos/{filename}'

        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO productos (nombre, cantidad, precio, imagen) VALUES (?, ?, ?, ?)",
                           (nombre, cantidad, precio, imagen_path))
            conn.commit()

        return redirect(url_for('registrar_producto'))

    return render_template('registrar_producto.html')

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/entradas', methods=['GET', 'POST'])
def registrar_entrada():
    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad = int(request.form['cantidad'])
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE id = ?", (cantidad, producto_id))
            conn.commit()
        return redirect(url_for('registrar_entrada'))
    return render_template('entradas.html')

@app.route('/salidas', methods=['GET', 'POST'])
def registrar_salida():
    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad = int(request.form['cantidad'])
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE productos SET cantidad = cantidad - ? WHERE id = ?", (cantidad, producto_id))
            conn.commit()
        return redirect(url_for('registrar_salida'))
    return render_template('salidas.html')

@app.route('/alertas')
def alertas_stock_bajo():
    with sqlite3.connect('inventario.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE cantidad <= 5")
        productos = cursor.fetchall()
    return render_template('alertas.html', productos=productos)

from flask import send_file
import pandas as pd
from fpdf import FPDF

@app.route('/reporte', methods=['GET'])
def reporte():
    return render_template('reporte.html')

@app.route('/reporte/excel', methods=['POST'])
def reporte_excel():
    with sqlite3.connect('inventario.db') as conn:
        df = pd.read_sql_query("SELECT * FROM productos", conn)
    path = 'reportes/reporte_inventario.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route('/reporte/pdf', methods=['POST'])
def reporte_pdf():
    with sqlite3.connect('inventario.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Inventario", ln=True, align='C')
    pdf.ln(10)

    for p in productos:
        linea = f"ID: {p[0]} - Nombre: {p[1]} - Cantidad: {p[2]} - Precio: ${p[3]}"
        pdf.cell(200, 10, txt=linea, ln=True)

    path = "reportes/reporte_inventario.pdf"
    pdf.output(path)
    return send_file(path, as_attachment=True)

from flask import session, flash

app.secret_key = 'clave-secreta-paula'

# Crear tabla de usuarios
def init_user_db():
    with sqlite3.connect('inventario.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

init_user_db()

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)", (nombre, email, password))
                conn.commit()
                flash("Usuario registrado correctamente", "success")
                return redirect(url_for('login'))
            except:
                flash("El correo ya está registrado", "danger")
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM usuarios WHERE email = ? AND password = ?", (email, password))
            usuario = cursor.fetchone()
            if usuario:
                session['usuario'] = usuario[0]
                return redirect(url_for('bienvenida'))
            else:
                flash("Credenciales incorrectas", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/bienvenida')
def bienvenida():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('bienvenida.html')

@app.route('/factura', methods=['GET', 'POST'])
def generar_factura():
    if request.method == 'POST':
        cliente = request.form['cliente']
        items = []
        with sqlite3.connect('inventario.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos")
            productos = cursor.fetchall()

            for producto in productos:
                pid = producto[0]
                checkbox = request.form.get(f'producto_{pid}')
                cantidad = request.form.get(f'cantidad_{pid}')
                if checkbox and cantidad and cantidad.isdigit():
                    cantidad = int(cantidad)
                    subtotal = cantidad * producto[3]
                    items.append((producto[1], cantidad, producto[3], subtotal))

        total = sum(item[3] for item in items)

        # Crear PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Factura de Venta", ln=True, align='C')
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Cliente: {cliente}", ln=True)
        pdf.ln(5)

        for item in items:
            nombre, cant, precio, subtotal = item
            linea = f"{nombre} - {cant} x ${precio:.2f} = ${subtotal:.2f}"
            pdf.cell(200, 10, txt=linea, ln=True)

        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Total: ${total:.2f}", ln=True)

        path = "reportes/factura_cliente.pdf"
        pdf.output(path)
        return send_file(path, as_attachment=True)

    with sqlite3.connect('inventario.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
    return render_template('factura.html', productos=productos)

from functools import wraps

def login_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorado
