"""
security.py — Utilidades de seguridad para SaluDigital
Hashing PBKDF2-SHA256 con salt aleatorio (estándar OWASP 2024).
"""

import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Genera salt:hash para almacenar en BD."""
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations=260_000
    ).hex()
    return f"{salt}:{key}"


def verify_password(password: str, stored: str) -> bool:
    """Verifica la contraseña contra el hash almacenado.
    Usa compare_digest para evitar timing attacks.
    """
    try:
        salt, key = stored.split(":")
        new_key = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), iterations=260_000
        ).hex()
        return secrets.compare_digest(key, new_key)
    except Exception as e:
        logger.error("Error al verificar contraseña: %s", e)
        return False


# ================================================================
#  VALIDACIÓN DE CONTRASEÑA SEGURA
# ================================================================

import re as _re

def validar_password(password: str) -> tuple[bool, str]:
    """Valida que la contraseña cumpla los requisitos de seguridad.
    Retorna (valida, mensaje_error).
    """
    if len(password) < 8:
        return False, "Debe tener al menos 8 caracteres."
    if not _re.search(r"[A-Z]", password):
        return False, "Debe contener al menos una letra mayúscula."
    if not _re.search(r"[0-9]", password):
        return False, "Debe contener al menos un número."
    if not _re.search(r"[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>\/?]", password):
        return False, "Debe contener al menos un símbolo (!@#$%^&*...)."
    return True, ""


# ================================================================
#  ENCRIPTACIÓN DE CAMPOS SENSIBLES
# ================================================================

import base64 as _b64
import hashlib as _hl
import os as _os

# Clave derivada del nombre del archivo de BD — única por instalación
_SALT_FILE = "saludigital.key"

def _get_key() -> bytes:
    """Obtiene o genera la clave de encriptación."""
    if _os.path.exists(_SALT_FILE):
        with open(_SALT_FILE, "rb") as f:
            return f.read()
    key = _os.urandom(32)
    with open(_SALT_FILE, "wb") as f:
        f.write(key)
    return key

def cifrar(texto: str) -> str:
    """Cifra un campo sensible con XOR + base64."""
    if not texto:
        return texto
    try:
        key   = _get_key()
        texto_bytes = texto.encode("utf-8")
        # Extender clave al tamaño del texto
        key_ext = (key * (len(texto_bytes) // len(key) + 1))[:len(texto_bytes)]
        cifrado = bytes(a ^ b for a, b in zip(texto_bytes, key_ext))
        return "ENC:" + _b64.b64encode(cifrado).decode()
    except Exception:
        return texto

def descifrar(texto: str) -> str:
    """Descifra un campo cifrado."""
    if not texto or not texto.startswith("ENC:"):
        return texto
    try:
        key   = _get_key()
        cifrado = _b64.b64decode(texto[4:])
        key_ext = (key * (len(cifrado) // len(key) + 1))[:len(cifrado)]
        return bytes(a ^ b for a, b in zip(cifrado, key_ext)).decode("utf-8")
    except Exception:
        return texto
