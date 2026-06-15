from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "nobiru_secret_key"
UPLOAD_FOLDER = "static/uploads/pdfs"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Mantener sesión hasta 60 días
app.permanent_session_lifetime = timedelta(days=60)


# ==========================
# CREAR BASE DE DATOS
# ==========================
def crear_bd():

    conexion = sqlite3.connect("database/nobiru.db")
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recordar INTEGER DEFAULT 0

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materiales(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        autor TEXT,
        fecha TEXT,
        archivo TEXT

    )
    """)
    
    conexion.commit()
    conexion.close()


crear_bd()


# ==========================
# PÁGINA PRINCIPAL
# ==========================
@app.route("/")
def inicio():
    return render_template("splash.html")


# ==========================
# VERIFICAR SESIÓN
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

        conexion = sqlite3.connect("database/nobiru.db")
        cursor = conexion.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO usuarios
                (email, username, password, recordar)

                VALUES (?, ?, ?, ?)
                """,
                (email, username, password_cifrada, recordar)
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

        conexion = sqlite3.connect("database/nobiru.db")
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT * FROM usuarios
            WHERE username = ?
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
# CUESTIONARIOS
# ==========================
@app.route("/cuestionarios")
def cuestionarios():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("cuestionarios.html")


# ==========================
# BIBLIOTECA
# ==========================
@app.route("/biblioteca", methods=["GET", "POST"])
def biblioteca():

    if "usuario" not in session:
        return redirect("/login")

    conexion = sqlite3.connect("database/nobiru.db")
    cursor = conexion.cursor()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        autor = request.form["autor"]
        fecha = request.form["fecha"]

        cursor.execute(
            """
            INSERT INTO materiales
            (titulo, descripcion, autor, fecha)

            VALUES (?, ?, ?, ?)
            """,
            (titulo, descripcion, autor, fecha)
        )

        conexion.commit()

    cursor.execute("SELECT * FROM materiales")

    materiales = cursor.fetchall()

    conexion.close()

    return render_template(
        "biblioteca.html",
        materiales=materiales
    )

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
# REELS EDUCATIVOS
# ==========================
@app.route("/reels")
def reels():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("reels.html")
# ==========================
# CERRAR SESIÓN
# ==========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
