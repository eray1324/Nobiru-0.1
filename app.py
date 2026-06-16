from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import psycopg2
import os
import random
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "nobiru_secret_key"
app.permanent_session_lifetime = timedelta(days=60)

# Configuración correcta de Cloudinary
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# Conexión limpia a PostgreSQL
def conectar_bd():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# Creación automática de todas las tablas necesarias
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
    
    # 3. Tabla de Comunidad (Preguntas y respuestas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comunidad(
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        contenido TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'pregunta' o 'respuesta'
        referencia_id INTEGER DEFAULT 0 -- ID de la pregunta si es una respuesta
    )
    """)
    
    # 4. Tabla de Reels (Videos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reels(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        url TEXT NOT NULL,
        categoria TEXT NOT NULL,
        usuario TEXT NOT NULL
    )
    """)

    # 5. Tabla de Favoritos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favoritos(
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        elemento_id INTEGER NOT NULL,
        tipo TEXT NOT NULL -- 'material', 'reel', 'cuestionario'
    )
    """)
    
    conexion.commit()
    conexion.close()

# Inicializamos las tablas al arrancar la app
crear_bd()

# Frases motivadoras organizadas por día simulado
FRASES = [
    "El esfuerzo de hoy es el éxito de mañana.",
    "Cada pregunta resuelta te acerca a tu meta.",
    "Aprender es avanzar.",
    "La constancia supera al talento.",
    "Nunca subestimes una hora de estudio.",
    "Tu futuro comienza con lo que haces hoy.",
    "La disciplina vence a la motivación."
]

# RUTA INICIO (Splash)
@app.route("/")
def inicio():
    return render_template("splash.html")

# VERIFICAR SESIÓN
@app.route("/verificar")
def verificar():
    if "usuario" in session:
        return redirect("/dashboard")
    return redirect("/login")

# REGISTRO DE USUARIOS
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        password_cifrada = generate_password_hash(password)
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (email, username, password, recordar) VALUES (%s, %s, %s, %s)",
                (email, username, password_cifrada, 0)
            )
            conexion.commit()
            conexion.close()
            return redirect("/login")
        except:
            conexion.close()
            return "Ese nombre de usuario ya existe."
    return render_template("register.html")

# LOGIN
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
            if "recordar" in request.form:
                session.permanent = True
            else:
                session.permanent = False
            session["usuario"] = username
            return redirect("/dashboard")
        else:
            return "Usuario o contraseña incorrectos."
    return render_template("login.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/login")
    
    # Selección de frase aleatoria del día
    frase_hoy = random.choice(FRASES)
    return render_template("dashboard.html", usuario=session["usuario"], frase=frase_hoy)

# BIBLIOTECA (SUBIR Y MOSTRAR)
@app.route("/biblioteca")
def biblioteca():
    if "usuario" not in session:
        return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM materiales ORDER BY id DESC")
    materiales = cursor.fetchall()
    conexion.close()
    return render_template("biblioteca.html", materiales=materiales)

@app.route("/subir-material", methods=["GET", "POST"])
def subir_material():
    if "usuario" not in session:
        return redirect("/login")
    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        autor = request.form["autor"]
        fecha = request.form["fecha"]
        archivo_pdf = request.files["archivo"]
        
        url_pdf = ""
        if archivo_pdf:
            # Subida directa y segura a Cloudinary sin tocar el disco duro de Render
            resultado = cloudinary.uploader.upload(archivo_pdf, resource_type="raw")
            url_pdf = resultado["secure_url"]
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO materiales (titulo, descripcion, autor, fecha, archivo, usuario) VALUES (%s, %s, %s, %s, %s, %s)",
            (titulo, descripcion, autor, fecha, url_pdf, session["usuario"])
        )
        conexion.commit()
        conexion.close()
        return redirect("/biblioteca")
    return render_template("subir_material.html")

# COMUNIDAD (PREGUNTAS Y RESPUESTAS)
@app.route("/comunidad", methods=["GET", "POST"])
def comunidad():
    if "usuario" not in session:
        return redirect("/login")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if request.method == "POST":
        contenido = request.form["contenido"]
        tipo = request.form["tipo"] # 'pregunta' o 'respuesta'
        referencia_id = request.form.get("referencia_id", 0)
        
        cursor.execute(
            "INSERT INTO comunidad (usuario, contenido, tipo, referencia_id) VALUES (%s, %s, %s, %s)",
            (session["usuario"], contenido, tipo, referencia_id)
        )
        conexion.commit()
        
    # Obtener preguntas y respuestas de la base de datos
    cursor.execute("SELECT * FROM comunidad WHERE tipo = 'pregunta' ORDER BY id DESC")
    preguntas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM comunidad WHERE tipo = 'respuesta' ORDER BY id ASC")
    respuestas = cursor.fetchall()
    
    conexion.close()
    return render_template("comunidad.html", preguntas=preguntas, respuestas=respuestas)

# CUESTIONARIOS (CON DEMO DE 10 PREGUNTAS)
@app.route("/cuestionarios", methods=["GET", "POST"])
def cuestionarios():
    if "usuario" not in session:
        return redirect("/login")
        
    # Datos en duro de las 10 preguntas de demostración solicitadas
    preguntas_quiz = [
        {"id": 1, "p": "¿Cuánto es 5 + 7?", "a": "10", "b": "12", "c": "14", "correcta": "b"},
        {"id": 2, "p": "¿Cuál es el río más largo del mundo?", "a": "Amazonas", "b": "Nilo", "c": "Misuri", "correcta": "a"},
        {"id": 3, "p": "¿Qué gas respiramos principalmente?", "a": "Oxígeno", "b": "Nitrógeno", "c": "Dióxido de carbono", "correcta": "a"},
        {"id": 4, "p": "¿En qué año se descubrió América?", "a": "1492", "b": "1582", "c": "1392", "correcta": "a"},
        {"id": 5, "p": "¿Cuál es el planeta más cercano al Sol?", "a": "Venus", "b": "Marte", "c": "Mercurio", "correcta": "c"},
        {"id": 6, "p": "¿Qué idioma se habla en Brasil?", "a": "Español", "b": "Portugués", "c": "Inglés", "correcta": "b"},
        {"id": 7, "p": "¿Cuál es la capital de Francia?", "a": "París", "b": "Roma", "c": "Madrid", "correcta": "a"},
        {"id": 8, "p": "¿Cuántos huesos tiene el cuerpo humano adulto?", "a": "206", "b": "300", "c": "150", "correcta": "a"},
        {"id": 9, "p": "¿Qué elemento químico tiene el símbolo 'H'?", "a": "Helio", "b": "Hierro", "c": "Hidrógeno", "correcta": "c"},
        {"id": 10, "p": "¿Cuál es el resultado de 9 x 8?", "a": "72", "b": "81", "c": "64", "correcta": "a"}
    ]
    
    if request.method == "POST":
        aciertos = 0
        errores = 0
        for q in preguntas_quiz:
            respuesta_usuario = request.form.get(f"pregunta_{q['id']}")
            if respuesta_usuario == q['correcta']:
                aciertos += 1
            else:
                errores += 1
        puntuacion = aciertos * 10
        return render_template("resultado_quiz.html", aciertos=aciertos, errores=errores, puntuacion=puntuacion)
        
    return render_template("cuestionarios.html", preguntas=preguntas_quiz)

# REELS (SUBIR VIDEOS CORTOS)
@app.route("/reels", methods=["GET", "POST"])
def reels():
    if "usuario" not in session:
        return redirect("/login")
        
    if request.method == "POST":
        titulo = request.form["titulo"]
        categoria = request.form["categoria"]
        archivo_video = request.files["video"]
        
        url_video = ""
        if archivo_video:
            # Subida de video optimizada a Cloudinary
            resultado = cloudinary.uploader.upload(archivo_video, resource_type="video")
            url_video = resultado["secure_url"]
            
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO reels (titulo, url, categoria, usuario) VALUES (%s, %s, %s, %s)",
            (titulo, url_video, categoria, session["usuario"])
        )
        conexion.commit()
        conexion.close()
        return redirect("/reels")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM reels ORDER BY id DESC")
    todos_reels = cursor.fetchall()
    conexion.close()
    
    return render_template("reels.html", reels=todos_reels)

# FAVORITOS (AGREGAR Y MOSTRAR)
@app.route("/guardar-favorito/<tipo>/<int:elemento_id>")
def guardar_favorito(tipo, elemento_id):
    if "usuario" not in session:
        return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO favoritos (usuario, elemento_id, tipo) VALUES (%s, %s, %s)",
        (session["usuario"], elemento_id, tipo)
    )
    conexion.commit()
    conexion.close()
    return redirect(f"/{tipo if tipo != 'material' else 'biblioteca'}")

@app.route("/favoritos")
def favoritos():
    if "usuario" not in session:
        return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Obtener los IDs guardados por este usuario concreto
    cursor.execute("SELECT elemento_id FROM favoritos WHERE usuario = %s AND tipo = 'material'", (session["usuario"],))
    fav_materiales_ids = [r[0] for r in cursor.fetchall()]
    
    materiales_favoritos = []
    if fav_materiales_ids:
        cursor.execute("SELECT * FROM materiales WHERE id IN %s", (tuple(fav_materiales_ids),))
        materiales_favoritos = cursor.fetchall()
        
    conexion.close()
    return render_template("favoritos.html", materiales=materiales_favoritos)

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
