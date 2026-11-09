# TaskFlow AI

TaskFlow AI es una aplicación web desarrollada con Python, Flask y SQLite enfocada en la organización académica y productividad personal.

La plataforma permite gestionar tareas, visualizar fechas importantes mediante un calendario interactivo y mejorar la organización diaria mediante prioridades automáticas y un sistema inteligente de apoyo motivacional.

---

# Características principales

* Registro e inicio de sesión de usuarios  
* Gestión de tareas académicas y personales  
* Prioridades automáticas según fecha de entrega  
* Dashboard interactivo y moderno  
* Calendario dinámico integrado  
* TaskBot con mensajes motivacionales  
* Diseño responsive adaptable a dispositivos móviles  
* Base de datos SQLite  
* Interfaz moderna desarrollada con HTML, CSS y Flask  

---

# Tecnologías utilizadas

- Python
- Flask
- SQLite
- HTML5
- CSS3
- JavaScript
- Git & GitHub

---

#  Vista previa

<img width="1433" height="961" alt="imagen" src="https://github.com/user-attachments/assets/ac029735-ad60-45f5-a73b-ae88a1d2cec2" />
<img width="1426" height="959" alt="imagen" src="https://github.com/user-attachments/assets/624d9367-e70f-436b-bc01-7c5fdee27158" />
<img width="1424" height="972" alt="imagen" src="https://github.com/user-attachments/assets/b2b5bb79-ef17-486d-a834-b280d8d42e54" />



---

#  Instalación

## 1. Clonar repositorio

```bash
git clone https://github.com/evelyn-escobar/taskFlow_web_app.git
```

---

## 2. Entrar a la carpeta

```bash
cd taskFlow_web_app
```

---

## 3. Crear un entorno virtual e instalar dependencias

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

La base de datos SQLite (`tasks.db`) se crea sola la primera vez que se ejecuta la aplicación.

---

## 4. Ejecutar aplicación

```bash
python app.py
```

---

## 5. Abrir en navegador

```plaintext
http://127.0.0.1:5000
```

---

# Seguridad

- Las contraseñas se guardan cifradas con `generate_password_hash` de Werkzeug, nunca en texto plano.
- Cada usuario solo puede ver, completar y eliminar sus propias tareas.
- Las consultas SQL usan parámetros (`?`) para evitar inyección SQL.
- La clave de sesión se lee de la variable de entorno `SECRET_KEY`, y el modo debug solo se activa con `FLASK_DEBUG=1`.

---

# Funcionalidades inteligentes

El sistema calcula automáticamente la prioridad de cada tarea dependiendo de la cercanía de la fecha de entrega:

- 🔴 Alta prioridad → faltan 3 días o menos
- 🟡 Prioridad media → faltan entre 4 y 7 días
- 🟢 Baja prioridad → faltan más de 7 días

Además, TaskBot proporciona mensajes motivacionales y recomendaciones para mejorar la productividad.

---

# Objetivo del proyecto

Este proyecto fue desarrollado como práctica de desarrollo web y backend utilizando Flask, buscando fortalecer habilidades en:

- lógica de programación,
- desarrollo backend,
- bases de datos,
- interfaces modernas,
- automatización de tareas,
- experiencia de usuario.

---

# Autor

### Evelyn Daniela Escobar

Estudiante de Tecnología en Desarrollo de Software  
Desarrolladora Junior en formación.

---

# Estado del proyecto

* En desarrollo activo  
* Nuevas funciones y mejoras próximamente
