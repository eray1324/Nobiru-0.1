from flask import Flask

app = Flask(__name__)

@app.route("/")
def inicio():
    return "INICIO"

@app.route("/verificar")
def verificar():
    return "FUNCIONA"

if __name__ == "__main__":
    app.run(debug=True)
