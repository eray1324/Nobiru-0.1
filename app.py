from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "nobiru_secret_key"

# Mantener sesión 60 días
app.permanent_session_lifetime = timedelta(days=60)

# Carpeta de PDFs
UPLOAD_FOLDER = "static/uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ==========================
# CONEXIÓN A POSTGRESQL
# ==========================
def conectar_bd():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL")
    )


# ==========================
# CREAR TABLAS
# ==========================
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

    conexion.commit()
    conexion.close()


crear_bd()


# ==========================
# INICIO
# ==========================
@app.route("/")
def inicio():
    return render_template("splash.html")


# ==========================
# VERIFICAR
# ==========================
@app.route("/verificar")
def verificar():

    if "usuario" in session:
        return redirect("/dashboard")

    return redirect("/login")


# ==========================
# REGISTRO
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        password_cifrada = generate_password_hash(password)

        recordar = 0

        if "recordar" in request.form:
            recordar = 1

        conexion = conectar_bd()
        cursor = conexion.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO usuarios
                (email, username, password, recordar)

                VALUES (%s, %s, %s, %s)
                """,
                (
                    email,
                    username,
                    password_cifrada,
                    recordar
                )
            )

            conexion.commit()

        except:

            conexion.close()
            return "Ese nombre de usuario ya existe."

        conexion.close()

        return redirect("/login")

    return render_template("register.html")


# ==========================
# LOGIN
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT * FROM usuarios
            WHERE username = %s
            """,
            (username,)
        )

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


# ==========================
# DASHBOARD
# ==========================
@app.route("/dashboard")
def dashboard():

    if "usuario" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        usuario=session["usuario"]
    )


# ==========================
# BIBLIOTECA
# ==========================
@app.route("/biblioteca")
def biblioteca():

    if "usuario" not in session:
        return redirect("/login")

    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT *
        FROM materiales
        ORDER BY id DESC
    """)

    materiales = cursor.fetchall()

    conexion.close()

    return render_template(
        "biblioteca.html",
        materiales=materiales
    )


# ==========================
# SUBIR MATERIAL
# ==========================
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

        nombre_archivo = ""

        if archivo_pdf:

            nombre_archivo = secure_filename(
                archivo_pdf.filename
            )

            ruta_guardado = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nombre_archivo
            )

            archivo_pdf.save(ruta_guardado)

        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute(
            """
            INSERT INTO materiales
            (
                titulo,
                descripcion,
                autor,
                fecha,
                archivo,
                usuario
            )

            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                titulo,
                descripcion,
                autor,
                fecha,
                nombre_archivo,
                session["usuario"]
            )
        )

        conexion.commit()
        conexion.close()

        return redirect("/biblioteca")

    return render_template("subir_material.html")


# ==========================
# CUESTIONARIOS
# ==========================
@app.route("/cuestionarios")
def cuestionarios():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("cuestionarios.html")


# ==========================
# COMUNIDAD
# ==========================
@app.route("/comunidad")
def comunidad():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("comunidad.html")


# ==========================
# FAVORITOS
# ==========================
@app.route("/favoritos")
def favoritos():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("favoritos.html")


# ==========================
# REELS
# ==========================
@app.route("/reels")
def reels():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("reels.html")


# ==========================
# LOGOUT
# ==========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
