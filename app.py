from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

app = Flask(__name__) # Corregido la sintaxis de inicialización de Flask
app.secret_key = "nobiru_secret_key"

# ==========================
# CONFIGURACIÓN CLOUDINARY
# ==========================
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# Mantener sesión viva por 60 días
app.permanent_session_lifetime = timedelta(days=60)

# Carpeta local temporal para PDFs
UPLOAD_FOLDER = "static/uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ==========================
# CONEXIÓN A POSTGRESQL (Corregido)
# ==========================
def conectar_bd():
    # Se pasa la URL del entorno correctamente dentro de los parámetros de conexión
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ==========================
# CREAR TABLAS (Estructura de Datos Nobiru)
# ==========================
def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Tabla de Usuarios (Corregido DEFAULT 0 con número)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0
    )
    """)
    
    # 2. Tabla de Materiales / Biblioteca (Corregido DEFAULT 0 con número)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materiales(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        autor TEXT,
        fecha TEXT,
        archivo TEXT,
        usuario TEXT,
        descargas INTEGER DEFAULT 0
    )
    """)
    
    # 3. Tabla de Cuestionarios (Cabeceras de los cuestionarios creados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuestionarios(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        creador TEXT,
        fecha TEXT
    )
    """)
    
    # 4. Tabla de Preguntas (Vinculadas a un cuestionario mediante llave foránea)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preguntas(
        id SERIAL PRIMARY KEY,
        cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE,
        pregunta_texto TEXT NOT NULL,
        opcion_a TEXT NOT NULL,
        opcion_b TEXT NOT NULL,
        opcion_c TEXT NOT NULL,
        opcion_d TEXT NOT NULL,
        correcta TEXT NOT NULL
    )
    """)
    
    # 5. Tabla de Historial de Respuestas (Registra los cuestionarios resueltos por usuario)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS respuestas_usuarios(
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE,
        puntaje INTEGER NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conexion.commit()
    conexion.close()

crear_bd()

# ==========================
# VISTAS Y RUTAS DE NAVEGACIÓN
# ==========================

@app.route("/")
def inicio():
    return render_template("splash.html")

@app.route("/verificar")
def verificar():
    if "usuario" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        password_cifrada = generate_password_hash(password)
        
        recordar = 1 if "recordar" in request.form else 0
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                INSERT INTO usuarios (email, username, password,
