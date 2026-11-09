import os
import random
import secrets
import sqlite3
from datetime import date, datetime

from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# La clave se lee de una variable de entorno; si no existe, se genera una aleatoria al iniciar
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(24)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("TASKFLOW_DB", os.path.join(BASE_DIR, "tasks.db"))

FILTROS = {
    "todas": "Todas",
    "pendientes": "Pendientes",
    "vencidas": "Vencidas",
    "completadas": "Completadas",
}


# --------------------------------
# DATABASE
# --------------------------------

def connect_db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = connect_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            priority TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0
        )
    """)

    # Las bases creadas con versiones anteriores no tienen la columna de notas
    columnas = [fila["name"] for fila in conn.execute("PRAGMA table_info(tasks)")]

    if "notes" not in columnas:
        conn.execute("ALTER TABLE tasks ADD COLUMN notes TEXT DEFAULT ''")

    conn.commit()

    conn.close()


init_db()


# --------------------------------
# PROTECCIÓN CSRF
# --------------------------------

def csrf_token():
    """Token por sesión que se incluye en cada formulario para evitar envíos falsificados."""

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)

    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def verificar_csrf():

    if request.method == "POST" and not app.config.get("TESTING"):

        token = request.form.get("csrf_token")

        if not token or token != session.get("csrf_token"):
            abort(400)


# --------------------------------
# LÓGICA DE TAREAS
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


def describir_plazo(days_left):
    """Texto amigable con el tiempo que falta para la entrega."""

    if days_left < -1:
        return f"Venció hace {-days_left} días"

    if days_left == -1:
        return "Venció ayer"

    if days_left == 0:
        return "Vence hoy"

    if days_left == 1:
        return "Vence mañana"

    return f"Faltan {days_left} días"


def preparar_tarea(fila, today=None):
    """Convierte una fila de la base de datos en un diccionario listo para mostrar."""

    today = today or date.today()

    due = datetime.strptime(fila["due_date"], "%Y-%m-%d").date()

    days_left = (due - today).days

    completada = bool(fila["completed"])

    return {
        "id": fila["id"],
        "title": fila["title"],
        "notes": fila["notes"] or "",
        "due_date": fila["due_date"],
        "due_label": due.strftime("%d/%m/%Y"),
        "completed": completada,
        "days_left": days_left,
        "plazo": describir_plazo(days_left),
        "vencida": days_left < 0 and not completada,
        # La prioridad se recalcula cada día para que no quede desactualizada
        "priority": calculate_priority(due, today),
    }


def leer_formulario_tarea():
    """Valida título, fecha y notas del formulario. Devuelve (datos, error)."""

    title = request.form.get("title", "").strip()

    notes = request.form.get("notes", "").strip()

    due_date = request.form.get("due_date", "")

    if not title:
        return None, "La tarea necesita un título."

    if len(title) > 120:
        return None, "El título puede tener máximo 120 caracteres."

    try:
        due = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Elige una fecha de entrega válida."

    return {"title": title, "notes": notes[:500], "due": due}, None


def mensaje_taskbot(tareas):
    """Mensaje del asistente según el estado real de las tareas."""

    vencidas = [t for t in tareas if t["vencida"]]

    hoy = [t for t in tareas if not t["completed"] and t["days_left"] == 0]

    pendientes = [t for t in tareas if not t["completed"]]

    if vencidas:
        return f"⚠️ Tienes {len(vencidas)} tarea(s) vencida(s). Empieza por «{vencidas[0]['title']}»."

    if hoy:
        return f"⏰ Hoy vence «{hoy[0]['title']}». ¡Tú puedes!"

    if tareas and not pendientes:
        return "🎉 ¡Completaste todas tus tareas! Buen trabajo."

    if not tareas:
        return "👋 Agrega tu primera tarea para empezar a organizarte."

    return random.choice([
        "💡 Consejo: empieza por las tareas pequeñas.",
        "📌 Mantener un horario organizado reduce el estrés.",
        "🧠 La constancia diaria genera mejores resultados.",
        "🔥 Cada tarea completada es un avance importante.",
    ])


def obtener_tarea(task_id):
    """Busca una tarea del usuario actual; responde 404 si no existe o es de otra persona."""

    conn = connect_db()

    fila = conn.execute(
        "SELECT * FROM tasks WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    ).fetchone()

    conn.close()

    if fila is None:
        abort(404)

    return fila


def login_requerido():

    return "user_id" not in session


def volver_al_dashboard():
    """Regresa a la vista anterior (con su filtro) solo si viene de esta misma aplicación."""

    anterior = request.referrer or ""

    if anterior.startswith(request.host_url):
        return redirect(anterior)

    return redirect(url_for("dashboard"))


# --------------------------------
# LOGIN Y REGISTRO
# --------------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        password = request.form.get("password", "")

        conn = connect_db()

        user = conn.execute(
            "SELECT id, username, password FROM users WHERE username=?",
            (username,)
        ).fetchone()

        conn.close()

        # Las contraseñas se guardan cifradas (hash); aquí se compara contra ese hash
        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        password = request.form.get("password", "")

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

            return render_template("register.html", error="Ese usuario ya existe")

        finally:

            conn.close()

        return render_template(
            "register.html",
            success="¡Usuario registrado correctamente! Ya puedes iniciar sesión."
        )

    return render_template("register.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# --------------------------------
# DASHBOARD
# --------------------------------

@app.route("/dashboard")
def dashboard():

    if login_requerido():
        return redirect(url_for("login"))

    filtro = request.args.get("filtro", "pendientes")

    if filtro not in FILTROS:
        filtro = "pendientes"

    busqueda = request.args.get("q", "").strip()

    conn = connect_db()

    filas = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY completed ASC, due_date ASC",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    tareas = [preparar_tarea(fila) for fila in filas]

    total = len(tareas)

    completadas = sum(1 for t in tareas if t["completed"])

    stats = {
        "total": total,
        "completadas": completadas,
        "pendientes": total - completadas,
        "vencidas": sum(1 for t in tareas if t["vencida"]),
        "progreso": round(completadas * 100 / total) if total else 0,
    }

    visibles = tareas

    if filtro == "pendientes":
        visibles = [t for t in tareas if not t["completed"]]
    elif filtro == "completadas":
        visibles = [t for t in tareas if t["completed"]]
    elif filtro == "vencidas":
        visibles = [t for t in tareas if t["vencida"]]

    if busqueda:
        visibles = [t for t in visibles if busqueda.lower() in t["title"].lower()]

    proximas = [t for t in tareas if not t["completed"] and t["days_left"] >= 0][:3]

    hoy = date.today()

    # Días del mes actual que tienen entregas pendientes, para marcarlos en el calendario
    dias_con_tareas = sorted({
        int(t["due_date"][8:10]) for t in tareas
        if not t["completed"] and t["due_date"][:7] == hoy.strftime("%Y-%m")
    })

    return render_template(
        "index.html",
        tareas=visibles,
        proximas=proximas,
        stats=stats,
        filtro=filtro,
        filtros=FILTROS,
        busqueda=busqueda,
        username=session["username"],
        bot_message=mensaje_taskbot(tareas),
        dias_con_tareas=dias_con_tareas,
        hoy=hoy.isoformat(),
    )


# --------------------------------
# CRUD DE TAREAS
# --------------------------------

@app.route("/add", methods=["POST"])
def add_task():

    if login_requerido():
        return redirect(url_for("login"))

    datos, error = leer_formulario_tarea()

    if error:
        flash(error, "error")
        return redirect(url_for("dashboard"))

    conn = connect_db()

    conn.execute(
        "INSERT INTO tasks (user_id, title, priority, due_date, notes) VALUES (?, ?, ?, ?, ?)",
        (
            session["user_id"],
            datos["title"],
            calculate_priority(datos["due"]),
            datos["due"].isoformat(),
            datos["notes"],
        )
    )

    conn.commit()

    conn.close()

    flash("Tarea agregada.", "success")

    return redirect(url_for("dashboard"))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):

    if login_requerido():
        return redirect(url_for("login"))

    fila = obtener_tarea(task_id)

    if request.method == "POST":

        datos, error = leer_formulario_tarea()

        if error:
            return render_template("edit.html", tarea=preparar_tarea(fila), error=error)

        conn = connect_db()

        conn.execute(
            "UPDATE tasks SET title=?, notes=?, due_date=?, priority=? WHERE id=? AND user_id=?",
            (
                datos["title"],
                datos["notes"],
                datos["due"].isoformat(),
                calculate_priority(datos["due"]),
                task_id,
                session["user_id"],
            )
        )

        conn.commit()

        conn.close()

        flash("Tarea actualizada.", "success")

        return redirect(url_for("dashboard"))

    return render_template("edit.html", tarea=preparar_tarea(fila))


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle_task(task_id):

    if login_requerido():
        return redirect(url_for("login"))

    fila = obtener_tarea(task_id)

    nuevo_estado = 0 if fila["completed"] else 1

    conn = connect_db()

    conn.execute(
        "UPDATE tasks SET completed=? WHERE id=? AND user_id=?",
        (nuevo_estado, task_id, session["user_id"])
    )

    conn.commit()

    conn.close()

    flash("¡Tarea completada! 🎉" if nuevo_estado else "Tarea marcada como pendiente.", "success")

    return volver_al_dashboard()


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):

    if login_requerido():
        return redirect(url_for("login"))

    obtener_tarea(task_id)

    conn = connect_db()

    conn.execute(
        "DELETE FROM tasks WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    )

    conn.commit()

    conn.close()

    flash("Tarea eliminada.", "success")

    return volver_al_dashboard()


@app.errorhandler(404)
def no_encontrado(error):

    return render_template("error.html", titulo="No encontramos esa página", codigo=404), 404


@app.errorhandler(400)
def solicitud_invalida(error):

    return render_template(
        "error.html",
        titulo="La solicitud no es válida. Recarga la página e inténtalo de nuevo.",
        codigo=400
    ), 400


# --------------------------------
# RUN APP
# --------------------------------

if __name__ == "__main__":

    # El modo debug solo se activa si se pide con la variable FLASK_DEBUG=1
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
