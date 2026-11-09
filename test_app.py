import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

# La base de datos de pruebas es un archivo temporal, separado de tasks.db
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["TASKFLOW_DB"] = _db.name

import app as taskflow  # noqa: E402


class TaskFlowTest(unittest.TestCase):

    def setUp(self):
        taskflow.app.config["TESTING"] = True
        conn = sqlite3.connect(taskflow.DB_PATH)
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()

    def cliente_con_sesion(self, usuario, clave="secreta1"):
        cliente = taskflow.app.test_client()
        cliente.post("/register", data={"username": usuario, "password": clave})
        cliente.post("/", data={"username": usuario, "password": clave})
        return cliente

    def consultar(self, sql, *params):
        conn = sqlite3.connect(taskflow.DB_PATH)
        fila = conn.execute(sql, params).fetchone()
        conn.close()
        return fila

    # Registro e inicio de sesión

    def test_registro_valida_contrasena_corta(self):
        respuesta = taskflow.app.test_client().post("/register", data={"username": "ana", "password": "123"})
        self.assertIn("al menos 6", respuesta.get_data(as_text=True))

    def test_contrasena_se_guarda_cifrada(self):
        self.cliente_con_sesion("ana")
        guardada = self.consultar("SELECT password FROM users WHERE username='ana'")[0]
        self.assertNotEqual(guardada, "secreta1")

    def test_usuario_repetido(self):
        cliente = taskflow.app.test_client()
        cliente.post("/register", data={"username": "ana", "password": "secreta1"})
        respuesta = cliente.post("/register", data={"username": "ana", "password": "secreta1"})
        self.assertIn("ya existe", respuesta.get_data(as_text=True))

    def test_login_incorrecto(self):
        self.cliente_con_sesion("ana")
        respuesta = taskflow.app.test_client().post("/", data={"username": "ana", "password": "mala"})
        self.assertIn("incorrectos", respuesta.get_data(as_text=True))

    def test_dashboard_requiere_sesion(self):
        respuesta = taskflow.app.test_client().get("/dashboard")
        self.assertEqual(respuesta.status_code, 302)

    # Tareas

    def test_crear_editar_completar_y_eliminar(self):
        cliente = self.cliente_con_sesion("ana")
        cliente.post("/add", data={"title": "Taller", "due_date": date.today().isoformat(), "notes": "Capítulo 3"})
        tarea_id, prioridad = self.consultar("SELECT id, priority FROM tasks WHERE title='Taller'")
        self.assertEqual(prioridad, "Alta")

        self.assertIn("Taller", cliente.get("/dashboard").get_data(as_text=True))

        lejana = (date.today() + timedelta(days=30)).isoformat()
        cliente.post(f"/edit/{tarea_id}", data={"title": "Taller final", "due_date": lejana, "notes": ""})
        self.assertEqual(self.consultar("SELECT title, priority FROM tasks WHERE id=?", tarea_id), ("Taller final", "Baja"))

        cliente.post(f"/toggle/{tarea_id}")
        self.assertEqual(self.consultar("SELECT completed FROM tasks WHERE id=?", tarea_id)[0], 1)

        cliente.post(f"/delete/{tarea_id}")
        self.assertIsNone(self.consultar("SELECT id FROM tasks WHERE id=?", tarea_id))

    def test_titulo_vacio_no_se_guarda(self):
        cliente = self.cliente_con_sesion("ana")
        cliente.post("/add", data={"title": "  ", "due_date": date.today().isoformat()})
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM tasks")[0], 0)

    def test_otro_usuario_no_puede_tocar_mis_tareas(self):
        ana = self.cliente_con_sesion("ana")
        luis = self.cliente_con_sesion("luis")
        ana.post("/add", data={"title": "Privada", "due_date": date.today().isoformat()})
        tarea_id = self.consultar("SELECT id FROM tasks")[0]

        self.assertNotIn("Privada", luis.get("/dashboard?filtro=todas").get_data(as_text=True))
        self.assertEqual(luis.post(f"/delete/{tarea_id}").status_code, 404)
        self.assertEqual(luis.get(f"/edit/{tarea_id}").status_code, 404)
        self.assertIsNotNone(self.consultar("SELECT id FROM tasks WHERE id=?", tarea_id))

    def test_filtro_vencidas(self):
        cliente = self.cliente_con_sesion("ana")
        ayer = (date.today() - timedelta(days=1)).isoformat()
        cliente.post("/add", data={"title": "Atrasada", "due_date": ayer})
        cliente.post("/add", data={"title": "A tiempo", "due_date": date.today().isoformat()})
        pagina = cliente.get("/dashboard?filtro=vencidas").get_data(as_text=True)
        # Se revisa la lista de tareas; "A tiempo" sí puede aparecer en "Próximas entregas"
        self.assertIn('task-title">Atrasada', pagina)
        self.assertNotIn('task-title">A tiempo', pagina)

    # Funciones auxiliares

    def test_prioridad_y_plazo(self):
        hoy = date(2026, 1, 1)
        self.assertEqual(taskflow.calculate_priority(date(2026, 1, 4), hoy), "Alta")
        self.assertEqual(taskflow.calculate_priority(date(2026, 1, 8), hoy), "Media")
        self.assertEqual(taskflow.calculate_priority(date(2026, 1, 20), hoy), "Baja")
        self.assertEqual(taskflow.describir_plazo(0), "Vence hoy")
        self.assertEqual(taskflow.describir_plazo(-3), "Venció hace 3 días")


if __name__ == "__main__":
    unittest.main()
