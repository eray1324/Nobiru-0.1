from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

# 1. Inicialización de la app
app = Flask(__name__)
app.secret_key = "nobiru_secret_key"

# 2. Configuración unificada de Cloudinary
cloudinary.config(
    cloud_name="Root",
    api_key="974437519682479",
    api_secret="gpl_ojcbZcjzLO9jFa2AqWdzMrU"
)

app.permanent_session_lifetime = timedelta(days=60)

UPLOAD_FOLDER = "static/uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 3. Conexión segura a la Base de Datos
def conectar_bd():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# 4. Creación limpia de las tablas
def crear_bd():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0
    )
    """)
    
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuestionarios(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        creador TEXT,
        fecha TEXT
    )
    """)
    
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS respuestas_usuarios(
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        cuestionario_id INTEGER REFERENCES cuestionarios(id) ON DELETE CASCADE,
        puntaje INTEGER NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

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

crear_bd()

# ==========================================
# RUTAS DE AUTENTICACIÓN
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
            conexion.commit() # ¡Guardado forzado!
            conexion.close()
            return redirect("/login")
        except Exception:
            conexion.close()
            return "Ese nombre de usuario ya existe."
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
            session.permanent = "recordar" in request.form
            session["usuario"] = username
            return redirect("/dashboard")
        else:
            return "Usuario o contraseña incorrectos."
    return render_template("login.html")

# ==========================================
# DASHBOARD
# ==========================================
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect("/login")
        
    username = session["usuario"]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM respuestas_usuarios WHERE usuario = %s", (username,))
    cuestionarios_completados = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM materiales WHERE usuario = %s", (username,))
    documentos_compartidos = cursor.fetchone()[0]
    conexion.close()
    
    frase_hoy = "El aprendizaje es un tesoro que seguirá a su dueño a todas partes."
    
    # Sistema de rangos rápido
    if cuestionarios_completados >= 10:
        rango, emoji, estilo_css = "Oro", "🏅", "background: #f1c40f; color: #2c3e50;"
    elif cuestionarios_completados >= 5:
        rango, emoji, estilo_css = "Plata", "🥈", "background: #7f8c8d; color: #fff;"
    else:
        rango, emoji, estilo_css = "Bronce", "🥉", "background: #8c5233; color: #fff;"

    return render_template(
        "dashboard.html",
        usuario=username, frase=frase_hoy,
        cuestionarios_completados=cuestionarios_completados,
        documentos_compartidos=documentos_compartidos,
        rango=rango, emoji=emoji, estilo_css=estilo_css
    )

# ==========================================
# SECCIÓN BIBLIOTECA (¡FIX DE GUARDADO!)
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
        titulo = request.form.get("titulo")
        descripcion = request.form.get("descripcion")
        autor = request.form.get("autor")
        fecha = request.form.get("fecha")
        archivo_pdf = request.files.get("archivo")
        url_pdf = ""
        
        if archivo_pdf and archivo_pdf.filename != "":
            try:
                resultado = cloudinary.uploader.upload(archivo_pdf, resource_type="raw")
                url_pdf = resultado.get("secure_url")
            except Exception as e:
                return f"Error en la nube: {e}", 500
                
        try:
            conexion = conectar_bd()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO materiales (titulo, descripcion, autor, fecha, archivo, usuario)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (titulo, descripcion, autor, fecha, url_pdf, session["usuario"]))
            conexion.commit() # 🔥 CRUCIAL: Contrata el guardado en la BD cloud
            conexion.close()
            return redirect("/biblioteca")
        except Exception as e:
            return f"Error al guardar material: {e}", 500
        
    return render_template("subir_material.html")

# ==========================================
# CUESTIONARIOS Y EVALUACIONES
# ==========================================
@app.route("/cuestionarios")
def cuestionarios():
    if "usuario" not in session:
        return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
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
        
        cursor.execute("""
            INSERT INTO cuestionarios (titulo, descripcion, creador, fecha)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (titulo, descripcion, creador, fecha_actual))
        cuestionario_id = cursor.fetchone()[0]
        
        preguntas_texto = request.form.getlist("pregunta_texto[]")
        opciones_a = request.form.getlist("opcion_a[]")
        opciones_b = request.form.getlist("opcion_b[]")
        opciones_c = request.form.getlist("opcion_c[]")
        opciones_d = request.form.getlist("opcion_d[]")
        correctas = request.form.getlist("correcta[]")
        
        for i in range(len(preguntas_texto)):
            cursor.execute("""
                INSERT INTO preguntas (cuestionario_id, pregunta_texto, opcion_a, opcion_b, opcion_c, opcion_d, correcta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (cuestionario_id, preguntas_texto[i], opciones_a[i], opciones_b[i], opciones_c[i], opciones_d[i], correctas[i]))
            
        conexion.commit() # 🔥 Guarda todo el cuestionario junto con sus preguntas
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
        try:
            cursor.execute("SELECT id, correcta FROM preguntas WHERE cuestionario_id = %s", (cuestionario_id,))
            preguntas_db = cursor.fetchall()
            
            total_preguntas = len(preguntas_db)
            aciertos = 0
            
            for preg in preguntas_db:
                p_id, correcta = preg
                respuesta_alumno = request.form.get(f"pregunta_{p_id}")
                if respuesta_alumno == correcta:
                    aciertos += 1
            
            errores = total_preguntas - aciertos
            puntuacion = int((aciertos / total_preguntas) * 100) if total_preguntas > 0 else 0
                
            cursor.execute("""
                INSERT INTO respuestas_usuarios (usuario, cuestionario_id, puntaje)
                VALUES (%s, %s, %s)
            """, (session["usuario"], cuestionario_id, puntuacion))
            conexion.commit()
            conexion.close()
            
            # Muestra tu plantilla exacta de resultados
            return render_template(
                "resultado_quiz.html", 
                puntuacion=puntuacion, aciertos=aciertos, errores=errores
            )
        except Exception as e:
            conexion.close()
            return redirect("/cuestionarios")
        
    # GET
    try:
        cursor.execute("SELECT id, titulo, descripcion FROM cuestionarios WHERE id = %s", (cuestionario_id,))
        cuestionario = cursor.fetchone()
        
        cursor.execute("""
            SELECT id, pregunta_texto, opcion_a, opcion_b, opcion_c, opcion_d 
            FROM preguntas WHERE cuestionario_id = %s ORDER BY id ASC
        """, (cuestionario_id,))
        preguntas_lista = cursor.fetchall()
        conexion.close()
        
        return render_template("responder_quiz.html", cuestionario=cuestionario, preguntas=preguntas_lista)
    except Exception:
        conexion.close()
        return redirect("/cuestionarios")

# ==========================================
# SECCIÓN VIDEOS (TIPO YOUTUBE - ¡MÁXIMA ESTABILIDAD!)
# ==========================================
@app.route("/reels")
def reels():
    if "usuario" not in session:
        return redirect("/login")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, titulo, url, usuario, fecha FROM reels ORDER BY id DESC")
    lista_videos = cursor.fetchall()
    conexion.close()
    return render_template("reels.html", reels=lista_videos)

@app.route("/subir-reel", methods=["GET", "POST"])
def subir_reel():
    if "usuario" not in session:
        return redirect("/login")
        
    if request.method == "POST":
        titulo = request.form.get("titulo")
        url_externa = request.form.get("url")
        descripcion = request.form.get("descripcion", "Sin descripción")
        
        if titulo and url_externa:
            try:
                conexion = conectar_bd()
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO reels (titulo, url, usuario, fecha)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (titulo, url_externa, descripcion))
                conexion.commit() # 🔥 Guarda el link educativo para siempre
                conexion.close()
                return redirect("/reels")
            except Exception as e:
                return f"Error al guardar video: {e}", 500
    return render_template("subir_reel.html")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
