import os
import random
import sqlite3
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# La clave se lee de una variable de entorno; si no existe, se genera una aleatoria al iniciar
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24).hex()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tasks.db")


# --------------------------------
# DATABASE
# --------------------------------

def connect_db():

    return sqlite3.connect(DB_PATH)


def init_db():

    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            priority TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0
        )
    """)

    conn.commit()

    conn.close()


init_db()


# --------------------------------
# PRIORIDAD AUTOMÁTICA
# --------------------------------

def calculate_priority(due_date, today=None):
    """Alta si faltan 3 días o menos, Media si faltan 7 o menos, Baja en otro caso."""

    today = today or date.today()

    days_left = (due_date - today).days

    if days_left <= 3:
        return "Alta"

    if days_left <= 7:
        return "Media"

    return "Baja"


# --------------------------------
# TASKBOT MESSAGES
# --------------------------------

messages = [

    "🤖 Estoy analizando tus próximas tareas.",

    "📚 Organizar tu tiempo mejora tu rendimiento.",

    "🔥 Cada tarea completada es un avance importante.",

    "🚀 Tu productividad está creciendo.",

    "⏰ Detecté actividades próximas esta semana.",

    "💡 Consejo: empieza por las tareas pequeñas.",

    "📌 Mantener un horario organizado reduce el estrés.",

    "🎯 Intenta completar al menos 3 tareas hoy.",

    "🧠 La constancia diaria genera mejores resultados.",

    "✨ TaskFlow AI está monitoreando tus entregas."

]


# --------------------------------
# LOGIN
# --------------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"]

        conn = connect_db()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, password FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        # Las contraseñas se guardan cifradas (hash); aquí se compara contra ese hash
        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]

            session["username"] = user[1]

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos"
        )

    return render_template("login.html")


# --------------------------------
# REGISTER
# --------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"]

        if not username or len(password) < 6:

            return render_template(
                "register.html",
                error="Escribe un usuario y una contraseña de al menos 6 caracteres"
            )

        conn = connect_db()

        try:

            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )

            conn.commit()

        except sqlite3.IntegrityError:

            return render_template(
                "register.html",
                error="Ese usuario ya existe"
            )

        finally:

            conn.close()

        return render_template(
            "register.html",
            success="¡Usuario registrado correctamente!"
        )

    return render_template("register.html")


# --------------------------------
# DASHBOARD
# --------------------------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect("/")

    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY due_date ASC",
        (session["user_id"],)
    )

    tasks = cursor.fetchall()

    conn.close()

    bot_message = random.choice(messages)

    return render_template(
        "index.html",
        tasks=tasks,
        username=session["username"],
        bot_message=bot_message
    )


# --------------------------------
# ADD TASK
# --------------------------------

@app.route("/add", methods=["POST"])
def add_task():

    if "user_id" not in session:

        return redirect("/")

    title = request.form["title"].strip()

    due_date = request.form["due_date"]

    try:

        due = datetime.strptime(due_date, "%Y-%m-%d").date()

    except ValueError:

        return redirect("/dashboard")

    if not title:

        return redirect("/dashboard")

    priority = calculate_priority(due)

    conn = connect_db()

    conn.execute(
        """
        INSERT INTO tasks
        (user_id, title, priority, due_date)
        VALUES (?, ?, ?, ?)
        """,
        (session["user_id"], title, priority, due_date)
    )

    conn.commit()

    conn.close()

    return redirect("/dashboard")


# --------------------------------
# COMPLETE TASK
# --------------------------------

@app.route("/complete/<int:task_id>")
def complete_task(task_id):

    if "user_id" not in session:

        return redirect("/")

    conn = connect_db()

    # Solo se puede completar una tarea propia
    conn.execute(
        "UPDATE tasks SET completed=1 WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    )

    conn.commit()

    conn.close()

    return redirect("/dashboard")


# --------------------------------
# DELETE TASK
# --------------------------------

@app.route("/delete/<int:task_id>")
def delete_task(task_id):

    if "user_id" not in session:

        return redirect("/")

    conn = connect_db()

    # Solo se puede eliminar una tarea propia
    conn.execute(
        "DELETE FROM tasks WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    )

    conn.commit()

    conn.close()

    return redirect("/dashboard")


# --------------------------------
# LOGOUT
# --------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# --------------------------------
# RUN APP
# --------------------------------

if __name__ == "__main__":

    # El modo debug solo se activa si se pide con la variable FLASK_DEBUG=1
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
