from flask import Flask, render_template, jsonify, request
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

def ok(data=None, status=200, mensaje="OK"):
    return jsonify({"status": "success", "mensaje": mensaje, "data": data}), status

def error(mensaje, status=400):
    return jsonify({"status": "error", "mensaje": mensaje, "data": None}), status

def filas(rows):
    return json.loads(json.dumps(rows, default=serializar))

# ============================================================
# FRONTEND
# ============================================================
@app.get("/")
def index():
    return render_template("index.html")

# ============================================================
# HEALTH
# ============================================================
@app.get("/api/health")
def health():
    return ok({"servicio": "Gestión Legal API", "version": "1.0"})

# ============================================================
# DASHBOARD
# ============================================================
@app.get("/api/dashboard")
def dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT estado, COUNT(*) AS total FROM expediente GROUP BY estado")
            estados = {r["estado"]: r["total"] for r in cur.fetchall()}
            hoy = date.today().isoformat()
            cur.execute("SELECT COUNT(*) AS total FROM audiencia WHERE fecha = %s", (hoy,))
            audiencias_hoy = cur.fetchone()["total"]
        return ok({
            "expedientes": {
                "pendientes": estados.get("pendiente", 0),
                "en_curso":   estados.get("en_curso",  0),
                "cerrados":   estados.get("cerrado",   0),
            },
            "audiencias_hoy": audiencias_hoy,
        })
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

# ============================================================
# ASEGURADORAS
# ============================================================
@app.get("/api/aseguradoras")
def listar_aseguradoras():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM aseguradora WHERE activa=1 ORDER BY nombre")
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.post("/api/aseguradoras")
def crear_aseguradora():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return error("El campo 'nombre' es obligatorio")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO aseguradora (nombre, telefono, email) VALUES (%s,%s,%s)",
                (nombre, data.get("telefono"), data.get("email"))
            )
        db.commit()
        return ok({"id": cur.lastrowid}, 201, "Aseguradora creada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

# ============================================================
# JUZGADOS
# ============================================================
@app.get("/api/juzgados")
def listar_juzgados():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM juzgado WHERE activo=1 ORDER BY nombre")
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

# ============================================================
# EXPEDIENTES
# ============================================================
@app.get("/api/expedientes")
def listar_expedientes():
    estado = request.args.get("estado")
    db = get_db()
    try:
        with db.cursor() as cur:
            sql = """
                SELECT e.*, a.nombre AS aseguradora, j.nombre AS juzgado,
                       u.nombre_completo AS abogado
                FROM expediente e
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                LEFT JOIN usuario     u ON e.abogado_id     = u.id
            """
            if estado:
                sql += " WHERE e.estado = %s ORDER BY e.created_at DESC"
                cur.execute(sql, (estado,))
            else:
                sql += " ORDER BY e.created_at DESC"
                cur.execute(sql)
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.get("/api/expedientes/<int:id>")
def obtener_expediente(id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT e.*, a.nombre AS aseguradora, j.nombre AS juzgado,
                       u.nombre_completo AS abogado
                FROM expediente e
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                LEFT JOIN usuario     u ON e.abogado_id     = u.id
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

@app.post("/api/expedientes")
def crear_expediente():
    data = request.get_json(silent=True) or {}
    if not data.get("numero") or not data.get("cliente_nombre"):
        return error("Campos obligatorios: numero, cliente_nombre")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO expediente
                (numero, cliente_nombre, descripcion, estado, aseguradora_id, juzgado_id, abogado_id, fecha_inicio)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (data["numero"], data["cliente_nombre"], data.get("descripcion"),
                  data.get("estado", "pendiente"), data.get("aseguradora_id"),
                  data.get("juzgado_id"), data.get("abogado_id"), data.get("fecha_inicio")))
        db.commit()
        return ok({"id": cur.lastrowid}, 201, "Expediente creado")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

@app.put("/api/expedientes/<int:id>")
def actualizar_expediente(id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE expediente
                SET cliente_nombre=%s, descripcion=%s, estado=%s,
                    aseguradora_id=%s, juzgado_id=%s, fecha_cierre=%s
                WHERE id=%s
            """, (data.get("cliente_nombre"), data.get("descripcion"), data.get("estado"),
                  data.get("aseguradora_id"), data.get("juzgado_id"),
                  data.get("fecha_cierre"), id))
        db.commit()
        return ok(None, 200, "Expediente actualizado")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

@app.delete("/api/expedientes/<int:id>")
def eliminar_expediente(id):
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
# AUDIENCIAS
# ============================================================
@app.get("/api/audiencias")
def listar_audiencias():
    fecha  = request.args.get("fecha")
    exp_id = request.args.get("expediente_id")
    db = get_db()
    try:
        with db.cursor() as cur:
            sql = """
                SELECT au.*, e.numero, e.cliente_nombre,
                       a.nombre AS aseguradora, j.nombre AS juzgado
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
            if exp_id:
                sql += " AND au.expediente_id = %s"
                params.append(exp_id)
            sql += " ORDER BY au.fecha, au.hora"
            cur.execute(sql, params)
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.get("/api/audiencias/hoy")
def agenda_hoy():
    hoy = date.today().isoformat()
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT au.*, e.numero, e.cliente_nombre,
                       a.nombre AS aseguradora, j.nombre AS juzgado
                FROM audiencia au
                JOIN expediente   e ON au.expediente_id  = e.id
                LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
                LEFT JOIN juzgado     j ON e.juzgado_id     = j.id
                WHERE au.fecha = %s
                ORDER BY au.hora
            """, (hoy,))
            return ok(filas(cur.fetchall()))
    except Exception as e:
        return error(str(e))
    finally:
        db.close()

@app.post("/api/audiencias")
def crear_audiencia():
    data = request.get_json(silent=True) or {}
    if not data.get("expediente_id") or not data.get("fecha") or not data.get("hora"):
        return error("Campos obligatorios: expediente_id, fecha, hora")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO audiencia (expediente_id, fecha, hora, lugar, tipo, observaciones, estado)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (data["expediente_id"], data["fecha"], data["hora"],
                  data.get("lugar"), data.get("tipo"), data.get("observaciones"),
                  data.get("estado", "programada")))
        db.commit()
        return ok({"id": cur.lastrowid}, 201, "Audiencia creada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

@app.put("/api/audiencias/<int:id>")
def actualizar_audiencia(id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE audiencia
                SET fecha=%s, hora=%s, lugar=%s, tipo=%s, observaciones=%s, estado=%s
                WHERE id=%s
            """, (data.get("fecha"), data.get("hora"), data.get("lugar"),
                  data.get("tipo"), data.get("observaciones"), data.get("estado"), id))
        db.commit()
        return ok(None, 200, "Audiencia actualizada")
    except Exception as e:
        db.rollback()
        return error(str(e))
    finally:
        db.close()

@app.delete("/api/audiencias/<int:id>")
def eliminar_audiencia(id):
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