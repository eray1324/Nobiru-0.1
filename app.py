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
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ==========================
# CREAR TABLAS (Estructura Completa para Nobiru)
# ==========================
def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0
    )
    """)
    
    # 2. Tabla de Materiales (Biblioteca)
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
    
    # 3. Tabla de Cuestionarios (Cabecera)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuestionarios(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        creador TEXT,
        fecha TEXT
    )
    """)
    
    # 4. Tabla de Preguntas vinculadas a los Cuestionarios
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
    
    # 5. Tabla de Historial de Respuestas (Para las estadísticas del Dashboard)
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
# DASHBOARD DINÁMICO CON SISTEMA DE INSIGNIAS
# ==========================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/login")
        
    username = session["usuario"]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # A. Contar Cuestionarios Respondidos por este alumno
    cursor.execute("SELECT COUNT(*) FROM respuestas_usuarios WHERE usuario = %s", (username,))
    cuestionarios_completados = cursor.fetchone()[0]
    
    # B. Contar Materiales que ha compartido en la biblioteca
    cursor.execute("SELECT COUNT(*) FROM materiales WHERE usuario = %s", (username,))
    documentos_compartidos = cursor.fetchone()[0]
    
    conexion.close()
    
    # REGLAS DEL JUEGO: Sistema de evolución de Insignias (10 Niveles)
    if cuestionarios_completados >= 45:
        rango, emoji, estilo_css = "Obsidiana", "🖤", "background: #2d3436; border: 4px solid #a29bfe; color: #fff;"
    elif cuestionarios_completados >= 40:
        rango, emoji, estilo_css = "Amatista", "🔮", "background: #6c5ce7; border: 4px solid #a29bfe; color: #fff;"
    elif cuestionarios_completados >= 35:
        rango, emoji, estilo_css = "Zafiro", "🔷", "background: #0984e3; border: 4px solid #74b9ff; color: #fff;"
    elif cuestionarios_completados >= 30:
        rango, emoji, estilo_css = "Esmeralda", "💚", "background: #00b894; border: 4px solid #55efc4; color: #fff;"
    elif cuestionarios_completados >= 25:
        rango, emoji, estilo_css = "Rubí", "🔻", "background: #d63031; border: 4px solid #ff7675; color: #fff;"
    elif cuestionarios_completados >= 20:
        rango, emoji, estilo_css = "Diamante", "💎", "background: #74b9ff; border: 4px solid #dff9fb; color: #fff;"
    elif cuestionarios_completados >= 15:
        rango, emoji, estilo_css = "Platino", "✨", "background: #dfe6e9; border: 4px solid #b2bec3; color: #2d3436;"
    elif cuestionarios_completados >= 10:
        rango, emoji, estilo_css = "Oro", "🏅", "background: #f1c40f; border: 4px solid #fff; color: #2c3e50; box-shadow: 0 0 15px #f1c40f;"
    elif cuestionarios_completados >= 5:
        rango, emoji, estilo_css = "Plata", "🥈", "background: #7f8c8d; border: 4px solid #dcdde1; color: #fff;"
    else:
        rango, emoji, estilo_css = "Bronce", "🥉", "background: #8c5233; border: 4px solid #b2bec3; color: #fff;"

    # Mandamos las variables vivas al HTML
    return render_template(
        "dashboard.html", 
        usuario=username,
        cuestionarios_completados=cuestionarios_completados,
        documentos_compartidos=documentos_compartidos,
        rango=rango,
        emoji=emoji,
        estilo_css=estilo_css
    )
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
