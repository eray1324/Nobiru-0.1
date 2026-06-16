from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
import psycopg2
import os
import cloudinary
import cloudinary.uploader

app = Flask(__name__) # Corregido la sintaxis de inicialización de Flask [cite: 8]
app.secret_key = "nobiru_secret_key" [cite: 9]

# ==========================
# CONFIGURACIÓN CLOUDINARY
# ==========================
cloudinary.config( [cite: 12]
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"), [cite: 14]
    api_key=os.environ.get("CLOUDINARY_API_KEY"), [cite: 15]
    api_secret=os.environ.get("CLOUDINARY_API_SECRET") [cite: 16]
)

# Mantener sesión viva por 60 días [cite: 17]
app.permanent_session_lifetime = timedelta(days=60) [cite: 18]

# Carpeta local temporal para PDFs [cite: 19]
UPLOAD_FOLDER = "static/uploads/pdfs" [cite: 20]
os.makedirs(UPLOAD_FOLDER, exist_ok=True) [cite: 21]
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER [cite: 22]

# ==========================
# CONEXIÓN A POSTGRESQL (Corregido)
# ==========================
def conectar_bd(): [cite: 26]
    # Se pasa la URL del entorno correctamente dentro de los parámetros de conexión [cite: 27, 29]
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ==========================
# CREAR TABLAS (Estructura de Datos Nobiru)
# ==========================
def crear_bd(): [cite: 33]
    conexion = conectar_bd() [cite: 34]
    cursor = conexion.cursor() [cite: 35]
    
    # 1. Tabla de Usuarios (Corregido DEFAULT 0 con número) [cite: 37, 42]
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0
    )
    """)
    
    # 2. Tabla de Materiales / Biblioteca (Corregido DEFAULT 0 con número) [cite: 46, 55]
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
    
    conexion.commit() [cite: 57]
    conexion.close() [cite: 58]

crear_bd() [cite: 59]

# ==========================
# VISTAS Y RUTAS DE NAVEGACIÓN
# ==========================

@app.route("/") [cite: 63]
def inicio(): [cite: 64]
    return render_template("splash.html") [cite: 67]

@app.route("/verificar") [cite: 72]
def verificar(): [cite: 73]
    if "usuario" in session: [cite: 74]
        return redirect("/dashboard") [cite: 75]
    return redirect("/login") [cite: 76]

@app.route("/register", methods=["GET", "POST"]) [cite: 81]
def register(): [cite: 82]
    if request.method == "POST": [cite: 83]
        email = request.form["email"] [cite: 84]
        username = request.form["username"] [cite: 85]
        password = request.form["password"] [cite: 86]
        password_cifrada = generate_password_hash(password) [cite: 87]
        
        recordar = 1 if "recordar" in request.form else 0 [cite: 89, 90]
        
        conexion = conectar_bd() [cite: 91]
        cursor = conexion.cursor() [cite: 92]
        try: [cite: 93]
            cursor.execute("""
                INSERT INTO usuarios (email, username, password, recordar)
                VALUES (%s, %s, %s, %s)
            """, (email, username, password_cifrada, recordar)) [cite: 96, 97, 98, 103, 104, 105, 106])
            conexion.commit() [cite: 107]
        except: [cite: 108]
            conexion.close() [cite: 109]
            return "Ese nombre de usuario ya existe." [cite: 110]
            
        conexion.close() [cite: 111]
        return redirect("/login") [cite: 112]
    return render_template("register.html") [cite: 113]

@app.route("/login", methods=["GET", "POST"]) [cite: 119]
def login(): [cite: 120]
    if request.method == "POST": [cite: 121]
        username = request.form["username"] [cite: 122]
        password = request.form["password"] [cite: 123]
        
        conexion = conectar_bd() [cite: 124]
        cursor = conexion.cursor() [cite: 125]
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,)) [cite: 128, 129, 130])
        usuario = cursor.fetchone() [cite: 131]
        conexion.close() [cite: 132]
        
        if usuario and check_password_hash(usuario[3], password): [cite: 133]
            if "recordar" in request.form: [cite: 134]
                session.permanent = True [cite: 135]
            else:
                session.permanent = False [cite: 137]
            session["usuario"] = username [cite: 138]
            return redirect("/dashboard") [cite: 139]
        else:
            return "Usuario o contraseña incorrectos." [cite: 141]
    return render_template("login.html") [cite: 142]

# ==========================
# DASHBOARD REAL CON MEDALLAS DINÁMICAS
# ==========================
@app.route("/dashboard") [cite: 149]
def dashboard(): [cite: 150]
    if "usuario" not in session: [cite: 151]
        return redirect("/login") [cite: 152]
        
    username = session["usuario"] [cite: 155]
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Consulta A: Contar cuántas veces ha respondido cuestionarios reales en la BD
    cursor.execute("SELECT COUNT(*) FROM respuestas_usuarios WHERE usuario = %s", (username,))
    cuestionarios_completados = cursor.fetchone()[0]
    
    # Consulta B: Contar cuántos PDFs ha compartido en la biblioteca
    cursor.execute("SELECT COUNT(*) FROM materiales WHERE usuario = %s", (username,))
    documentos_compartidos = cursor.fetchone()[0]
    
    conexion.close()
    
    # Lógica algorítmica de recompensas (10 niveles automáticos basados en participación)
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

    return render_template( [cite: 153]
        "dashboard.html", [cite: 154]
        usuario=username, [cite: 155]
        cuestionarios_completados=cuestionarios_completados,
        documentos_compartidos=documentos_compartidos,
        rango=rango,
        emoji=emoji,
        estilo_css=estilo_css
    )

# ==========================
# SECCIÓN BIBLIOTECA Y SUBIDA
# ==========================
@app.route("/biblioteca") [cite: 160]
def biblioteca(): [cite: 161]
    if "usuario" not in session: [cite: 163]
        return redirect("/login") [cite: 164]
    conexion = conectar_bd() [cite: 165]
    cursor = conexion.cursor() [cite: 166]
    cursor.execute("SELECT * FROM materiales ORDER BY id DESC") [cite: 167, 168, 169, 170]
    materiales = cursor.fetchall() [cite: 172]
    conexion.close() [cite: 173]
    return render_template("biblioteca.html", materiales=materiales) [cite: 174, 176, 177]

@app.route("/subir-material", methods=["GET", "POST"]) [cite: 182]
def subir_material(): [cite: 183]
    if "usuario" not in session: [cite: 184]
        return redirect("/login") [cite: 185]
        
    if request.method == "POST": [cite: 186]
        titulo = request.form["titulo"] [cite: 187]
        descripcion = request.form["descripcion"] [cite: 188]
        autor = request.form["autor"] [cite: 189]
        fecha = request.form["fecha"] [cite: 190]
        archivo_pdf = request.files["archivo"] [cite: 191]
        url_pdf = "" [cite: 192]
        
        if archivo_pdf: [cite: 193]
            resultado = cloudinary.uploader.upload(archivo_pdf, resource_type="raw") [cite: 194]
            url_pdf = resultado["secure_url"] [cite: 194]
            
        conexion = conectar_bd() [cite: 194]
        cursor = conexion.cursor() [cite: 194]
        cursor.execute("""
            INSERT INTO materiales (titulo, descripcion, autor, fecha, archivo, usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (titulo, descripcion, autor, fecha, url_pdf, session["usuario"])) [cite: 194]
        conexion.commit() [cite: 194]
        conexion.close() [cite: 194]
        return redirect("/biblioteca") [cite: 194]
        
    return render_template("subir_material.html") [cite: 194]

# ==========================
# SECCIÓN CUESTIONARIOS DINÁMICOS
# ==========================
@app.route("/cuestionarios") [cite: 195]
def cuestionarios(): [cite: 195]
    if "usuario" not in session: [cite: 195]
        return redirect("/login") [cite: 195]
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    # Trae únicamente los datos informativos (Título y creador) para listarlos de forma elegante 
    cursor.execute("SELECT id, titulo, creador, fecha FROM cuestionarios ORDER BY id DESC")
    lista_cuestionarios = cursor.fetchall()
    conexion.close()
    
    return render_template("cuestionarios.html", cuestionarios=lista_cuestionarios) [cite: 195]

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
        
        # Guardamos la cabecera del cuestionario y recuperamos su ID generado
        cursor.execute("""
            INSERT INTO cuestionarios (titulo, descripcion, creador, fecha)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (titulo, descripcion, creador, fecha_actual))
        cuestionario_id = cursor.fetchone()[0]
        
        # Capturamos los arreglos dinámicos de preguntas provenientes del formulario HTML
        preguntas_texto = request.form.getlist("pregunta_texto[]")
        opciones_a = request.form.getlist("opcion_a[]")
        opciones_b = request.form.getlist("opcion_b[]")
        opciones_c = request.form.getlist("opcion_c[]")
        opciones_d = request.form.getlist("opcion_d[]")
        correctas = request.form.getlist("correcta[]")
        
        # Guardamos en bucle cada una de las preguntas vinculadas a este cuestionario
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
        # Traemos la clave de respuestas correctas de la base de datos para calificar
        cursor.execute("SELECT id, correcta FROM preguntas WHERE cuestionario_id = %s", (cuestionario_id,))
        preguntas_db = cursor.fetchall()
        
        puntaje = 0
        for preg in preguntas_db:
            p_id, correcta = preg
            # Recibimos lo que seleccionó el alumno en el formulario dinámico
            respuesta_alumno = request.form.get(f"pregunta_{p_id}")
            if respuesta_alumno == correcta:
                puntaje += 1
                
        # Insertamos el intento en la tabla de historial para alimentar las estadísticas reales del Dashboard
        cursor.execute("""
            INSERT INTO respuestas_usuarios (usuario, cuestionario_id, puntaje)
            VALUES (%s, %s, %s)
        """, (session["usuario"], cuestionario_id, puntaje))
        
        conexion.commit()
        conexion.close()
        return redirect("/dashboard") # Al terminar, vuelve al inicio y ve su medalla actualizada
        
    # GET: Carga el cuestionario de forma aislada por su ID
    cursor.execute("SELECT id, titulo, descripcion FROM cuestionarios WHERE id = %s", (cuestionario_id,))
    cuestionario = cursor.fetchone()
    
    cursor.execute("SELECT id, pregunta_texto, opcion_a, opcion_b, opcion_c, opcion_d FROM preguntas WHERE cuestionario_id = %s", (cuestionario_id,))
    preguntas_lista = cursor.fetchall()
    
    conexion.close()
    return render_template("responder_cuestionario.html", cuestionario=cuestionario, preguntas=preguntas_lista)

# ==========================
# RUTAS RESTANTES DE CONTROL
# ==========================
@app.route("/comunidad") [cite: 196]
def comunidad(): [cite: 196]
    if "usuario" not in session: [cite: 196]
        return redirect("/login") [cite: 196]
    return render_template("comunidad.html") [cite: 196]

@app.route("/favoritos") [cite: 196]
def favoritos(): [cite: 196]
    if "usuario" not in session: [cite: 196]
        return redirect("/login") [cite: 196]
    return render_template("favoritos.html") [cite: 196]

@app.route("/reels") [cite: 197]
def reels(): [cite: 197]
    if "usuario" not in session: [cite: 197]
        return redirect("/login") [cite: 197]
    return render_template("reels.html") [cite: 197]

@app.route("/logout") [cite: 197]
def logout(): [cite: 197]
    session.clear() [cite: 197]
    return redirect("/login") [cite: 197]

if __name__ == "__main__": [cite: 197]
    app.run(debug=True) [cite: 197]
