"""
database.py — Capa de datos de SaluDigital
Toda la lógica de acceso a SQLite vive aquí.
La UI no importa sqlite3 directamente.
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Importar cifrado (disponible después de que security.py esté cargado)
def _cifrar(t):
    try:
        from security import cifrar
        return cifrar(t) if t else t
    except Exception:
        return t

def _descifrar(t):
    try:
        from security import descifrar
        return descifrar(t) if t else t
    except Exception:
        return t


DB_PATH = "salud_unellez.db"


def _connect():
    return sqlite3.connect(DB_PATH)


# ================================================================
#  INICIALIZACIÓN
# ================================================================

def inicializar(admin_hash: str):
    """Crea las tablas si no existen y el usuario admin por defecto."""
    try:
        conn = _connect()
        cur  = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula           TEXT    NOT NULL,
                nombre           TEXT,
                apellido         TEXT,
                telefono         TEXT,
                tipo_persona     TEXT,
                fecha_nacimiento TEXT,
                edad             INTEGER,
                motivo           TEXT,
                diagnostico      TEXT,
                tratamiento      TEXT,
                altura_cm        REAL,
                peso_kg          REAL,
                imc              REAL,
                area_atencion    TEXT,
                fecha_registro   TEXT
            )
        ''')

        # Migración: agregar columnas si la BD ya existía sin ellas
        for col_sql in [
            "ALTER TABLE pacientes ADD COLUMN tipo_persona TEXT",
            "ALTER TABLE pacientes ADD COLUMN fecha_nacimiento TEXT",
            "ALTER TABLE pacientes ADD COLUMN edad INTEGER",
            "ALTER TABLE pacientes ADD COLUMN diagnostico TEXT",
            "ALTER TABLE pacientes ADD COLUMN tratamiento TEXT",
            "ALTER TABLE pacientes ADD COLUMN altura_cm REAL",
            "ALTER TABLE pacientes ADD COLUMN peso_kg REAL",
            "ALTER TABLE pacientes ADD COLUMN imc REAL",
        ]:
            try:
                cur.execute(col_sql)
            except Exception:
                pass  # columna ya existe, ignorar

        cur.execute('''
            CREATE TABLE IF NOT EXISTS insumos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre   TEXT UNIQUE NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS movimientos_insumos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                insumo_id   INTEGER NOT NULL,
                nombre      TEXT NOT NULL,
                tipo        TEXT NOT NULL,
                cantidad    INTEGER NOT NULL,
                cantidad_anterior INTEGER,
                cantidad_nueva    INTEGER,
                fecha       TEXT NOT NULL,
                FOREIGN KEY (insumo_id) REFERENCES insumos(id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol           TEXT NOT NULL DEFAULT 'usuario',
                activo        INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Admin por defecto solo si no existe ningún usuario
        cur.execute("SELECT COUNT(*) FROM usuarios")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO usuarios (username, password_hash, rol) VALUES (?,?,?)",
                ("admin", admin_hash, "admin")
            )
            logger.info("Usuario admin creado — contraseña inicial: Admin1234!")

        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error al inicializar la base de datos: %s", e)
        raise
    finally:
        conn.close()


# ================================================================
#  USUARIOS
# ================================================================

def obtener_todos_usuarios() -> list[tuple]:
    """Devuelve (id, username, rol, activo) de todos los usuarios."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("SELECT id, username, rol, activo FROM usuarios ORDER BY id ASC")
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("obtener_todos_usuarios: %s", e); return []
    finally: conn.close()


def crear_usuario(username: str, password_hash: str, rol: str) -> bool:
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO usuarios (username, password_hash, rol, activo) VALUES (?,?,?,1)",
            (username, password_hash, rol))
        conn.commit()
        logger.info("Usuario creado: %s (%s)", username, rol)
        return True
    except sqlite3.IntegrityError:
        logger.warning("Usuario ya existe: %s", username)
        return False
    except sqlite3.Error as e:
        logger.error("crear_usuario: %s", e); return False
    finally: conn.close()


def actualizar_usuario(uid: int, rol: str, activo: int) -> bool:
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("UPDATE usuarios SET rol=?, activo=? WHERE id=?", (rol, activo, uid))
        conn.commit()
        logger.info("Usuario id=%s actualizado rol=%s activo=%s", uid, rol, activo)
        return True
    except sqlite3.Error as e:
        logger.error("actualizar_usuario id=%s: %s", uid, e); return False
    finally: conn.close()


def cambiar_password(uid: int, nuevo_hash: str) -> bool:
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (nuevo_hash, uid))
        conn.commit()
        logger.info("Contraseña cambiada para usuario id=%s", uid)
        return True
    except sqlite3.Error as e:
        logger.error("cambiar_password id=%s: %s", uid, e); return False
    finally: conn.close()


def eliminar_usuario(uid: int) -> bool:
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id=?", (uid,))
        conn.commit()
        logger.info("Usuario id=%s eliminado", uid)
        return True
    except sqlite3.Error as e:
        logger.error("eliminar_usuario id=%s: %s", uid, e); return False
    finally: conn.close()



def obtener_usuario(username: str) -> dict | None:
    """Devuelve {password_hash, rol, activo} o None si no existe."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT password_hash, rol, activo FROM usuarios WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()
        if row:
            return {"password_hash": row[0], "rol": row[1], "activo": row[2]}
        return None
    except sqlite3.Error as e:
        logger.error("Error al obtener usuario '%s': %s", username, e)
        return None
    finally:
        conn.close()


# ================================================================
#  PACIENTES
# ================================================================

def registrar_paciente(cedula, nombre, apellido, telefono, tipo_persona,
                       fecha_nacimiento, edad, motivo, diagnostico, tratamiento,
                       altura_cm, peso_kg, imc, area) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        cur.execute(
            "INSERT INTO pacientes "
            "(cedula, nombre, apellido, telefono, tipo_persona, fecha_nacimiento, edad, "
            "motivo, diagnostico, tratamiento, altura_cm, peso_kg, imc, "
            "area_atencion, fecha_registro) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_cifrar(cedula), nombre, apellido, telefono, tipo_persona,
             fecha_nacimiento, edad, _cifrar(motivo), _cifrar(diagnostico),
             _cifrar(tratamiento), altura_cm, peso_kg, imc, area, fecha)
        )
        conn.commit()
        logger.info("Paciente registrado: cédula=%s, área=%s", cedula, area)
        return True
    except sqlite3.Error as e:
        logger.error("Error al registrar paciente: %s", e)
        return False
    finally:
        conn.close()


def obtener_pacientes(area: str, busqueda: str = "") -> list[tuple]:
    """Devuelve (id, fecha, nombre, apellido, cedula, tipo_persona, edad, motivo, diagnostico, tratamiento, altura_cm, peso_kg, imc)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        q    = f"%{busqueda}%"
        cur.execute(
            """
            SELECT id, fecha_registro, nombre, apellido, cedula, tipo_persona,
                   edad, motivo, diagnostico, tratamiento, altura_cm, peso_kg, imc
            FROM   pacientes
            WHERE  area_atencion = ?
              AND  (nombre   LIKE ?
                OR apellido  LIKE ?
                OR cedula    LIKE ?
                OR motivo    LIKE ?
                OR diagnostico LIKE ?
                OR tratamiento LIKE ?)
            ORDER BY id DESC
            """,
            (area, q, q, q, q, q, q)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error al obtener pacientes: %s", e)
        return []
    finally:
        conn.close()


def eliminar_todos_pacientes_area(area: str) -> int:
    """Elimina todos los pacientes de un área. Devuelve la cantidad eliminada."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pacientes WHERE area_atencion = ?", (area,))
        total = cur.fetchone()[0]
        cur.execute("DELETE FROM pacientes WHERE area_atencion = ?", (area,))
        conn.commit()
        logger.info("Eliminados %s registros del área '%s'", total, area)
        return total
    except sqlite3.Error as e:
        logger.error("Error al eliminar registros del área '%s': %s", area, e)
        return -1
    finally:
        conn.close()



def obtener_historial_paciente(cedula: str) -> list[tuple]:
    """Historial completo de un paciente por cédula en todos los módulos.
    Devuelve (id, fecha, area, tipo_persona, edad, motivo, diagnostico, tratamiento)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, fecha_registro, area_atencion, tipo_persona, edad,
                   motivo, diagnostico, tratamiento, altura_cm, peso_kg, imc
            FROM   pacientes
            WHERE  cedula = ?
            ORDER  BY fecha_registro ASC
            """,
            (cedula,)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error al obtener historial cédula=%s: %s", cedula, e)
        return []
    finally:
        conn.close()


def obtener_datos_paciente(cedula: str) -> dict | None:
    """Datos personales del paciente más reciente con esa cédula."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT nombre, apellido, telefono, tipo_persona, fecha_nacimiento, edad "
            "FROM pacientes WHERE cedula = ? ORDER BY id DESC LIMIT 1",
            (cedula,)
        )
        row = cur.fetchone()
        if row:
            return dict(zip(["nombre","apellido","telefono","tipo_persona",
                              "fecha_nacimiento","edad"], row))
        return None
    except sqlite3.Error as e:
        logger.error("Error al obtener datos paciente cédula=%s: %s", cedula, e)
        return None
    finally:
        conn.close()



def obtener_paciente_por_id(paciente_id: int) -> dict | None:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, cedula, nombre, apellido, telefono, tipo_persona, "
            "fecha_nacimiento, edad, motivo, diagnostico, tratamiento, "
            "altura_cm, peso_kg, imc "
            "FROM pacientes WHERE id = ?",
            (paciente_id,)
        )
        row = cur.fetchone()
        if row:
            row = list(row)
            row[1] = _descifrar(row[1])   # cedula
            row[8] = _descifrar(row[8])   # motivo
            row[9] = _descifrar(row[9])   # diagnostico
            row[10] = _descifrar(row[10]) # tratamiento
            return dict(zip(["id","cedula","nombre","apellido","telefono","tipo_persona",
                              "fecha_nacimiento","edad","motivo","diagnostico","tratamiento",
                              "altura_cm","peso_kg","imc"], row))
        return None
    except sqlite3.Error as e:
        logger.error("Error al obtener paciente id=%s: %s", paciente_id, e)
        return None
    finally:
        conn.close()


def actualizar_paciente(paciente_id: int, cedula, nombre, apellido, telefono, tipo_persona,
                        fecha_nacimiento, edad, motivo, diagnostico, tratamiento,
                        altura_cm=None, peso_kg=None, imc=None) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE pacientes SET cedula=?, nombre=?, apellido=?, telefono=?, tipo_persona=?, "
            "fecha_nacimiento=?, edad=?, motivo=?, diagnostico=?, tratamiento=?, "
            "altura_cm=?, peso_kg=?, imc=? "
            "WHERE id=?",
            (_cifrar(cedula), nombre, apellido, telefono, tipo_persona,
             fecha_nacimiento, edad, _cifrar(motivo), _cifrar(diagnostico),
             _cifrar(tratamiento), altura_cm, peso_kg, imc, paciente_id)
        )
        conn.commit()
        logger.info("Paciente id=%s actualizado", paciente_id)
        return True
    except sqlite3.Error as e:
        logger.error("Error al actualizar paciente id=%s: %s", paciente_id, e)
        return False
    finally:
        conn.close()


def eliminar_paciente(paciente_id: int) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
        conn.commit()
        logger.info("Paciente id=%s eliminado", paciente_id)
        return True
    except sqlite3.Error as e:
        logger.error("Error al eliminar paciente id=%s: %s", paciente_id, e)
        return False
    finally:
        conn.close()


def contar_pacientes_mes() -> int:
    try:
        conn = _connect()
        cur  = conn.cursor()
        mes  = datetime.now().strftime("/%m/%Y")
        cur.execute("SELECT COUNT(*) FROM pacientes WHERE fecha_registro LIKE ?", (f"%{mes}%",))
        return cur.fetchone()[0]
    except sqlite3.Error as e:
        logger.error("Error al contar pacientes del mes: %s", e)
        return 0
    finally:
        conn.close()


def estadisticas_por_modulo() -> list[tuple]:
    """Devuelve (area, total) ordenado por total desc."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("""
            SELECT area_atencion, COUNT(*) as total
            FROM pacientes GROUP BY area_atencion ORDER BY total DESC
        """)
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("estadisticas_por_modulo: %s", e); return []
    finally: conn.close()


def estadisticas_por_tipo() -> list[tuple]:
    """Devuelve (tipo_persona, total)."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(tipo_persona, 'Sin tipo'), COUNT(*)
            FROM pacientes GROUP BY tipo_persona ORDER BY COUNT(*) DESC
        """)
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("estadisticas_por_tipo: %s", e); return []
    finally: conn.close()


def estadisticas_por_mes(ultimos_n: int = 6) -> list[tuple]:
    """Devuelve (mes_label, total) de los últimos N meses."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute("""
            SELECT substr(fecha_registro, 4, 7) as mes, COUNT(*)
            FROM pacientes
            GROUP BY mes ORDER BY mes DESC LIMIT ?
        """, (ultimos_n,))
        rows = cur.fetchall()
        return list(reversed(rows))
    except sqlite3.Error as e:
        logger.error("estadisticas_por_mes: %s", e); return []
    finally: conn.close()


def obtener_pacientes_rango(fecha_ini: str, fecha_fin: str, area: str = None) -> list[tuple]:
    """Pacientes entre fecha_ini y fecha_fin (DD/MM/AAAA).
    Devuelve (fecha, cedula, nombre, apellido, tipo_persona, area/motivo)."""
    try:
        from datetime import datetime as _dt
        def parse(f): return _dt.strptime(f.strip(), "%d/%m/%Y")
        ini = parse(fecha_ini); fin = parse(fecha_fin)
        conn = _connect(); cur = conn.cursor()
        if area:
            cur.execute(
                "SELECT fecha_registro, cedula, nombre, apellido, tipo_persona, motivo "
                "FROM pacientes WHERE area_atencion = ? ORDER BY fecha_registro ASC",
                (area,))
        else:
            cur.execute(
                "SELECT fecha_registro, cedula, nombre, apellido, tipo_persona, area_atencion "
                "FROM pacientes ORDER BY fecha_registro ASC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            try:
                fecha_row = _dt.strptime(row[0].split()[0], "%d/%m/%Y")
                if ini <= fecha_row <= fin:
                    result.append(row)
            except Exception:
                pass
        return result
    except sqlite3.Error as e:
        logger.error("obtener_pacientes_rango: %s", e); return []
    finally: conn.close()



def registrar_auditoria(usuario: str, accion: str,
                         detalle: str = "", modulo: str = "") -> None:
    """Registra un evento de auditoría en la BD."""
    try:
        conn = _connect(); cur = conn.cursor()
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cur.execute(
            "INSERT INTO auditoria (fecha, usuario, accion, detalle, modulo) "
            "VALUES (?,?,?,?,?)",
            (fecha, usuario, accion, detalle, modulo)
        )
        conn.commit()
        logger.info("AUDIT [%s] %s — %s", usuario, accion, detalle)
    except sqlite3.Error as e:
        logger.error("Error auditoria: %s", e)
    finally:
        conn.close()


def obtener_auditoria(limite: int = 100) -> list[tuple]:
    """Devuelve los últimos N eventos de auditoría."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute(
            "SELECT fecha, usuario, accion, detalle, modulo "
            "FROM auditoria ORDER BY id DESC LIMIT ?", (limite,)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error obtener_auditoria: %s", e)
        return []
    finally:
        conn.close()


def guardar_preferencia(clave: str, valor: str) -> None:
    """Guarda una preferencia de usuario en la BD."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS preferencias (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')
        cur.execute(
            "INSERT INTO preferencias (clave, valor) VALUES (?,?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (clave, valor)
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error guardar_preferencia '%s': %s", clave, e)
    finally:
        conn.close()


def obtener_preferencia(clave: str, defecto: str = "") -> str:
    """Lee una preferencia de usuario."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS preferencias (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS auditoria (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT NOT NULL,
                usuario     TEXT NOT NULL,
                accion      TEXT NOT NULL,
                detalle     TEXT,
                modulo      TEXT
            )
        ''')
        conn.commit()
        cur.execute("SELECT valor FROM preferencias WHERE clave = ?", (clave,))
        row = cur.fetchone()
        return row[0] if row else defecto
    except sqlite3.Error as e:
        logger.error("Error obtener_preferencia '%s': %s", clave, e)
        return defecto
    finally:
        conn.close()



def buscar_pacientes_global(busqueda: str) -> list[tuple]:
    """Búsqueda global: (id, fecha, nombre, apellido, cedula, tipo_persona, area, motivo)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        q    = f"%{busqueda}%"
        cur.execute(
            """
            SELECT id, fecha_registro, nombre, apellido, cedula, tipo_persona,
                   area_atencion, motivo
            FROM   pacientes
            WHERE  nombre   LIKE ?
               OR  apellido LIKE ?
               OR  cedula   LIKE ?
               OR  motivo   LIKE ?
            ORDER BY fecha_registro DESC
            """,
            (q, q, q, q)
        )
        rows = cur.fetchall()
        return [
            (r[0], r[1], r[2], r[3], _descifrar(r[4]), r[5],
             r[6], _descifrar(r[7]))
            for r in rows
        ]
    except sqlite3.Error as e:
        logger.error("Error en busqueda global: %s", e)
        return []
    finally:
        conn.close()



def obtener_todos_pacientes() -> list[tuple]:
    """Para PDF global: (fecha, cedula, nombre, apellido, tipo_persona, area)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT fecha_registro, cedula, nombre, apellido, tipo_persona, area_atencion "
            "FROM pacientes ORDER BY fecha_registro DESC"
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error al obtener todos los pacientes: %s", e)
        return []
    finally:
        conn.close()


def obtener_pacientes_por_area(area: str) -> list[tuple]:
    """Para PDF por área: (fecha, cedula, nombre, apellido, tipo_persona, motivo)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT fecha_registro, cedula, nombre, apellido, tipo_persona, motivo "
            "FROM pacientes WHERE area_atencion = ? ORDER BY fecha_registro DESC",
            (area,)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error al obtener pacientes por área '%s': %s", area, e)
        return []
    finally:
        conn.close()


# ================================================================
#  INSUMOS
# ================================================================

def eliminar_todos_insumos() -> int:
    """Elimina todos los insumos del inventario. Devuelve la cantidad eliminada."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM insumos")
        total = cur.fetchone()[0]
        cur.execute("DELETE FROM insumos")
        conn.commit()
        logger.info("Eliminados todos los insumos (%s)", total)
        return total
    except sqlite3.Error as e:
        logger.error("Error al eliminar todos los insumos: %s", e)
        return -1
    finally:
        conn.close()



def agregar_insumo(nombre: str, cantidad: int) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        # Cantidad anterior
        cur.execute("SELECT id, cantidad FROM insumos WHERE nombre = ?", (nombre,))
        row = cur.fetchone()
        cant_ant = row[1] if row else 0
        iid      = row[0] if row else None
        cur.execute(
            "INSERT INTO insumos (nombre, cantidad) VALUES (?,?) "
            "ON CONFLICT(nombre) DO UPDATE SET cantidad = cantidad + excluded.cantidad",
            (nombre, cantidad)
        )
        # Obtener id si era nuevo
        if not iid:
            cur.execute("SELECT id FROM insumos WHERE nombre = ?", (nombre,))
            iid = cur.fetchone()[0]
        cant_nueva = cant_ant + cantidad
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        cur.execute(
            "INSERT INTO movimientos_insumos (insumo_id, nombre, tipo, cantidad, "
            "cantidad_anterior, cantidad_nueva, fecha) VALUES (?,?,?,?,?,?,?)",
            (iid, nombre, "ENTRADA", cantidad, cant_ant, cant_nueva, fecha)
        )
        conn.commit()
        logger.info("Insumo '%s' +%s unidades", nombre, cantidad)
        return True
    except sqlite3.Error as e:
        logger.error("Error al agregar insumo '%s': %s", nombre, e)
        return False
    finally:
        conn.close()


def obtener_todos_insumos() -> list[tuple]:
    """Para PDF: devuelve (nombre, cantidad, estado) de todos los insumos."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT nombre, cantidad FROM insumos ORDER BY nombre ASC")
        rows = cur.fetchall()
        return [(n, c, "⚠️ Stock bajo" if c < 5 else "✅ Normal") for n, c in rows]
    except sqlite3.Error as e:
        logger.error("Error al obtener todos los insumos: %s", e)
        return []
    finally:
        conn.close()


def obtener_insumos(busqueda: str = "") -> list[tuple]:
    """Devuelve (id, nombre, cantidad)."""
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, nombre, cantidad FROM insumos WHERE nombre LIKE ? ORDER BY nombre ASC",
            (f"%{busqueda}%",)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error al obtener insumos: %s", e)
        return []
    finally:
        conn.close()


def usar_insumo(nombre: str, cantidad: int = 1) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT id, cantidad FROM insumos WHERE nombre = ?", (nombre,))
        row = cur.fetchone()
        if not row or row[1] < cantidad:
            logger.warning("No se pudo usar '%s': stock insuficiente", nombre)
            return False
        iid, cant_ant = row
        cur.execute(
            "UPDATE insumos SET cantidad = cantidad - ? WHERE nombre = ?",
            (cantidad, nombre)
        )
        cant_nueva = cant_ant - cantidad
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        cur.execute(
            "INSERT INTO movimientos_insumos (insumo_id, nombre, tipo, cantidad, "
            "cantidad_anterior, cantidad_nueva, fecha) VALUES (?,?,?,?,?,?,?)",
            (iid, nombre, "SALIDA", cantidad, cant_ant, cant_nueva, fecha)
        )
        conn.commit()
        logger.info("Insumo '%s' -%s unidades", nombre, cantidad)
        return True
    except sqlite3.Error as e:
        logger.error("Error al usar insumo '%s': %s", nombre, e)
        return False
    finally:
        conn.close()


def eliminar_insumo(insumo_id: int) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("DELETE FROM insumos WHERE id = ?", (insumo_id,))
        conn.commit()
        logger.info("Insumo id=%s eliminado", insumo_id)
        return True
    except sqlite3.Error as e:
        logger.error("Error al eliminar insumo id=%s: %s", insumo_id, e)
        return False
    finally:
        conn.close()


def actualizar_cantidad_insumo(insumo_id: int, nueva_cantidad: int) -> bool:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT nombre, cantidad FROM insumos WHERE id = ?", (insumo_id,))
        row = cur.fetchone()
        cant_ant = row[1] if row else 0
        nombre   = row[0] if row else "?"
        cur.execute("UPDATE insumos SET cantidad = ? WHERE id = ?",
                    (nueva_cantidad, insumo_id))
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        cur.execute(
            "INSERT INTO movimientos_insumos (insumo_id, nombre, tipo, cantidad, "
            "cantidad_anterior, cantidad_nueva, fecha) VALUES (?,?,?,?,?,?,?)",
            (insumo_id, nombre, "AJUSTE", abs(nueva_cantidad - cant_ant),
             cant_ant, nueva_cantidad, fecha)
        )
        conn.commit()
        logger.info("Insumo id=%s cantidad actualizada a %s", insumo_id, nueva_cantidad)
        return True
    except sqlite3.Error as e:
        logger.error("Error al actualizar insumo id=%s: %s", insumo_id, e)
        return False
    finally:
        conn.close()


def obtener_historial_insumo(insumo_id: int) -> list[tuple]:
    """Devuelve (fecha, tipo, cantidad, cant_anterior, cant_nueva) del insumo."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute(
            "SELECT fecha, tipo, cantidad, cantidad_anterior, cantidad_nueva "
            "FROM movimientos_insumos WHERE insumo_id = ? ORDER BY id DESC",
            (insumo_id,)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error historial insumo id=%s: %s", insumo_id, e)
        return []
    finally: conn.close()


def obtener_insumos_bajo_stock(limite: int = 5) -> list[tuple]:
    """Devuelve (id, nombre, cantidad) de insumos bajo el límite."""
    try:
        conn = _connect(); cur = conn.cursor()
        cur.execute(
            "SELECT id, nombre, cantidad FROM insumos WHERE cantidad < ? ORDER BY cantidad ASC",
            (limite,)
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        logger.error("Error obtener_insumos_bajo_stock: %s", e)
        return []
    finally: conn.close()


def contar_insumos_bajo_stock(limite: int = 5) -> int:
    try:
        conn = _connect()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM insumos WHERE cantidad < ?", (limite,))
        return cur.fetchone()[0]
    except sqlite3.Error as e:
        logger.error("Error al contar insumos bajo stock: %s", e)
        return 0
    finally:
        conn.close()
