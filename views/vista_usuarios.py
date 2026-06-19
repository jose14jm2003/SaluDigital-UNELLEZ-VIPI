"""
views/vista_usuarios.py — Solo cambiar contraseña propia.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import logging

import database as db
from security import hash_password, verify_password, validar_password
from views.styles import ENTRY

logger = logging.getLogger(__name__)


class VistaUsuarios(ctk.CTkFrame):
    def __init__(self, parent, usuario_actual: dict):
        super().__init__(parent, fg_color="transparent")
        self._usuario_actual = usuario_actual
        self._build_ui()

    def _build_ui(self):
        # Centrar contenido
        ctk.CTkLabel(self, text="🔑 Cambiar Contraseña",
                     font=("Helvetica", 22, "bold"), text_color="black").pack(
                         anchor="w", padx=25, pady=(25, 5))

        ctk.CTkLabel(self,
                     text=f"Usuario: {self._usuario_actual.get('username', '')}",
                     font=("Helvetica", 13), text_color="#555").pack(
                         anchor="w", padx=25, pady=(0, 20))

        card = ctk.CTkFrame(self, fg_color="#F8F9F9", corner_radius=14,
                            border_width=1, border_color="#D5D8DC")
        card.pack(padx=25, pady=5, fill="x")

        self._entries = {}
        campos = [
            ("Contraseña actual",       "actual",  "*"),
            ("Nueva contraseña",        "nueva",   "*"),
            ("Confirmar nueva contraseña", "conf", "*"),
        ]

        for label, key, show in campos:
            f = ctk.CTkFrame(card, fg_color="transparent")
            f.pack(fill="x", padx=25, pady=10)
            ctk.CTkLabel(f, text=label, font=("Helvetica", 13, "bold"),
                         text_color="black").pack(anchor="w")
            ent = ctk.CTkEntry(f, show=show, height=42, **ENTRY)
            ent.pack(fill="x")
            self._entries[key] = ent

        self._lbl_msg = ctk.CTkLabel(card, text="",
                                      font=("Helvetica", 11, "bold"),
                                      text_color="#E74C3C")
        self._lbl_msg.pack(pady=(0, 5))

        ctk.CTkButton(card, text="💾 GUARDAR CONTRASEÑA",
                      fg_color="#2ecc71", height=44,
                      font=("Helvetica", 13, "bold"),
                      command=self._guardar).pack(
                          padx=25, pady=(5, 20), fill="x")

    def _guardar(self):
        actual = self._entries["actual"].get()
        nueva  = self._entries["nueva"].get()
        conf   = self._entries["conf"].get()

        # Validaciones
        if not actual or not nueva or not conf:
            self._lbl_msg.configure(text="Complete todos los campos.", text_color="#E74C3C")
            return
        if nueva != conf:
            self._lbl_msg.configure(text="Las contraseñas nuevas no coinciden.", text_color="#E74C3C")
            return
        valida, msg_error = validar_password(nueva)
        if not valida:
            self._lbl_msg.configure(text=msg_error, text_color="#E74C3C")
            return
        if actual == nueva:
            self._lbl_msg.configure(text="La nueva contraseña debe ser diferente a la actual.", text_color="#E74C3C")
            return

        # Verificar contraseña actual
        usuario = db.obtener_usuario(self._usuario_actual["username"])
        if not usuario or not verify_password(actual, usuario["password_hash"]):
            self._lbl_msg.configure(text="La contraseña actual es incorrecta.", text_color="#E74C3C")
            return

        # Obtener id
        todos = db.obtener_todos_usuarios()
        uid   = next((u[0] for u in todos
                      if u[1] == self._usuario_actual["username"]), None)
        if not uid:
            self._lbl_msg.configure(text="No se encontró el usuario.", text_color="#E74C3C")
            return

        ok = db.cambiar_password(uid, hash_password(nueva))
        if ok:
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "CAMBIO_PASSWORD", "Contraseña actualizada")
            self._lbl_msg.configure(text="✅ Contraseña actualizada correctamente.",
                                     text_color="#196F3D")
            for e in self._entries.values():
                e.delete(0, tk.END)
        else:
            self._lbl_msg.configure(text="No se pudo cambiar la contraseña.", text_color="#E74C3C")
