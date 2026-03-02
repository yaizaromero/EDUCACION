# backend/db.py
from pathlib import Path
import os
import sqlite3
from contextlib import contextmanager
import re
from typing import Optional

DEFAULT_DB = "data/palabria.db"

def get_db_path():
    env_db = os.getenv("DB_PATH")
    if env_db:
        p = Path(env_db)
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    local_db = Path(DEFAULT_DB)
    local_db.parent.mkdir(parents=True, exist_ok=True)
    return str(local_db)

DB_PATH = get_db_path()

DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  filename TEXT,
  uploaded_at TEXT DEFAULT (datetime('now')),
  text_hash TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS metrics(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value REAL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS usage_stats(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  event TEXT NOT NULL,
  value REAL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bolsa_palabras(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  categoria TEXT NOT NULL,
  palabra_fallada TEXT NOT NULL,
  palabra_correcta TEXT NOT NULL,
  aciertos_restantes INTEGER DEFAULT 3,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id),
  UNIQUE(user_id, palabra_fallada, categoria)
);

CREATE TABLE IF NOT EXISTS user_levels(
  user_id INTEGER PRIMARY KEY,
  nivel_general TEXT DEFAULT 'Sin datos',
  nivel_b_v TEXT DEFAULT 'Sin datos',
  nivel_g_j TEXT DEFAULT 'Sin datos',
  nivel_y_ll TEXT DEFAULT 'Sin datos',
  nivel_h TEXT DEFAULT 'Sin datos',
  nivel_c_z TEXT DEFAULT 'Sin datos',
  nivel_tildes TEXT DEFAULT 'Sin datos',
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_badges(
  user_id INTEGER NOT NULL,
  badge_name TEXT NOT NULL,
  earned_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, badge_name),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_profiles(
  user_id INTEGER PRIMARY KEY,
  avatar TEXT DEFAULT '🐼',
  current_streak INTEGER DEFAULT 1,
  last_login_date TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

def init_db():
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(DDL)
        con.commit()
    finally:
        con.close()

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        yield con
        con.commit()
    finally:
        con.close()

_ALLOWED = re.compile(r"^[A-Za-z0-9_\-\.]{1,32}$")

def sanitize_username(username: str) -> str:
    username = (username or "").strip()
    if not username:
        raise ValueError("username vacío")
    if not _ALLOWED.match(username):
        raise ValueError("username inválido: usa letras, números, _ - . (máx 32)")
    return username

def user_exists(username: str) -> bool:
    username = sanitize_username(username)
    with db() as con:
        row = con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        return bool(row)

def create_user(username: str) -> int:
    username = sanitize_username(username)
    with db() as con:
        cur = con.execute("INSERT INTO users(username) VALUES(?)", (username,))
        return cur.lastrowid

def get_user_id(username: str) -> Optional[int]:
    username = sanitize_username(username)
    with db() as con:
        row = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        return row["id"] if row else None

def ensure_user(username: str) -> int:
    username = sanitize_username(username)
    with db() as con:
        row = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if row:
            return row["id"]
        cur = con.execute("INSERT INTO users(username) VALUES(?)", (username,))
        return cur.lastrowid

def record_usage(user_id: int, event: str, value: float | None = None):
    with db() as con:
        con.execute(
            "INSERT INTO usage_stats(user_id, event, value) VALUES(?,?,?)",
            (user_id, event, value)
        )

def record_login_ts(user_id: int, epoch_seconds: float):
    record_usage(user_id, "login_ts", float(epoch_seconds))
    record_usage(user_id, "heartbeat", float(epoch_seconds))

def close_open_session(user_id: int, now_epoch: float, idle_grace: float = 1800.0):
    with db() as con:
        row_login = con.execute("""
            SELECT id, value FROM usage_stats
            WHERE user_id=? AND event='login_ts'
            ORDER BY id DESC LIMIT 1
        """, (user_id,)).fetchone()
        if not row_login:
            return
        last_login_id = int(row_login["id"])
        start_ts = float(row_login["value"] or 0.0)

        row_sd = con.execute("""
            SELECT id FROM usage_stats
            WHERE user_id=? AND event='session_duration' AND id>? 
            ORDER BY id DESC LIMIT 1
        """, (user_id, last_login_id)).fetchone()
        if row_sd:
            return

        row_hb = con.execute("""
            SELECT value FROM usage_stats
            WHERE user_id=? AND event='heartbeat' AND id>=?
            ORDER BY id DESC LIMIT 1
        """, (user_id, last_login_id)).fetchone()
        hb_ts = float(row_hb["value"]) if row_hb and row_hb["value"] is not None else None

        end_ts = float(now_epoch)
        if hb_ts is not None and (end_ts - hb_ts) <= idle_grace + 5:
            end_ts = hb_ts

        dur = max(0.0, end_ts - start_ts)
        dur = min(max(dur, 10.0), 12 * 3600.0)

        con.execute("INSERT INTO usage_stats(user_id, event, value) VALUES(?,?,?)",
                    (user_id, "session_duration", float(dur)))
        con.execute("INSERT INTO usage_stats(user_id, event, value) VALUES(?,?,NULL)",
                    (user_id, "logout"))

def create_document(user_id: int, filename: str | None, text_hash: str | None) -> int:
    with db() as con:
        cur = con.execute(
            "INSERT INTO documents(user_id, filename, text_hash) VALUES(?,?,?)",
            (user_id, filename, text_hash)
        )
        return cur.lastrowid

def insert_metric(document_id: int, name: str, value: float):
    with db() as con:
        con.execute(
            "INSERT INTO metrics(document_id, metric_name, metric_value) VALUES(?,?,?)",
            (document_id, name, float(value))
        )

def get_user_overview(username: str):
    username = sanitize_username(username)
    with db() as con:
        row_docs = con.execute("""
            SELECT COUNT(*) AS docs
            FROM documents d
            JOIN users u ON u.id = d.user_id
            WHERE u.username=?
        """, (username,)).fetchone()
        total_docs = int(row_docs["docs"] if row_docs else 0)

        avg_rows = con.execute("""
            WITH latest AS (
                SELECT m.* FROM metrics m
                JOIN (
                    SELECT document_id, metric_name, MAX(id) AS max_id
                    FROM metrics GROUP BY document_id, metric_name
                ) mx ON mx.max_id = m.id
            )
            SELECT l.metric_name, AVG(l.metric_value) AS avg_value
            FROM latest l
            JOIN documents d ON d.id = l.document_id
            JOIN users u ON u.id = d.user_id
            WHERE u.username=?
            GROUP BY l.metric_name
        """, (username,)).fetchall()

        row_docs_with_tu = con.execute("""
            WITH latest_tu AS (
                SELECT m.document_id, m.metric_value
                FROM metrics m
                JOIN (
                    SELECT document_id, MAX(id) AS max_id
                    FROM metrics
                    WHERE metric_name='frases_con_tu_impersonal'
                    GROUP BY document_id
                ) mx ON mx.max_id = m.id
            )
            SELECT COUNT(DISTINCT d.id) AS docs_with_tu
            FROM documents d
            JOIN users u ON u.id = d.user_id
            LEFT JOIN latest_tu lt ON lt.document_id = d.id
            WHERE u.username=? AND COALESCE(lt.metric_value,0) > 0
        """, (username,)).fetchone()
        docs_with_tu = int(row_docs_with_tu["docs_with_tu"] if row_docs_with_tu else 0)
        docs_with_tu_percent = round((docs_with_tu * 100.0 / total_docs), 1) if total_docs > 0 else 0.0

        row_docs_no_changes = con.execute("""
            WITH latest_user_changes AS (
                SELECT m.document_id, m.metric_value
                FROM metrics m
                JOIN (
                    SELECT document_id, MAX(id) AS max_id
                    FROM metrics
                    WHERE metric_name='cambios_realizados_usuario'
                    GROUP BY document_id
                ) mx ON mx.max_id = m.id
            )
            SELECT COUNT(DISTINCT d.id) AS docs_no_changes
            FROM documents d
            JOIN users u ON u.id = d.user_id
            LEFT JOIN latest_user_changes luc ON luc.document_id = d.id
            WHERE u.username=? AND COALESCE(luc.metric_value,0) = 0
        """, (username,)).fetchone()

        docs_no_changes = int(row_docs_no_changes["docs_no_changes"] if row_docs_no_changes else 0)
        docs_no_changes_percent = round((docs_no_changes * 100.0 / total_docs), 1) if total_docs > 0 else 0.0

        usage_rows = con.execute("""
            SELECT event, COUNT(*) AS n, AVG(value) AS avg_val
            FROM usage_stats us
            JOIN users u ON u.id = us.user_id
            WHERE u.username=?
            GROUP BY event
        """, (username,)).fetchall()

        login_days_row = con.execute("""
            SELECT COUNT(DISTINCT date(us.created_at)) AS days
            FROM usage_stats us
            JOIN users u ON u.id = us.user_id
            WHERE u.username=? AND us.event='login'
        """, (username,)).fetchone()

        avg_session_row = con.execute("""
            SELECT AVG(us.value) AS avg_sec
            FROM usage_stats us
            JOIN users u ON u.id = us.user_id
            WHERE u.username=? AND us.event='session_duration'
        """, (username,)).fetchone()

        return {
            "docs": total_docs,
            "avg_metrics": {r["metric_name"]: r["avg_value"] for r in avg_rows},
            "usage": {r["event"]: {"count": r["n"], "avg": r["avg_val"]} for r in usage_rows},
            "login_days": int(login_days_row["days"] if login_days_row else 0),
            "docs_with_tu_percent": docs_with_tu_percent,
            "docs_no_changes_percent": docs_no_changes_percent,
            "avg_session_seconds": float(avg_session_row["avg_sec"] or 0.0),
        }

def get_user_weekly_activity(username: str):
    """
    Devuelve los últimos 7 días con su tiempo total de conexión (sumado)
    y una categoría de actividad.
    """
    username = sanitize_username(username)
    with db() as con:
        rows = con.execute("""
            SELECT 
                date(us.created_at) AS day,
                SUM(CASE WHEN us.event='session_duration' THEN us.value ELSE 0 END) AS total_seconds
            FROM usage_stats us
            JOIN users u ON u.id = us.user_id
            WHERE u.username=? 
              AND date(us.created_at) >= date('now', '-6 days')
            GROUP BY date(us.created_at)
            ORDER BY day ASC
        """, (username,)).fetchall()

        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        data = []
        seconds_by_day = {r["day"]: float(r["total_seconds"] or 0) for r in rows}

        for d in days:
            secs = seconds_by_day.get(d, 0)
            if secs == 0:
                cat = "No inició sesión"
            elif secs <= 300:
                cat = "Hasta 5 min"
            elif secs <= 900:
                cat = "Hasta 15 min"
            elif secs <= 1800:
                cat = "Hasta 30 min"
            else:
                cat = "Más de 30 min"
            data.append({"day": d, "total_seconds": secs, "categoria": cat})
        return data

def get_user_documents(username: str):
    username = sanitize_username(username)
    with db() as con:
        rows = con.execute("""
            SELECT d.id, d.filename, d.uploaded_at
            FROM documents d
            JOIN users u ON u.id = d.user_id
            WHERE u.username=?
            ORDER BY d.id DESC
        """, (username,)).fetchall()
        return [dict(r) for r in rows]

def get_document_metrics(doc_id: int):
    with db() as con:
        rows = con.execute("""
            SELECT metric_name, metric_value, created_at
            FROM metrics
            WHERE document_id=?
            ORDER BY id
        """, (doc_id,)).fetchall()
        return [dict(r) for r in rows]

def delete_document(doc_id: int) -> bool:
    with db() as con:
        con.execute("DELETE FROM metrics WHERE document_id=?", (doc_id,))
        cur = con.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        return cur.rowcount > 0
    
def agregar_palabras_bolsa(user_id: int, listas_errores: dict):
    """Guarda los errores en la bolsa. Si ya existía el error, reinicia los aciertos a 3."""
    with db() as con:
        for categoria, errores in listas_errores.items():
            for palabra_fallada, palabra_correcta in errores:
                # Upsert: Si la palabra ya está en la bolsa, le volvemos a poner 3 aciertos restantes
                con.execute("""
                    INSERT INTO bolsa_palabras (user_id, categoria, palabra_fallada, palabra_correcta, aciertos_restantes)
                    VALUES (?, ?, ?, ?, 3)
                    ON CONFLICT(user_id, palabra_fallada, categoria) 
                    DO UPDATE SET aciertos_restantes = 3, palabra_correcta = excluded.palabra_correcta
                """, (user_id, categoria, palabra_fallada, palabra_correcta))

def obtener_palabras_repaso(username: str):
    """Devuelve las palabras que al usuario le quedan por acertar."""
    user_id = get_user_id(username)
    with db() as con:
        rows = con.execute("""
            SELECT id, categoria, palabra_fallada, palabra_correcta, aciertos_restantes
            FROM bolsa_palabras
            WHERE user_id=? AND aciertos_restantes > 0
            ORDER BY RANDOM() -- Para que los ejercicios salgan mezclados
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def registrar_acierto_palabra(palabra_id: int):
    """Resta 1 al contador de aciertos. Si llega a 0, ya no aparecerá."""
    with db() as con:
        con.execute("""
            UPDATE bolsa_palabras 
            SET aciertos_restantes = aciertos_restantes - 1 
            WHERE id=? AND aciertos_restantes > 0
        """, (palabra_id,))


def get_user_error_progress(username: str, limit: int = 15):
    """
    Devuelve los últimos `limit` textos para cada categoría donde hubo palabras susceptibles,
    calculando el % de error.
    """
    username = sanitize_username(username)
    categorias = ["b_v", "g_j", "y_ll", "h", "c_z", "tildes"]
    resultado = []
    
    with db() as con:
        for cat in categorias:
            # Query que junta la métrica de error y la de susceptibles del mismo documento
            rows = con.execute(f"""
                SELECT d.id AS doc_id, d.uploaded_at,
                       m_err.metric_value AS errores,
                       m_sus.metric_value AS susceptibles
                FROM documents d
                JOIN users u ON u.id = d.user_id
                JOIN metrics m_err ON m_err.document_id = d.id AND m_err.metric_name = 'errores_{cat}'
                JOIN metrics m_sus ON m_sus.document_id = d.id AND m_sus.metric_name = 'susceptibles_{cat}'
                WHERE u.username = ? AND m_sus.metric_value > 0
                ORDER BY d.id DESC
                LIMIT ?
            """, (username, limit)).fetchall()
            
            # Revertimos para que queden en orden cronológico ascendente (el más viejo primero para la gráfica)
            rows = list(reversed(rows))
            
            for index, r in enumerate(rows):
                err = float(r["errores"])
                sus = float(r["susceptibles"])
                porcentaje = (err / sus) * 100 if sus > 0 else 0
                resultado.append({
                    "categoria": cat.upper(),
                    "doc_index": index + 1,  # Eje X secuencial (1, 2, 3... 15)
                    "fecha": r["uploaded_at"],
                    "porcentaje_error": round(porcentaje, 2),
                    "doc_id": r["doc_id"]
                })
    return resultado

def calcular_nivel_ortografico(porcentaje_error: float) -> str:
    """Clasifica el nivel en función del % de error."""
    if porcentaje_error < 10.0:
        return "🟢 Avanzado"
    elif porcentaje_error <= 25.0:
        return "🟡 Medio"
    else:
        return "🔴 Bajo"

def actualizar_niveles_usuario(user_id: int, limit: int = 15):
    """
    Recalcula los niveles del usuario sumando los errores y susceptibles
    de los últimos 'limit' documentos y hace un UPSERT en la base de datos.
    """
    categorias = ["b_v", "g_j", "y_ll", "h", "c_z", "tildes"]
    niveles = {}
    
    total_errores_global = 0
    total_susceptibles_global = 0
    
    with db() as con:
        for cat in categorias:
            # Sumamos errores y susceptibles de los últimos N textos donde hubo opciones de fallar
            row = con.execute(f"""
                SELECT SUM(errores) as sum_err, SUM(susceptibles) as sum_sus FROM (
                    SELECT m_err.metric_value AS errores, m_sus.metric_value AS susceptibles
                    FROM documents d
                    JOIN metrics m_err ON m_err.document_id = d.id AND m_err.metric_name = 'errores_{cat}'
                    JOIN metrics m_sus ON m_sus.document_id = d.id AND m_sus.metric_name = 'susceptibles_{cat}'
                    WHERE d.user_id = ? AND m_sus.metric_value > 0
                    ORDER BY d.id DESC
                    LIMIT ?
                )
            """, (user_id, limit)).fetchone()
            
            sum_err = float(row["sum_err"] or 0)
            sum_sus = float(row["sum_sus"] or 0)
            
            total_errores_global += sum_err
            total_susceptibles_global += sum_sus
            
            if sum_sus > 0:
                porcentaje = (sum_err / sum_sus) * 100
                niveles[f"nivel_{cat}"] = calcular_nivel_ortografico(porcentaje)
            else:
                niveles[f"nivel_{cat}"] = "⚪ Sin datos"
        
        # Calcular el Nivel General
        if total_susceptibles_global > 0:
            porcentaje_global = (total_errores_global / total_susceptibles_global) * 100
            niveles["nivel_general"] = calcular_nivel_ortografico(porcentaje_global)
        else:
            niveles["nivel_general"] = "⚪ Sin datos"
            
        # Guardar en la base de datos (Upsert: Inserta o actualiza si ya existe)
        con.execute("""
            INSERT INTO user_levels (user_id, nivel_general, nivel_b_v, nivel_g_j, nivel_y_ll, nivel_h, nivel_c_z, nivel_tildes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                nivel_general=excluded.nivel_general,
                nivel_b_v=excluded.nivel_b_v,
                nivel_g_j=excluded.nivel_g_j,
                nivel_y_ll=excluded.nivel_y_ll,
                nivel_h=excluded.nivel_h,
                nivel_c_z=excluded.nivel_c_z,
                nivel_tildes=excluded.nivel_tildes,
                updated_at=datetime('now')
        """, (user_id, niveles["nivel_general"], niveles["nivel_b_v"], niveles["nivel_g_j"], 
              niveles["nivel_y_ll"], niveles["nivel_h"], niveles["nivel_c_z"], niveles["nivel_tildes"]))

def get_niveles_usuario(username: str):
    """Obtiene los niveles actuales del usuario."""
    uid = get_user_id(username)
    with db() as con:
        row = con.execute("SELECT * FROM user_levels WHERE user_id=?", (uid,)).fetchone()
        return dict(row) if row else None
    
def check_and_award_badges(user_id: int):
    """Comprueba las rachas de los últimos 15 textos y otorga insignias."""
    
    # 1. Medallas que van por porcentaje (< 10% de error)
    categorias_porcentaje = {
        "b_v": "dominio_b_v",
        "g_j": "dominio_g_j",
        "y_ll": "dominio_y_ll",
        "tildes": "dominio_tildes",
        "h": "dominio_h",
        "c_z": "dominio_c_z" # Por si quieres añadir la insignia de C/Z/S en el futuro
    }
    
    with db() as con:
        ya_ganadas = {r['badge_name'] for r in con.execute("SELECT badge_name FROM user_badges WHERE user_id=?", (user_id,)).fetchall()}
        ganadas_ahora = set(ya_ganadas)

        # A) Comprobar medallas de porcentaje (B/V, G/J, Y/LL, H, Tildes)
        for cat, badge_id in categorias_porcentaje.items():
            if badge_id in ya_ganadas:
                continue 

            rows = con.execute(f"""
                SELECT m_err.metric_value as err, m_sus.metric_value as sus
                FROM documents d
                JOIN metrics m_err ON m_err.document_id = d.id AND m_err.metric_name = 'errores_{cat}'
                JOIN metrics m_sus ON m_sus.document_id = d.id AND m_sus.metric_name = 'susceptibles_{cat}'
                WHERE d.user_id = ? AND m_sus.metric_value > 0
                ORDER BY d.id DESC LIMIT 15
            """, (user_id,)).fetchall()

            if len(rows) == 15:
                if all((float(r['err']) / float(r['sus']) * 100) < 10.0 for r in rows):
                    con.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, ?)", (user_id, badge_id))
                    ganadas_ahora.add(badge_id)

        # B) Comprobar medalla "Buena Escritura" (OTROS) -> Menos de 2 fallos
        if "dominio_otros" not in ya_ganadas:
            # Aquí solo buscamos los errores_otros de los últimos 15 textos analizados
            rows_otros = con.execute("""
                SELECT m_err.metric_value as err
                FROM documents d
                JOIN metrics m_err ON m_err.document_id = d.id AND m_err.metric_name = 'errores_otros'
                WHERE d.user_id = ?
                ORDER BY d.id DESC LIMIT 15
            """, (user_id,)).fetchall()
            
            # Condición: Tener 15 textos analizados y que en TODOS ellos el valor de errores_otros sea < 2 (0 o 1)
            if len(rows_otros) == 15:
                if all(float(r['err']) < 2 for r in rows_otros):
                    con.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, 'dominio_otros')", (user_id,))
                    ganadas_ahora.add("dominio_otros")

        # C) Comprobar la medalla MÁSTER (Tiene las 7 insignias básicas)
        if len([b for b in ganadas_ahora if b != "master_ortografia"]) >= 7:
            if "master_ortografia" not in ya_ganadas:
                con.execute("INSERT INTO user_badges (user_id, badge_name) VALUES (?, 'master_ortografia')", (user_id,))

def get_user_badges(username: str):
    """Devuelve la lista de insignias del usuario."""
    uid = get_user_id(username)
    with db() as con:
        rows = con.execute("SELECT badge_name FROM user_badges WHERE user_id=?", (uid,)).fetchall()
        return [r['badge_name'] for r in rows]
    
def update_user_streak(user_id: int):
    """Actualiza la racha de días seguidos del usuario."""
    from datetime import datetime, timedelta
    today = datetime.utcnow().date().isoformat()
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    
    with db() as con:
        row = con.execute("SELECT current_streak, last_login_date FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            con.execute("INSERT INTO user_profiles (user_id, avatar, current_streak, last_login_date) VALUES (?, '🐼', 1, ?)", (user_id, today))
        else:
            last_login = row["last_login_date"]
            streak = row["current_streak"]
            if last_login == yesterday:
                # Se conectó ayer, sube la racha
                con.execute("UPDATE user_profiles SET current_streak=?, last_login_date=? WHERE user_id=?", (streak + 1, today, user_id))
            elif last_login != today:
                # Perdió la racha (no se conectó ayer ni hoy), vuelve a 1
                con.execute("UPDATE user_profiles SET current_streak=1, last_login_date=? WHERE user_id=?", (today, user_id))

def get_user_profile(username: str):
    """Devuelve el avatar y la racha del usuario."""
    uid = get_user_id(username)
    with db() as con:
        row = con.execute("SELECT avatar, current_streak FROM user_profiles WHERE user_id=?", (uid,)).fetchone()
        if row: return dict(row)
        return {"avatar": "🐼", "current_streak": 1}

def update_user_avatar(username: str, avatar: str):
    uid = get_user_id(username)
    with db() as con:
        con.execute("UPDATE user_profiles SET avatar=? WHERE user_id=?", (avatar, uid))