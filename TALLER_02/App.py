from flask import Flask, render_template, request, redirect, url_for, jsonify
import pymysql
import pymysql.cursors
import json
from datetime import date, time, datetime

app = Flask(__name__)

DB_CONFIG = {
    "host":     "localhost",
    "port":     3307,
    "user":     "root",
    "password": "root",
    "database": "gestion_legal",
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# ============================================================
# HELPERS
# ============================================================
def get_db():
    return pymysql.connect(**DB_CONFIG)

def serializar(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, time):
        return str(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")

def filas(rows):
    return json.loads(json.dumps(rows, default=serializar))

# ============================================================
# PÁGINA PRINCIPAL – Jinja2
# ============================================================
@app.get("/")
def index():
    db = get_db()
    try:
        with db.cursor() as cur:
            hoy = date.today()

            # Audiencias del día actual
            cur.execute("""
                SELECT au.id, au.hora, au.lugar, au.tipo, au.estado,
                       e.cliente_nombre, a.nombre AS aseguradora, j.nombre AS juzgado
                FROM audiencia au
                JOIN expediente   e ON au.expediente_id  = e.id
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                WHERE au.fecha = %s
                ORDER BY au.hora
            """, (hoy,))
            audiencias = cur.fetchall()

            # Contadores expedientes
            cur.execute("SELECT estado, COUNT(*) AS total FROM expediente GROUP BY estado")
            estados = {r["estado"]: r["total"] for r in cur.fetchall()}

            # Lista expedientes para el formulario
            cur.execute("SELECT id, numero, cliente_nombre FROM expediente ORDER BY id DESC LIMIT 50")
            expedientes = cur.fetchall()

        # Fecha en español
        dias  = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        meses = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        fecha_str = f"{dias[hoy.weekday()]} {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"

        return render_template("index.html",
            audiencias  = audiencias,
            fecha_str   = fecha_str,
            pendientes  = estados.get("pendiente", 0),
            en_curso    = estados.get("en_curso",  0),
            cerrados    = estados.get("cerrado",   0),
            expedientes = expedientes,
        )
    except Exception as e:
        return f"<h2>Error de conexión:</h2><pre>{e}</pre>", 500
    finally:
        db.close()

# ============================================================
# CREAR AUDIENCIA (formulario POST)
# ============================================================
@app.post("/audiencias/crear")
def crear_audiencia():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO audiencia (expediente_id, fecha, hora, lugar, tipo, estado)
                VALUES (%s, %s, %s, %s, %s, 'programada')
            """, (
                request.form.get("expediente_id"),
                request.form.get("fecha"),
                request.form.get("hora"),
                request.form.get("lugar"),
                request.form.get("tipo"),
            ))
        db.commit()
    except Exception as e:
        print(f"Error al crear audiencia: {e}")
    finally:
        db.close()
    return redirect(url_for("index"))

# ============================================================
# ELIMINAR AUDIENCIA
# ============================================================
@app.post("/audiencias/eliminar/<int:id>")
def eliminar_audiencia(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM audiencia WHERE id=%s", (id,))
        db.commit()
    finally:
        db.close()
    return redirect(url_for("index"))

# ============================================================
# API REST (JSON)
# ============================================================
def ok(data=None, status=200, mensaje="OK"):
    return jsonify({"status": "success", "mensaje": mensaje, "data": data}), status

def error(mensaje, status=400):
    return jsonify({"status": "error", "mensaje": mensaje, "data": None}), status

@app.get("/api/health")
def health():
    return ok({"servicio": "Gestión Legal API"})

@app.get("/api/dashboard")
def dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT estado, COUNT(*) AS total FROM expediente GROUP BY estado")
            estados = {r["estado"]: r["total"] for r in cur.fetchall()}
            cur.execute("SELECT COUNT(*) AS total FROM audiencia WHERE fecha = %s", (date.today(),))
            hoy = cur.fetchone()["total"]
        return ok({"expedientes": estados, "audiencias_hoy": hoy})
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.get("/api/expedientes")
def api_expedientes():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT e.*, a.nombre AS aseguradora, j.nombre AS juzgado
                FROM expediente e
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                ORDER BY e.created_at DESC
            """)
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.get("/api/audiencias")
def api_audiencias():
    fecha = request.args.get("fecha")
    db = get_db()
    try:
        with db.cursor() as cur:
            sql = """
                SELECT au.*, e.cliente_nombre, a.nombre AS aseguradora, j.nombre AS juzgado
                FROM audiencia au
                JOIN expediente   e ON au.expediente_id  = e.id
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                WHERE 1=1
            """
            params = []
            if fecha:
                sql += " AND au.fecha = %s"
                params.append(fecha)
            sql += " ORDER BY au.fecha, au.hora"
            cur.execute(sql, params)
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

# ============================================================
# ARRANQUE
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)