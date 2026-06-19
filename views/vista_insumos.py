"""
views/vista_insumos.py — Inventario de insumos con historial y alertas.
"""

from tkinter import messagebox
import customtkinter as ctk
import logging

import database as db
from views.widgets import VentanaEditarInsumo
from views.styles import ENTRY, ENTRY_SEARCH

logger = logging.getLogger(__name__)

COLOR_TIPO = {
    "ENTRADA": ("#EAFAF1", "#196F3D", "📥"),
    "SALIDA":  ("#FDEDEC", "#C0392B", "📤"),
    "AJUSTE":  ("#EBF5FB", "#1A5276", "🔧"),
}


class VistaInsumos(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()
        self._verificar_alertas()

    # ----------------------------------------------------------

    def _build_ui(self):
        # ── Encabezado ────────────────────────────────────────
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=25, pady=(20, 5))
        ctk.CTkLabel(head, text="Inventario de Insumos",
                     font=("Helvetica", 20, "bold"), text_color="black").pack(side="left")
        ctk.CTkButton(head, text="📄 PDF INSUMOS", fg_color="#34495E", width=150,
                      command=self._generar_pdf).pack(side="right", padx=(4, 0))
        ctk.CTkButton(head, text="🗑️ BORRAR TODO", fg_color="#C0392B", width=140,
                      font=("Helvetica", 11, "bold"),
                      command=self._borrar_todos).pack(side="right", padx=(0, 4))

        # ── Formulario agregar ────────────────────────────────
        add_f = ctk.CTkFrame(self, fg_color="#F8F9F9", corner_radius=12, border_width=1)
        add_f.pack(fill="x", padx=25, pady=10)

        self._ent_nombre = ctk.CTkEntry(add_f, placeholder_text="Nombre del Insumo",
                                         width=280, **ENTRY)
        self._ent_nombre.grid(row=0, column=0, padx=15, pady=12)
        self._ent_cant = ctk.CTkEntry(add_f, placeholder_text="Cantidad",
                                       width=100, **ENTRY)
        self._ent_cant.grid(row=0, column=1, padx=5, pady=12)
        ctk.CTkButton(add_f, text="AÑADIR AL STOCK", fg_color="#2ecc71",
                      font=("Helvetica", 11, "bold"),
                      command=self._agregar).grid(row=0, column=2, padx=15)

        # ── Búsqueda ─────────────────────────────────────────
        self._bus = ctk.CTkEntry(self, placeholder_text="🔍 Buscar en inventario...",
                                  height=34, **ENTRY_SEARCH)
        self._bus.pack(fill="x", padx=25, pady=5)
        self._bus.bind("<KeyRelease>", lambda e: self._cargar())

        # ── Lista ─────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="white", border_width=1)
        self._scroll.pack(fill="both", expand=True, padx=25, pady=5)
        self._cargar()

    # ----------------------------------------------------------

    def _verificar_alertas(self):
        """Muestra alerta si hay insumos con stock bajo."""
        bajos = db.obtener_insumos_bajo_stock(5)
        if not bajos:
            return
        lista = "\n".join(f"  ⚠️  {n}  →  {c} unidades" for _, n, c in bajos)
        messagebox.showwarning(
            "⚠️ Alerta de Stock Bajo",
            f"Los siguientes insumos tienen menos de 5 unidades:\n\n{lista}\n\n"
            "Por favor reponga el inventario."
        )

    def _agregar(self):
        n = self._ent_nombre.get().strip().upper()
        c = self._ent_cant.get().strip()
        if not n:
            messagebox.showwarning("Aviso", "Ingrese el nombre del insumo.")
            return
        if not c.isdigit() or int(c) <= 0:
            messagebox.showwarning("Aviso", "Ingrese una cantidad válida mayor a 0.")
            return
        ok = db.agregar_insumo(n, int(c))
        if ok:
            self._ent_nombre.delete(0, "end")
            self._ent_cant.delete(0, "end")
            self._cargar()
        else:
            messagebox.showerror("Error", "No se pudo agregar el insumo.\nRevise logs/app.log.")

    def _cargar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        insumos = db.obtener_insumos(self._bus.get().strip())

        if not insumos:
            ctk.CTkLabel(self._scroll, text="Sin insumos registrados.",
                         text_color="gray").pack(pady=10)
            return

        for iid, nombre, cantidad in insumos:
            f = ctk.CTkFrame(self._scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)

            ctk.CTkLabel(f, text=nombre, text_color="black",
                         font=("Helvetica", 11, "bold"),
                         width=250, anchor="w").pack(side="left", padx=15)

            color = "#e74c3c" if cantidad < 5 else "#2c3e50"
            # Badge cantidad
            badge_bg = "#FDEDEC" if cantidad < 5 else "#EAFAF1"
            badge = ctk.CTkFrame(f, fg_color=badge_bg, corner_radius=8)
            badge.pack(side="left", padx=4)
            ctk.CTkLabel(badge, text=f"{'⚠️ ' if cantidad < 5 else ''}{cantidad} uds",
                         text_color=color,
                         font=("Helvetica", 12, "bold")).pack(padx=10, pady=3)

            ctk.CTkButton(f, text="USAR 1", fg_color="#34495E", width=80, height=28,
                          command=lambda n=nombre: self._usar(n)).pack(side="right", padx=4)
            ctk.CTkButton(f, text="✏️ Editar", fg_color="#2980B9", width=80, height=28,
                          command=lambda i=iid, n=nombre, c=cantidad:
                              VentanaEditarInsumo(self, i, n, c, self._cargar)
                          ).pack(side="right", padx=4)
            ctk.CTkButton(f, text="📋 Historial", fg_color="#8E44AD", width=95, height=28,
                          command=lambda i=iid, n=nombre:
                              VentanaHistorialInsumo(self, i, n)
                          ).pack(side="right", padx=4)
            ctk.CTkButton(f, text="🗑️ Borrar", fg_color="#E74C3C", width=80, height=28,
                          command=lambda i=iid, n=nombre:
                              self._eliminar(i, n)).pack(side="right", padx=4)

    def _usar(self, nombre):
        ok = db.usar_insumo(nombre)
        if not ok:
            messagebox.showwarning("Stock", f"'{nombre}' no tiene unidades disponibles.")
        else:
            # Verificar si quedó bajo stock tras el uso
            insumos = db.obtener_insumos(nombre)
            if insumos and insumos[0][2] < 5:
                messagebox.showwarning(
                    "⚠️ Stock Bajo",
                    f"'{nombre}' tiene solo {insumos[0][2]} unidades restantes.\n"
                    "Considere reponer el inventario."
                )
        self._cargar()

    def _eliminar(self, iid, nombre):
        if messagebox.askyesno("Confirmar",
                               f"¿Eliminar '{nombre}' del inventario?\n"
                               "Esta acción no se puede deshacer."):
            ok = db.eliminar_insumo(iid)
            if ok:
                self._cargar()
            else:
                messagebox.showerror("Error", "No se pudo eliminar.\nRevise logs/app.log.")

    def _borrar_todos(self):
        try:
            import sqlite3 as _sq
            c = _sq.connect('salud_unellez.db').cursor()
            c.execute("SELECT COUNT(*) FROM insumos")
            total = c.fetchone()[0]
        except Exception:
            total = 0

        if total == 0:
            messagebox.showinfo("Aviso", "No hay insumos en el inventario para eliminar.")
            return
        if not messagebox.askyesno("⚠️ Confirmar borrado total",
                                   f"Estás a punto de eliminar los {total} insumo(s).\n\n"
                                   "Esta acción NO se puede deshacer.\n\n¿Deseas continuar?"):
            return
        if not messagebox.askyesno("⚠️ Última advertencia",
                                   "¿Estás SEGURO de eliminar TODO el inventario?\n\n"
                                   "Esta operación es IRREVERSIBLE."):
            return
        eliminados = db.eliminar_todos_insumos()
        if eliminados >= 0:
            messagebox.showinfo("Completado", f"Se eliminaron {eliminados} insumo(s).")
            self._cargar()
        else:
            messagebox.showerror("Error", "No se pudo completar el borrado.\nRevise logs/app.log.")

    # ----------------------------------------------------------
    #  PDF
    # ----------------------------------------------------------

    def _generar_pdf(self):
        from tkinter import filedialog
        from datetime import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"Insumos_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            filetypes=[("PDF files", "*.pdf")])
        if not filename:
            return
        try:
            doc    = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            elems  = []
            elems.append(Paragraph("<b>Reporte de Inventario de Insumos</b>", styles["Title"]))
            elems.append(Paragraph(
                f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  SaluDigital UNELLEZ VIPI",
                styles["Normal"]))
            elems.append(Spacer(1, 20))

            todos      = db.obtener_todos_insumos()
            total      = len(todos)
            bajo_stock = sum(1 for _, c, _ in todos if c < 5)
            elems.append(Paragraph(
                f"Total de insumos: <b>{total}</b>  |  En stock bajo: <b>{bajo_stock}</b>",
                styles["Normal"]))
            elems.append(Spacer(1, 15))

            data = [["INSUMO", "CANTIDAD", "ESTADO"]] + [
                [nombre, str(cantidad), estado] for nombre, cantidad, estado in todos]
            t = Table(data, colWidths=[260, 80, 140])
            t.setStyle(TableStyle([
                ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#000066")),
                ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.whitesmoke),
                ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0, 0), (-1,-1),  9),
                ("ALIGN",          (1, 0), (2, -1),  "CENTER"),
                ("GRID",           (0, 0), (-1,-1),  0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F7")]),
                *[("BACKGROUND", (0, i+1), (-1, i+1), colors.HexColor("#FADBD8"))
                  for i, (_, c, _) in enumerate(todos) if c < 5],
            ]))
            elems.append(t)
            doc.build(elems)
            messagebox.showinfo("PDF", "Reporte de insumos generado con éxito.")
        except PermissionError:
            messagebox.showerror("Error", "No se pudo guardar el PDF.\nVerifique que el archivo no esté abierto.")
        except Exception as e:
            logger.error("Error PDF insumos: %s", e)
            messagebox.showerror("Error", "No se pudo crear el PDF.\nRevise logs/app.log.")


# ================================================================
#  VENTANA HISTORIAL DE INSUMO
# ================================================================

class VentanaHistorialInsumo(ctk.CTkToplevel):
    def __init__(self, parent, insumo_id: int, nombre: str):
        super().__init__(parent)
        self.title(f"Historial — {nombre}")
        self.geometry("680x500")
        self.grab_set()
        self._build_ui(insumo_id, nombre)

    def _build_ui(self, insumo_id, nombre):
        # Encabezado
        head = ctk.CTkFrame(self, fg_color="#000066", corner_radius=0)
        head.pack(fill="x")
        ctk.CTkLabel(head, text=f"📋  Historial de movimientos: {nombre}",
                     font=("Helvetica", 15, "bold"), text_color="white").pack(
                         anchor="w", padx=20, pady=12)

        # Cabecera tabla
        cab = ctk.CTkFrame(self, fg_color="#F0F4F8", corner_radius=0)
        cab.pack(fill="x", padx=15, pady=(10, 0))
        for txt, w in [("Fecha", 140), ("Tipo", 90), ("Cantidad", 80),
                       ("Antes", 80), ("Después", 80)]:
            ctk.CTkLabel(cab, text=txt, font=("Helvetica", 11, "bold"),
                         text_color="#2C3E50", width=w, anchor="w").pack(
                             side="left", padx=8, pady=6)

        # Lista movimientos
        scroll = ctk.CTkScrollableFrame(self, fg_color="white", border_width=1)
        scroll.pack(fill="both", expand=True, padx=15, pady=(2, 15))

        historial = db.obtener_historial_insumo(insumo_id)

        if not historial:
            ctk.CTkLabel(scroll, text="Sin movimientos registrados.",
                         text_color="gray").pack(pady=20)
        else:
            for i, (fecha, tipo, cantidad, cant_ant, cant_nueva) in enumerate(historial):
                bg, fg, icono = COLOR_TIPO.get(tipo, ("#F9F9F9", "#333", "•"))
                row = ctk.CTkFrame(scroll,
                                   fg_color="#F9F9F9" if i % 2 == 0 else "white",
                                   corner_radius=0)
                row.pack(fill="x", pady=1)

                ctk.CTkLabel(row, text=fecha, text_color="#555",
                             font=("Helvetica", 10), width=140,
                             anchor="w").pack(side="left", padx=8, pady=5)

                # Badge tipo
                badge = ctk.CTkFrame(row, fg_color=bg, corner_radius=6, width=90)
                badge.pack(side="left", padx=4)
                ctk.CTkLabel(badge, text=f"{icono} {tipo}", text_color=fg,
                             font=("Helvetica", 10, "bold")).pack(padx=6, pady=3)

                ctk.CTkLabel(row, text=str(cantidad), text_color="#333",
                             font=("Helvetica", 11, "bold"), width=80,
                             anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text=str(cant_ant) if cant_ant is not None else "—",
                             text_color="#888", font=("Helvetica", 10),
                             width=80, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text=str(cant_nueva) if cant_nueva is not None else "—",
                             text_color="#27AE60" if tipo == "ENTRADA" else "#C0392B",
                             font=("Helvetica", 10, "bold"),
                             width=80, anchor="w").pack(side="left", padx=8)

        ctk.CTkButton(self, text="Cerrar", fg_color="#7F8C8D",
                      width=120, command=self.destroy).pack(pady=(0, 10))
