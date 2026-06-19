"""
views/vista_auditoria.py — Log de auditoría del sistema (solo admin).
"""

import customtkinter as ctk
import logging
import database as db

logger = logging.getLogger(__name__)

COLOR_ACCION = {
    "LOGIN":             ("#EAFAF1", "#196F3D", "🔑"),
    "LOGOUT":            ("#F9F9F9", "#555",    "🚪"),
    "LOGOUT_AUTO":       ("#FEF9E7", "#D4AC0D", "⏰"),
    "REGISTRO_PACIENTE": ("#EAF4FB", "#1A5276", "➕"),
    "ELIMINAR_PACIENTE": ("#FDEDEC", "#C0392B", "🗑️"),
    "BORRAR_TODO_AREA":  ("#FDEDEC", "#C0392B", "⚠️"),
    "CAMBIO_PASSWORD":   ("#F5EEF8", "#6C3483", "🔒"),
    "RESTAURAR_BD":      ("#FEF9E7", "#D4AC0D", "♻️"),
}


class VistaAuditoria(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        # Encabezado
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=25, pady=(20, 5))
        ctk.CTkLabel(head, text="🔍 Registro de Auditoría",
                     font=("Helvetica", 22, "bold"), text_color="black").pack(side="left")
        ctk.CTkButton(head, text="🔄 Actualizar", fg_color="#34495E",
                      width=120, command=self._cargar).pack(side="right")

        # Cabecera tabla
        cab = ctk.CTkFrame(self, fg_color="#000066", corner_radius=8)
        cab.pack(fill="x", padx=25, pady=(8, 0))
        for txt, w in [("Fecha/Hora", 150), ("Usuario", 120),
                       ("Acción", 160), ("Módulo", 120), ("Detalle", 0)]:
            ctk.CTkLabel(cab, text=txt, text_color="white",
                         font=("Helvetica", 11, "bold"),
                         width=w, anchor="w").pack(side="left", padx=8, pady=8)

        # Lista
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="white", border_width=1)
        self._scroll.pack(fill="both", expand=True, padx=25, pady=(2, 15))
        self._cargar()

    def _cargar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        eventos = db.obtener_auditoria(200)
        if not eventos:
            ctk.CTkLabel(self._scroll, text="Sin eventos registrados.",
                         text_color="gray").pack(pady=15)
            return

        for i, (fecha, usuario, accion, detalle, modulo) in enumerate(eventos):
            bg, fg, icono = COLOR_ACCION.get(accion, ("#F9F9F9", "#333", "•"))
            row = ctk.CTkFrame(self._scroll,
                               fg_color="#F9F9F9" if i % 2 == 0 else "white",
                               corner_radius=0)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=fecha, text_color="#555",
                         font=("Helvetica", 10), width=150,
                         anchor="w").pack(side="left", padx=8, pady=6)

            ctk.CTkLabel(row, text=usuario, text_color="#1A5276",
                         font=("Helvetica", 10, "bold"), width=120,
                         anchor="w").pack(side="left", padx=4)

            # Badge acción
            badge = ctk.CTkFrame(row, fg_color=bg, corner_radius=6, width=160)
            badge.pack(side="left", padx=4)
            ctk.CTkLabel(badge, text=f"{icono} {accion}", text_color=fg,
                         font=("Helvetica", 9, "bold")).pack(padx=6, pady=3)

            ctk.CTkLabel(row, text=modulo or "—", text_color="#888",
                         font=("Helvetica", 10), width=120,
                         anchor="w").pack(side="left", padx=4)

            ctk.CTkLabel(row, text=detalle or "—", text_color="#333",
                         font=("Helvetica", 10), anchor="w",
                         wraplength=350).pack(side="left", padx=4,
                                              fill="x", expand=True)
