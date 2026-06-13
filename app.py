from flask import Flask, render_template, request, redirect, session
import sqlite3

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
@app.route("/register")
def register():
    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login")
def login():
    return render_template("login.html")


# ---------- PANEL ----------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)
