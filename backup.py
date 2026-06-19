"""
backup.py — Utilidad de backup automático de la base de datos.
Crea una copia en la carpeta backups/ al iniciar sesión.
Conserva solo los últimos MAX_BACKUPS archivos.
"""

import os
import shutil
import logging
from datetime import datetime

logger    = logging.getLogger(__name__)
DB_PATH   = "salud_unellez.db"
BACKUP_DIR = "backups"
MAX_BACKUPS = 5


def hacer_backup() -> str | None:
    """Crea un backup con timestamp. Devuelve la ruta o None si falla."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        if not os.path.exists(DB_PATH):
            logger.warning("BD no encontrada para backup: %s", DB_PATH)
            return None

        ahora     = datetime.now()
        # Nombre legible: Backup_05-Jun-2026_15h24m30s.db
        timestamp = ahora.strftime("%d-%b-%Y_%Hh%Mm%Ss")
        dest = os.path.join(BACKUP_DIR, f"Backup_{timestamp}.db")
        shutil.copy2(DB_PATH, dest)
        logger.info("Backup creado: %s", dest)

        _limpiar_backups_antiguos()
        return dest

    except Exception as e:
        logger.error("Error al crear backup: %s", e)
        return None


def _limpiar_backups_antiguos():
    """Elimina backups más allá del límite MAX_BACKUPS."""
    try:
        archivos = sorted([
            os.path.join(BACKUP_DIR, f)
            for f in os.listdir(BACKUP_DIR)
            if (f.startswith("Backup_") or f.startswith("salud_unellez_"))
            and f.endswith(".db")
        ])
        while len(archivos) > MAX_BACKUPS:
            os.remove(archivos.pop(0))
            logger.info("Backup antiguo eliminado.")
    except Exception as e:
        logger.error("Error al limpiar backups: %s", e)


def listar_backups() -> list[dict]:
    """Devuelve lista de backups disponibles con nombre, ruta y fecha."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return []
        resultado = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if (f.startswith("Backup_") or f.startswith("salud_unellez_")) and f.endswith(".db"):
                ruta = os.path.join(BACKUP_DIR, f)
                # Extraer fecha del nombre
                ts = f.replace("Backup_","").replace("salud_unellez_","").replace(".db","")
                try:
                    fecha = datetime.strptime(ts, "%d-%b-%Y_%Hh%Mm%Ss").strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    try:
                        fecha = datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        fecha = ts
                size = os.path.getsize(ruta)
                resultado.append({"nombre": f, "ruta": ruta,
                                  "fecha": fecha, "size": size})
        return resultado
    except Exception as e:
        logger.error("Error al listar backups: %s", e)
        return []


def restaurar_backup(ruta: str) -> bool:
    """Restaura la BD desde un backup."""
    try:
        shutil.copy2(ruta, DB_PATH)
        logger.info("BD restaurada desde: %s", ruta)
        return True
    except Exception as e:
        logger.error("Error al restaurar backup '%s': %s", ruta, e)
        return False
