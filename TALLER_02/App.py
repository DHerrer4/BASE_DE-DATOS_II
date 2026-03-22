from flask import Flask, render_template, request, redirect, url_for, jsonify
import pymysql
import pymysql.cursors
import json
from datetime import date, time, datetime, timedelta

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
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, timedelta):          # fix: TIME de MariaDB llega como timedelta
        total = int(obj.total_seconds())
        h, rem = divmod(total, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    if isinstance(obj, time):
        return str(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")

def filas(rows):
    return json.loads(json.dumps(rows, default=serializar))

def hora_str(valor):
    if isinstance(valor, timedelta):
        total = int(valor.total_seconds())
        h, rem = divmod(total, 3600)
        m, _   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}"
    return str(valor)

def ok(data=None, status=200, mensaje="OK"):
    return jsonify({"status": "success", "mensaje": mensaje, "data": data}), status

def error(mensaje, status=400):
    return jsonify({"status": "error", "mensaje": mensaje, "data": None}), status

# ============================================================
# PÁGINA PRINCIPAL – Jinja2
# ============================================================
@app.route("/", methods=["GET"])
def index():
    db = get_db()
    try:
        with db.cursor() as cur:
            hoy = date.today()

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
            audiencias_raw = cur.fetchall()
            audiencias = []
            for a in audiencias_raw:
                a["hora"] = hora_str(a["hora"])
                audiencias.append(a)

            cur.execute("SELECT estado, COUNT(*) AS total FROM expediente GROUP BY estado")
            estados = {r["estado"]: r["total"] for r in cur.fetchall()}

            cur.execute("SELECT id, numero, cliente_nombre FROM expediente ORDER BY id DESC LIMIT 50")
            expedientes = cur.fetchall()

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
# FORMULARIO: CREAR AUDIENCIA (desde la página)
# ============================================================
@app.route("/audiencias/crear", methods=["POST"])
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
# FORMULARIO: ELIMINAR AUDIENCIA (desde la página)
# ============================================================
@app.route("/audiencias/eliminar/<int:id>", methods=["POST"])
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
# API REST – HEALTH
# ============================================================
@app.route("/api/health", methods=["GET"])
def health():
    return ok({"servicio": "Gestión Legal API"})

# ============================================================
# API REST – DASHBOARD
# ============================================================
@app.route("/api/dashboard", methods=["GET"])
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

# ============================================================
# API REST – EXPEDIENTES (CRUD completo)
# ============================================================

# SELECT todos
@app.route("/api/expedientes", methods=["GET"])
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

# SELECT uno por id
@app.route("/api/expedientes/<int:id>", methods=["GET"])
def api_obtener_expediente(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT e.*, a.nombre AS aseguradora, j.nombre AS juzgado
                FROM expediente e
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                WHERE e.id = %s
            """, (id,))
            row = cur.fetchone()
        if not row:
            return error("Expediente no encontrado", 404)
        return ok(filas([row])[0])
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

# INSERT
@app.route("/api/expedientes", methods=["POST"])
def api_crear_expediente():
    data = request.get_json(silent=True) or {}
    if not data.get("numero") or not data.get("cliente_nombre"):
        return error("Campos obligatorios: numero, cliente_nombre")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO expediente
                (numero, cliente_nombre, descripcion, estado, aseguradora_id, juzgado_id, fecha_inicio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (data["numero"], data["cliente_nombre"], data.get("descripcion"),
                  data.get("estado", "pendiente"), data.get("aseguradora_id"),
                  data.get("juzgado_id"), data.get("fecha_inicio")))
        db.commit()
        return ok({"id": cur.lastrowid}, 201, "Expediente creado")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# UPDATE
@app.route("/api/expedientes/<int:id>", methods=["PUT"])
def api_actualizar_expediente(id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE expediente
                SET cliente_nombre=%s, descripcion=%s, estado=%s,
                    aseguradora_id=%s, juzgado_id=%s, fecha_cierre=%s
                WHERE id=%s
            """, (data.get("cliente_nombre"), data.get("descripcion"),
                  data.get("estado"), data.get("aseguradora_id"),
                  data.get("juzgado_id"), data.get("fecha_cierre"), id))
        db.commit()
        return ok(None, 200, "Expediente actualizado")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# DELETE
@app.route("/api/expedientes/<int:id>", methods=["DELETE"])
def api_eliminar_expediente(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM expediente WHERE id=%s", (id,))
        db.commit()
        return ok(None, 200, "Expediente eliminado")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# ============================================================
# API REST – AUDIENCIAS (CRUD completo)
# ============================================================

# SELECT todos
@app.route("/api/audiencias", methods=["GET"])
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

# SELECT uno por id
@app.route("/api/audiencias/<int:id>", methods=["GET"])
def api_obtener_audiencia(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT au.*, e.cliente_nombre, a.nombre AS aseguradora, j.nombre AS juzgado
                FROM audiencia au
                JOIN expediente   e ON au.expediente_id  = e.id
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                WHERE au.id = %s
            """, (id,))
            row = cur.fetchone()
        if not row:
            return error("Audiencia no encontrada", 404)
        return ok(filas([row])[0])
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

# INSERT
@app.route("/api/audiencias", methods=["POST"])
def api_crear_audiencia():
    data = request.get_json(silent=True) or {}
    if not data.get("expediente_id") or not data.get("fecha") or not data.get("hora"):
        return error("Campos obligatorios: expediente_id, fecha, hora")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO audiencia (expediente_id, fecha, hora, lugar, tipo, estado)
                VALUES (%s, %s, %s, %s, %s, 'programada')
            """, (data["expediente_id"], data["fecha"], data["hora"],
                  data.get("lugar"), data.get("tipo")))
        db.commit()
        return ok({"id": cur.lastrowid}, 201, "Audiencia creada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# UPDATE
@app.route("/api/audiencias/<int:id>", methods=["PUT"])
def api_actualizar_audiencia(id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE audiencia
                SET fecha=%s, hora=%s, lugar=%s, tipo=%s, estado=%s
                WHERE id=%s
            """, (data.get("fecha"), data.get("hora"), data.get("lugar"),
                  data.get("tipo"), data.get("estado"), id))
        db.commit()
        return ok(None, 200, "Audiencia actualizada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# DELETE
@app.route("/api/audiencias/<int:id>", methods=["DELETE"])
def api_eliminar_audiencia(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM audiencia WHERE id=%s", (id,))
        db.commit()
        return ok(None, 200, "Audiencia eliminada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# ============================================================
# ARRANQUE
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)