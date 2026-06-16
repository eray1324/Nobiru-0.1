from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

# 1. Inicialización correcta de la app
app = Flask(__name__)
app.secret_key = "nobiru_secret_key"

# 2. Configuración unificada de Cloudinary
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# Sesión duradera por 60 días
app.permanent_session_lifetime = timedelta(days=60)

# Carpeta temporal local para procesamiento de archivos
UPLOAD_FOLDER = "static/uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 3. Conexión segura a la Base de Datos
def conectar_bd():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# 4. Creación limpia de las 5 tablas sin errores SQL
def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0
    )
    """)
    
    # Tabla de Biblioteca / Materiales
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
    
    # Tabla de Cuestionarios (Estructura dinámica de cabecera)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuestionarios(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        creador TEXT,
        fecha TEXT
    )
    """)
    
    # Tabla de Preguntas (Corregido el paréntesis roto del PDF)
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
    
    # Tabla de Historial (Alimenta el Dashboard)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS respuestas_usuarios(
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE,
        puntaje INTEGER NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabla de Reels / Videos cortos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reels (
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        url TEXT NOT NULL,
        usuario TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conexion.commit()
    conexion.close()

# Ejecutar inicializador de tablas
crear_bd()

# ==========================================
# RUTAS DE AUTENTICACIÓN Y ENTRADA
# ==========================================

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
                INSERT INTO usuarios (email, username, password, recordar)
                VALUES (%s, %s, %s, %s)
            """, (email, username, password_cifrada, recordar))
            conexion.commit()
        except Exception:
            conexion.close()
            return "Ese nombre de usuario ya existe."
            
        conexion.close()
        return redirect("/login")
    return render_template("register.html")

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

# ==========================================
# DASHBOARD REAL CON 10 RANGOS AUTOMÁTICOS
# ==========================================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/login")
        
    username = session["usuario"]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Consulta A: Contar cuestionarios reales completados en la BD
    cursor.execute("SELECT COUNT(*) FROM respuestas_usuarios WHERE usuario = %s", (username,))
    cuestionarios_completados = cursor.fetchone()[0]
    
    # Consulta B: Contar PDFs reales compartidos en la biblioteca
    cursor.execute("SELECT COUNT(*) FROM materiales WHERE usuario = %s", (username,))
    documentos_compartidos = cursor.fetchone()[0]
    
    conexion.close()
    
    # Inyectar una frase motivadora del día
    frase_hoy = "El aprendizaje es un tesoro que seguirá a su dueño a todas partes."
    
    # Algoritmo de Rangos según participación de cuestionarios
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

    return render_template(
        "dashboard.html",
        usuario=username,
        frase=frase_hoy,
        cuestionarios_completados=cuestionarios_completados,
        documentos_compartidos=documentos_compartidos,
        rango=rango,
        emoji=emoji,
        estilo_css=estilo_css
    )

# ==========================================
# SECCIÓN BIBLIOTECA (COMPARTIR Y SUBIR)
# ==========================================
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
            resultado = cloudinary.uploader.upload(archivo_pdf, resource_type="raw")
            url_pdf = resultado["secure_url"]
            
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO materiales (titulo, descripcion, autor, fecha, archivo, usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (titulo, descripcion, autor, fecha, url_pdf, session["usuario"]))
        conexion.commit()
        conexion.close()
        return redirect("/biblioteca")
        
    return render_template("subir_material.html")

# ==========================================
# CUESTIONARIOS DINÁMICOS POR TÍTULO
# ==========================================
@app.route("/cuestionarios")
def cuestionarios():
    if "usuario" not in session:
        return redirect("/login")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    # Trae los metadatos necesarios de manera limpia y ordenada
    cursor.execute("SELECT id, titulo, creador, fecha FROM cuestionarios ORDER BY id DESC")
    lista_cuestionarios = cursor.fetchall()
    conexion.close()
    
    return render_template("cuestionarios.html", cuestionarios=lista_cuestionarios)

@app.route("/crear-cuestionario", methods=["GET", "POST"])
def crear_cuestionario():
    if "usuario" not in session:
        return redirect("/login")
        
    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        creador = session["usuario"]
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        
        # Guarda la cabecera del cuestionario
        cursor.execute("""
            INSERT INTO cuestionarios (titulo, descripcion, creador, fecha)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (titulo, descripcion, creador, fecha_actual))
        cuestionario_id = cursor.fetchone()[0]
        
        # Captura las listas dinámicas enviadas desde el formulario HTML
        preguntas_texto = request.form.getlist("pregunta_texto[]")
        opciones_a = request.form.getlist("opcion_a[]")
        opciones_b = request.form.getlist("opcion_b[]")
        opciones_c = request.form.getlist("opcion_c[]")
        opciones_d = request.form.getlist("opcion_d[]")
        correctas = request.form.getlist("correcta[]")
        
        # Inserta cada pregunta vinculada al ID del cuestionario creado
        for i in range(len(preguntas_texto)):
            cursor.execute("""
                INSERT INTO preguntas (cuestionario_id, pregunta_texto, opcion_a, opcion_b, opcion_c, opcion_d, correcta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (cuestionario_id, preguntas_texto[i], opciones_a[i], opciones_b[i], opciones_c[i], opciones_d[i], correctas[i]))
            
        conexion.commit()
        conexion.close()
        return redirect("/cuestionarios")
        
    return render_template("crear_cuestionario.html")

@app.route("/responder-cuestionario/<int:cuestionario_id>", methods=["GET", "POST"])
def responder_cuestionario(cuestionario_id):
    if "usuario" not in session:
        return redirect("/login")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if request.method == "POST":
        cursor.execute("SELECT id, correcta FROM preguntas WHERE cuestionario_id = %s", (cuestionario_id,))
        preguntas_db = cursor.fetchall()
        
        puntaje = 0
        for preg in preguntas_db:
            p_id, correcta = preg
            respuesta_alumno = request.form.get(f"pregunta_{p_id}")
            if respuesta_alumno == correcta:
                puntaje += 1
                
        # Registra el intento del usuario en el historial
        cursor.execute("""
            INSERT INTO respuestas_usuarios (usuario, cuestionario_id, puntaje)
            VALUES (%s, %s, %s)
        """, (session["usuario"], cuestionario_id, puntaje))
        
        conexion.commit()
        conexion.close()
        return redirect("/dashboard") # Redirige para ver sus nuevas medallas actualizadas
        
    # GET: Carga el cuestionario de manera independiente
    cursor.execute("SELECT id, titulo, descripcion FROM cuestionarios WHERE id = %s", (cuestionario_id,))
    cuestionario = cursor.fetchone()
    
    cursor.execute("SELECT id, pregunta_texto, opcion_a, opcion_b, opcion_c, opcion_d FROM preguntas WHERE cuestionario_id = %s", (cuestionario_id,))
    preguntas_lista = cursor.fetchall()
    
    conexion.close()
    return render_template("responder_cuestionario.html", cuestionario=cuestionario, preguntas=preguntas_lista)

# ==========================================
# RUTAS RESTANTES DE CONTROL
# ==========================================
@app.route("/comunidad")
def comunidad():
    if "usuario" not in session:
        return redirect("/login")
    return render_template("comunidad.html")

@app.route("/favoritos")
def favoritos():
    if "usuario" not in session:
        return redirect("/login")
    return render_template("favoritos.html")

@app.route("/reels")
def reels():
    if "usuario" not in session:
        return redirect("/login")
        return render_template("reels.html")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    # Obtenemos todos los videos guardados en la BD para mostrarlos en el feed público
    cursor.execute("SELECT * FROM reels ORDER BY id DESC")
    lista_reels = cursor.fetchall()
    conexion.close()
    return render_template("reels.html", reels=lista_reels)

@app.route("/subir-reel", methods=["GET", "POST"])
def subir_reel():
    if "usuario" not in session:
        return redirect("/login")
        
    if request.method == "POST":
        titulo = request.form.get("titulo")
        archivo_video = request.files.get("video")
        url_video = ""
        
        if archivo_video:
            # resource_type="video" es vital para Cloudinary
            resultado = cloudinary.uploader.upload(archivo_video, resource_type="video")
            url_video = resultado["secure_url"]
            
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO reels (titulo, url, usuario, fecha)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (titulo, url_video, session["usuario"]))
        conexion.commit()
        conexion.close()
        return redirect("/reels")
        
    return render_template("subir_reel.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
