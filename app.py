from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "nobiru_secret_key"


# ---------- CREAR BASE DE DATOS ----------
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

    conexion.commit()
    conexion.close()


crear_bd()


# ---------- PÁGINA PRINCIPAL ----------
@app.route("/")
def inicio():
    return render_template("index.html")


# ---------- REGISTRO ----------
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
    
# ---------- LOGIN ----------
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

            session["usuario"] = username

            return redirect("/dashboard")

        else:

            return "Usuario o contraseña incorrectos."

    return render_template("login.html")
    
# ---------- PANEL ----------
@app.route("/dashboard")
def dashboard():

    if "usuario" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        usuario=session["usuario"]
    )


if __name__ == "__main__":
    app.run(debug=True)
