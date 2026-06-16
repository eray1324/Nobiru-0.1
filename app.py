from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

# 1. Configuración Inicial
app = Flask(__name__)
app.secret_key = "nobiru_secret_key"
app.permanent_session_lifetime = timedelta(days=60)

# Configuración Cloudinary
cloudinary.config(
    cloud_name="Root",
    api_key="974437519682479",
    api_secret="gpl_ojcbZcjzLO9jFa2AqWdzMrU"
)

# Configuración de carpetas
UPLOAD_FOLDER = "static/uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 2. Conexión y Creación de Tablas
def conectar_bd():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Crear tablas si no existen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(id SERIAL PRIMARY KEY, email TEXT, username TEXT UNIQUE, password TEXT, recordar INTEGER);
    CREATE TABLE IF NOT EXISTS materiales(id SERIAL PRIMARY KEY, titulo TEXT, descripcion TEXT, autor TEXT, fecha TEXT, archivo TEXT, usuario TEXT, descargas INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS cuestionarios(id SERIAL PRIMARY KEY, titulo TEXT, descripcion TEXT, creador TEXT, fecha TEXT);
    CREATE TABLE IF NOT EXISTS preguntas(id SERIAL PRIMARY KEY, cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE, pregunta_texto TEXT, opcion_a TEXT, opcion_b TEXT, opcion_c TEXT, opcion_d TEXT, correcta TEXT);
    CREATE TABLE IF NOT EXISTS respuestas_usuarios(id SERIAL PRIMARY KEY, usuario TEXT, cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE, puntaje INTEGER, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS reels(id SERIAL PRIMARY KEY, titulo TEXT, url TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS comunidad(id SERIAL PRIMARY KEY, usuario TEXT, comentario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)
    
    conexion.commit()
    conexion.close()

crear_bd()

# 3. Rutas de Autenticación
@app.route("/")
def inicio(): return render_template("splash.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        usuario = cursor.fetchone()
        conexion.close()
        if usuario and check_password_hash(usuario[3], password):
            session["usuario"] = username
            return redirect("/dashboard")
        return "Usuario o contraseña incorrectos."
    return render_template("login.html")

# 4. Dashboard
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session: return redirect("/login")
    return render_template("dashboard.html", usuario=session["usuario"])

# 5. Biblioteca
@app.route("/biblioteca")
def biblioteca():
    if "usuario" not in session: return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM materiales ORDER BY id DESC")
    materiales = cursor.fetchall()
    conexion.close()
    return render_template("biblioteca.html", materiales=materiales)

@app.route("/subir-material", methods=["GET", "POST"])
def subir_material():
    if "usuario" not in session: return redirect("/login")
    if request.method == "POST":
        titulo, desc, autor, fecha = request.form["titulo"], request.form["descripcion"], request.form["autor"], request.form["fecha"]
        archivo = request.files.get("archivo")
        url_pdf = ""
        if archivo:
            res = cloudinary.uploader.upload(archivo, resource_type="raw")
            url_pdf = res["secure_url"]
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO materiales (titulo, descripcion, autor, fecha, archivo, usuario) VALUES (%s, %s, %s, %s, %s, %s)",
                       (titulo, desc, autor, fecha, url_pdf, session["usuario"]))
        conexion.commit()
        conexion.close()
        return redirect("/biblioteca")
    return render_template("subir_material.html")

# 6. Reels
@app.route("/reels")
def reels():
    if "usuario" not in session: return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM reels ORDER BY id DESC")
    lista = cursor.fetchall()
    conexion.close()
    return render_template("reels.html", reels=lista)

@app.route("/subir-reel", methods=["POST"])
def subir_reel():
    if "usuario" not in session: return redirect("/login")
    titulo, url = request.form["titulo"], request.form["url"]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO reels (titulo, url, usuario) VALUES (%s, %s, %s)", (titulo, url, session["usuario"]))
    conexion.commit()
    conexion.close()
    return redirect("/reels")

# 7. Comunidad
@app.route("/comunidad", methods=["GET", "POST"])
def comunidad():
    if "usuario" not in session: return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    if request.method == "POST":
        comentario = request.form["comentario"]
        cursor.execute("INSERT INTO comunidad (usuario, comentario) VALUES (%s, %s)", (session["usuario"], comentario))
        conexion.commit()
    cursor.execute("SELECT usuario, comentario, fecha FROM comunidad ORDER BY id DESC")
    lista = cursor.fetchall()
    conexion.close()
    return render_template("comunidad.html", comentarios=lista)

# 8. Favoritos
@app.route("/favoritos")
def favoritos():
    if "usuario" not in session: return redirect("/login")
    return render_template("favoritos.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
