from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

app = Flask(__name__) # Corrección de sintaxis
app.secret_key = "nobiru_secret_key"

# Configuración Cloudinary
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

app.permanent_session_lifetime = timedelta(days=60)

def conectar_bd():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# --- CORRECCIÓN: Tablas con valores 0 numéricos ---
def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios(id SERIAL PRIMARY KEY, email TEXT NOT NULL, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, recordar INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS materiales(id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT, autor TEXT, fecha TEXT, archivo TEXT, usuario TEXT, descargas INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cuestionarios(id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT, creador TEXT, fecha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS preguntas(id SERIAL PRIMARY KEY, cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE, pregunta_texto TEXT NOT NULL, opcion_a TEXT NOT NULL, opcion_b TEXT NOT NULL, opcion_c TEXT NOT NULL, opcion_d TEXT NOT NULL, correcta TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS respuestas_usuarios(id SERIAL PRIMARY KEY, usuario TEXT NOT NULL, cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE, puntaje INTEGER NOT NULL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conexion.commit()
    conexion.close()

crear_bd()

# --- Lógica del Dashboard y Medallas ---
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session: return redirect("/login")
    username = session["usuario"]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM respuestas_usuarios WHERE usuario = %s", (username,))
    cuestionarios_completados = cursor.fetchone()[0]
    
    # Lógica de niveles (puedes añadir más niveles aquí)
    if cuestionarios_completados >= 10: rango, emoji = "Oro", "🏅"
    elif cuestionarios_completados >= 5: rango, emoji = "Plata", "🥈"
    else: rango, emoji = "Bronce", "🥉"
    
    conexion.close()
    return render_template("dashboard.html", usuario=username, cuestionarios_completados=cuestionarios_completados, rango=rango, emoji=emoji)

# (Asegúrate de implementar las rutas de /subir-material y /cuestionarios como se discutió anteriormente)
