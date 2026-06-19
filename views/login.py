"""
views/login.py — Login moderno con foto de fondo y logo.
"""

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import logging

import database as db
from security import verify_password

logger = logging.getLogger(__name__)


class LoginView(ctk.CTkFrame):
    MAX_INTENTOS = 3

    def __init__(self, parent, on_login_success):
        super().__init__(parent, fg_color="#0a0a2e")
        self._on_success = on_login_success
        self._intentos   = 0
        self._bloqueado  = False
        self._build_ui()

    # ----------------------------------------------------------

    def _build_ui(self):
        # ── Fondo completo con foto ───────────────────────────
        try:
            bg = Image.open("assets/fondo_unellez.png").convert("RGB")
            bg = bg.resize((1920, 1080), Image.LANCZOS)
            # Oscurecer bastante para contraste
            bg = ImageEnhance.Brightness(bg).enhance(0.35)
            self._bg_img = ctk.CTkImage(bg, size=(1920, 1080))
            ctk.CTkLabel(self, image=self._bg_img, text="").place(
                x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            logger.info("Fondo no cargado: %s", e)

        # ── Card: borde naranja exterior + interior azul ─────
        outer = ctk.CTkFrame(self, width=502, height=622,
                             corner_radius=22, fg_color="#E67E22")
        outer.place(relx=0.5, rely=0.5, anchor="center")
        outer.pack_propagate(False)

        card = ctk.CTkFrame(outer, width=498, height=618,
                            corner_radius=19,
                            fg_color="#0d0d35")
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # ── Logo ─────────────────────────────────────────────
        logo = self._logo_circular("assets/logo_unellez.png", (135, 135))
        if logo:
            # Añadir borde blanco al logo
            bordered = Image.new("RGBA", (145, 145), (255, 255, 255, 0))
            mask_border = Image.new("L", (145, 145), 0)
            ImageDraw.Draw(mask_border).ellipse((0, 0, 144, 144), fill=255)
            white_circle = Image.new("RGBA", (145, 145), (255, 255, 255, 255))
            bordered.paste(white_circle, (0, 0), mask_border)
            logo_resized = logo.resize((133, 133), Image.LANCZOS)
            bordered.paste(logo_resized, (6, 6), logo_resized)
            self._logo_img = ctk.CTkImage(bordered, size=(135, 135))
            ctk.CTkLabel(card, image=self._logo_img, text="",
                         fg_color="transparent").pack(pady=(28, 0))

        # ── Títulos ───────────────────────────────────────────
        ctk.CTkLabel(card, text="SaluDigital",
                     font=("Helvetica", 28, "bold"),
                     text_color="white").pack(pady=(8, 0))
        ctk.CTkLabel(card, text="UNELLEZ · VIPI",
                     font=("Helvetica", 12),
                     text_color="#E67E22").pack(pady=(0, 20))

        # ── Separador ────────────────────────────────────────
        sep = ctk.CTkFrame(card, height=1, fg_color="#333366", corner_radius=0)
        sep.pack(fill="x", padx=40, pady=(0, 20))

        # ── Campos ───────────────────────────────────────────
        ENTRY_STYLE = dict(
            fg_color="#0f0f3d",
            border_color="#E67E22",
            border_width=1,
            text_color="white",
            placeholder_text_color="#6666aa",
            corner_radius=10,
        )

        # Usuario
        user_frame = ctk.CTkFrame(card, fg_color="transparent")
        user_frame.pack(fill="x", padx=45, pady=(0, 12))
        ctk.CTkLabel(user_frame, text="USUARIO",
                     font=("Helvetica", 10, "bold"),
                     text_color="#E67E22").pack(anchor="w", pady=(0, 4))
        self._ent_user = ctk.CTkEntry(user_frame,
                                       placeholder_text="Ingresa tu usuario",
                                       height=44, **ENTRY_STYLE)
        self._ent_user.pack(fill="x")

        # Contraseña
        pass_frame = ctk.CTkFrame(card, fg_color="transparent")
        pass_frame.pack(fill="x", padx=45, pady=(0, 8))
        ctk.CTkLabel(pass_frame, text="CONTRASEÑA",
                     font=("Helvetica", 10, "bold"),
                     text_color="#E67E22").pack(anchor="w", pady=(0, 4))
        self._ent_pass = ctk.CTkEntry(pass_frame,
                                       placeholder_text="Ingresa tu contraseña",
                                       show="*", height=44, **ENTRY_STYLE)
        self._ent_pass.pack(fill="x")

        # Error label
        self._lbl_error = ctk.CTkLabel(card, text="",
                                        text_color="#ff4444",
                                        font=("Helvetica", 10, "bold"),
                                        wraplength=380)
        self._lbl_error.pack(pady=(4, 0))

        # ── Botón INGRESAR ────────────────────────────────────
        self._btn = ctk.CTkButton(
            card, text="INGRESAR",
            command=self._intentar_login,
            width=410, height=46,
            corner_radius=10,
            fg_color="#E67E22",
            hover_color="#CA6F1E",
            text_color="white",
            font=("Helvetica", 14, "bold"))
        self._btn.pack(padx=45, pady=(12, 0))

        # ── Franja inferior ───────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color="#333366",
                     corner_radius=0).pack(fill="x", padx=40, pady=(20, 8))
        ctk.CTkLabel(card, text="Sistema de Gestión de Salud",
                     font=("Helvetica", 10),
                     text_color="#555588").pack()

        # Binds
        self._ent_user.bind("<Return>", lambda e: self._ent_pass.focus())
        self._ent_pass.bind("<Return>", lambda e: self._intentar_login())

    # ----------------------------------------------------------

    def _logo_circular(self, ruta, size):
        try:
            img  = Image.open(ruta).convert("RGBA").resize(size, Image.LANCZOS)
            mask = Image.new("L", size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size[0]-1, size[1]-1), fill=255)
            out  = Image.new("RGBA", size, (0, 0, 0, 0))
            out.paste(img, (0, 0), mask=mask)
            return out
        except Exception as e:
            logger.warning("Error logo: %s", e)
            return None

    def _intentar_login(self):
        if self._bloqueado:
            self._lbl_error.configure(
                text="Acceso bloqueado. Contacte al administrador.")
            return

        username = self._ent_user.get().strip()
        password = self._ent_pass.get()

        if not username or not password:
            self._lbl_error.configure(text="Complete usuario y contraseña.")
            return

        usuario = db.obtener_usuario(username)

        if usuario and usuario["activo"] == 1 and \
                verify_password(password, usuario["password_hash"]):
            logger.info("Sesión iniciada: %s", username)
            self._intentos = 0
            self._on_success({"username": username, "rol": usuario["rol"]})
        else:
            self._intentos += 1
            restantes = self.MAX_INTENTOS - self._intentos
            logger.warning("Login fallido '%s' (%d/%d)",
                           username, self._intentos, self.MAX_INTENTOS)
            if self._intentos >= self.MAX_INTENTOS:
                self._bloqueado = True
                self._btn.configure(state="disabled", fg_color="#555")
                self._lbl_error.configure(
                    text="Demasiados intentos. Acceso bloqueado.")
            else:
                self._lbl_error.configure(
                    text=f"Credenciales incorrectas. "
                         f"Intentos restantes: {restantes}")
            self._ent_pass.delete(0, tk.END)

    def reset(self):
        self._intentos  = 0
        self._bloqueado = False
        self._btn.configure(state="normal", fg_color="#E67E22")
        self._lbl_error.configure(text="")
        self._ent_user.delete(0, tk.END)
        self._ent_pass.delete(0, tk.END)
