"""
views/vista_area.py — Módulo de área médica.
Incluye: fecha nacimiento, edad, diagnóstico, tratamiento, historial por paciente.
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date
import customtkinter as ctk
import logging

import database as db
from views.widgets import VentanaEditarPaciente
from views.styles import ENTRY, ENTRY_SEARCH

logger = logging.getLogger(__name__)

TIPOS_PERSONA = ["Estudiante", "Docente", "Personal Obrero"]

COLOR_TIPO = {
    "Estudiante":       ("#EAF4FB", "#2980B9"),
    "Docente":          ("#EAFAF1", "#27AE60"),
    "Personal Obrero":  ("#FEF9E7", "#D4AC0D"),
}




def calcular_edad(fecha_str: str) -> int | None:
    """Calcula edad a partir de DD/MM/AAAA."""
    try:
        fn = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except Exception:
        return None


def calcular_imc(peso_kg: float, altura_cm: float):
    """Devuelve (imc, clasificacion) o (None, None) si datos inválidos."""
    try:
        if peso_kg <= 0 or altura_cm <= 0:
            return None, None
        h_m = altura_cm / 100
        imc = round(peso_kg / (h_m ** 2), 1)
        if imc < 18.5:
            clasificacion = "⚠️ Bajo peso"
        elif imc < 25:
            clasificacion = "✅ Normal"
        elif imc < 30:
            clasificacion = "⚠️ Sobrepeso"
        elif imc < 35:
            clasificacion = "🔴 Obesidad I"
        elif imc < 40:
            clasificacion = "🔴 Obesidad II"
        else:
            clasificacion = "🔴 Obesidad III"
        return imc, clasificacion
    except Exception:
        return None, None


class VistaArea(ctk.CTkFrame):
    def __init__(self, parent, area: str, generar_pdf_fn, usuario_actual: dict = None):
        super().__init__(parent, fg_color="transparent")
        self._area           = area
        self._generar_pdf    = generar_pdf_fn
        self._usuario_actual = usuario_actual or {}
        self._build_ui()

    # ----------------------------------------------------------

    def _build_ui(self):
        # ── Encabezado ────────────────────────────────────────
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=25, pady=(20, 5))
        ctk.CTkLabel(head, text=f"Módulo: {self._area}",
                     font=("Helvetica", 22, "bold"), text_color="black").pack(side="left")
        ctk.CTkButton(head, text="📄 PDF ÁREA", fg_color="#34495E", width=130,
                      command=lambda: self._generar_pdf(self._area)).pack(side="right", padx=(4, 0))
        ctk.CTkButton(head, text="🗑️ BORRAR TODO", fg_color="#C0392B", width=140,
                      font=("Helvetica", 11, "bold"),
                      command=self._borrar_todos).pack(side="right", padx=(0, 4))

        # ── Formulario ────────────────────────────────────────
        form = ctk.CTkFrame(self, fg_color="#F8F9F9", corner_radius=12, border_width=1)
        form.pack(fill="x", padx=25, pady=8)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self._campos = {}

        # Fila 0: Cédula, Nombre
        for label, row, col in [("Cédula", 0, 0), ("Nombre", 0, 1),
                                  ("Apellido", 1, 0), ("Teléfono", 1, 1)]:
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.grid(row=row, column=col, padx=20, pady=8, sticky="ew")
            ctk.CTkLabel(f, text=label, text_color="black",
                         font=("Helvetica", 13, "bold")).pack(anchor="w")
            self._campos[label] = ctk.CTkEntry(f, height=40, **ENTRY)
            self._campos[label].pack(fill="x")

        # Fila 2: Fecha Nacimiento + Edad (auto)
        f_dates = ctk.CTkFrame(form, fg_color="transparent")
        f_dates.grid(row=2, column=0, columnspan=2, padx=20, pady=8, sticky="ew")
        f_dates.columnconfigure(0, weight=2)
        f_dates.columnconfigure(1, weight=1)

        f_fn = ctk.CTkFrame(f_dates, fg_color="transparent")
        f_fn.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(f_fn, text="Fecha de Nacimiento (DD/MM/AAAA)", text_color="black",
                     font=("Helvetica", 13, "bold")).pack(anchor="w")
        self._ent_fnac = ctk.CTkEntry(f_fn, height=40,
                                       placeholder_text="DD/MM/AAAA", **ENTRY)
        self._ent_fnac.pack(fill="x")
        self._ent_fnac.bind("<FocusOut>", self._auto_edad)

        f_edad = ctk.CTkFrame(f_dates, fg_color="transparent")
        f_edad.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(f_edad, text="Edad", text_color="black",
                     font=("Helvetica", 13, "bold")).pack(anchor="w")
        self._ent_edad = ctk.CTkEntry(f_edad, height=40,
                                       placeholder_text="Auto", **ENTRY)
        self._ent_edad.pack(fill="x")

        # Fila 2b: Altura, Peso, IMC (solo módulos con antropometría)
        self._ent_altura = None
        self._ent_peso   = None
        self._lbl_imc    = None

        if True:
            f_antro = ctk.CTkFrame(form, fg_color="transparent")
            f_antro.grid(row=2, column=1, padx=20, pady=8, sticky="ew")
            f_antro.columnconfigure(0, weight=1)
            f_antro.columnconfigure(1, weight=1)
            f_antro.columnconfigure(2, weight=1)

            for label, attr, col, ph in [
                ("Altura (cm)", "_ent_altura", 0, "Ej: 165"),
                ("Peso (kg)",   "_ent_peso",   1, "Ej: 70.5"),
            ]:
                fx = ctk.CTkFrame(f_antro, fg_color="transparent")
                fx.grid(row=0, column=col, sticky="ew", padx=(0, 8))
                ctk.CTkLabel(fx, text=label, text_color="black",
                             font=("Helvetica", 11, "bold")).pack(anchor="w")
                ent = ctk.CTkEntry(fx, height=40, placeholder_text=ph, **ENTRY)
                ent.pack(fill="x")
                ent.bind("<FocusOut>", self._auto_imc)
                setattr(self, attr, ent)

            fx_imc = ctk.CTkFrame(f_antro, fg_color="transparent")
            fx_imc.grid(row=0, column=2, sticky="ew")
            ctk.CTkLabel(fx_imc, text="IMC", text_color="black",
                         font=("Helvetica", 11, "bold")).pack(anchor="w")
            self._lbl_imc = ctk.CTkLabel(fx_imc, text="—",
                                          font=("Helvetica", 12, "bold"),
                                          text_color="#E67E22",
                                          fg_color="#F0F4F8",
                                          corner_radius=8,
                                          height=40)
            self._lbl_imc.pack(fill="x")

        # Fila 3: Tipo persona + Motivo
        f_row3 = ctk.CTkFrame(form, fg_color="transparent")
        f_row3.grid(row=3, column=0, columnspan=2, padx=20, pady=8, sticky="ew")
        f_row3.columnconfigure(1, weight=1)

        f_tipo = ctk.CTkFrame(f_row3, fg_color="transparent")
        f_tipo.grid(row=0, column=0, sticky="w", padx=(0, 20))
        ctk.CTkLabel(f_tipo, text="Tipo de Persona", text_color="black",
                     font=("Helvetica", 13, "bold")).pack(anchor="w")
        self._tipo_var = ctk.StringVar(value=TIPOS_PERSONA[0])
        ctk.CTkSegmentedButton(
            f_tipo, values=TIPOS_PERSONA, variable=self._tipo_var,
            fg_color="#E8EDF2", selected_color="#E67E22",
            selected_hover_color="#CA6F1E", unselected_color="#E8EDF2",
            unselected_hover_color="#D0D8E4", text_color="black",
            font=("Helvetica", 13, "bold"), height=40,
        ).pack(anchor="w")

        f_mot = ctk.CTkFrame(f_row3, fg_color="transparent")
        f_mot.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(f_mot, text="Motivo de consulta", text_color="black",
                     font=("Helvetica", 13, "bold")).pack(anchor="w")
        self._ent_mot = ctk.CTkEntry(f_mot, placeholder_text="Describa el motivo...",
                                      height=40, **ENTRY)
        self._ent_mot.pack(fill="x")

        # Fila 4: Diagnóstico + Tratamiento
        f_row4 = ctk.CTkFrame(form, fg_color="transparent")
        f_row4.grid(row=4, column=0, columnspan=2, padx=20, pady=8, sticky="ew")
        f_row4.columnconfigure(0, weight=1)
        f_row4.columnconfigure(1, weight=1)

        for label, attr, col in [("Diagnóstico", "_ent_diag", 0),
                                   ("Tratamiento", "_ent_trat", 1)]:
            fx = ctk.CTkFrame(f_row4, fg_color="transparent")
            fx.grid(row=0, column=col, sticky="ew", padx=(0 if col else 0, 10 if col == 0 else 0))
            ctk.CTkLabel(fx, text=label, text_color="black",
                         font=("Helvetica", 13, "bold")).pack(anchor="w")
            ent = ctk.CTkEntry(fx, placeholder_text=f"Ingrese {label.lower()}...",
                               height=40, **ENTRY)
            ent.pack(fill="x")
            setattr(self, attr, ent)

        # ── Botón registrar ───────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(2, 5))
        ctk.CTkButton(btn_row, text="💾 REGISTRAR PACIENTE",
                      fg_color="#2ecc71", height=36, width=220,
                      font=("Helvetica", 11, "bold"),
                      command=self._guardar).pack(side="right")

        # ── Búsqueda ──────────────────────────────────────────
        self._bus = ctk.CTkEntry(self,
                                  placeholder_text="🔍 Buscar por nombre, cédula, motivo, diagnóstico...",
                                  height=40, **ENTRY_SEARCH)
        self._bus.pack(fill="x", padx=25, pady=4)
        self._bus.bind("<KeyRelease>", lambda e: self._cargar())

        # ── Lista ─────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="white", border_width=1)
        self._scroll.pack(fill="both", expand=True, padx=25, pady=8)
        self._cargar()

    # ----------------------------------------------------------

    def _auto_edad(self, event=None):
        """Calcula la edad automáticamente al salir del campo fecha."""
        edad = calcular_edad(self._ent_fnac.get())
        if edad is not None:
            self._ent_edad.delete(0, tk.END)
            self._ent_edad.insert(0, str(edad))

    def _auto_imc(self, event=None):
        """Calcula IMC automáticamente al salir de altura o peso."""
        if not self._ent_altura or not self._ent_peso:
            return
        try:
            peso   = float(self._ent_peso.get().replace(",", "."))
            altura = float(self._ent_altura.get().replace(",", "."))
            imc, clasif = calcular_imc(peso, altura)
            if imc and self._lbl_imc:
                self._lbl_imc.configure(text=f"{imc}  {clasif}")
        except Exception:
            pass

    def _guardar(self):
        d    = {k: v.get().strip() for k, v in self._campos.items()}
        tipo = self._tipo_var.get()
        fnac = self._ent_fnac.get().strip()
        edad_str = self._ent_edad.get().strip()
        edad = int(edad_str) if edad_str.isdigit() else None
        m    = self._ent_mot.get().strip()
        diag = self._ent_diag.get().strip()
        trat = self._ent_trat.get().strip()

        if not d["Cédula"] or not m:
            messagebox.showwarning("Aviso", "Cédula y Motivo son campos obligatorios.")
            return

        # Antropometría (solo módulos aplicables)
        altura_cm = peso_kg = imc_val = None
        if self._ent_altura and self._ent_peso:
            try:
                altura_cm = float(self._ent_altura.get().replace(",", ".")) or None
                peso_kg   = float(self._ent_peso.get().replace(",", "."))   or None
                if altura_cm and peso_kg:
                    imc_val, _ = calcular_imc(peso_kg, altura_cm)
            except Exception:
                pass

        ok = db.registrar_paciente(
            d["Cédula"], d["Nombre"], d["Apellido"], d["Teléfono"],
            tipo, fnac, edad, m, diag, trat, altura_cm, peso_kg, imc_val, self._area)
        if ok:
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "REGISTRO_PACIENTE",
                f"Paciente CI:{d['Cédula']} en {self._area}",
                self._area)
            self._ent_mot.delete(0, tk.END)
            self._ent_diag.delete(0, tk.END)
            self._ent_trat.delete(0, tk.END)
            self._ent_fnac.delete(0, tk.END)
            self._ent_edad.delete(0, tk.END)
            self._tipo_var.set(TIPOS_PERSONA[0])
            for v in self._campos.values():
                v.delete(0, tk.END)
            if self._ent_altura:
                self._ent_altura.delete(0, tk.END)
            if self._ent_peso:
                self._ent_peso.delete(0, tk.END)
            if self._lbl_imc:
                self._lbl_imc.configure(text="—")
            self._cargar()
        else:
            messagebox.showerror("Error", "No se pudo registrar el paciente.\nRevise logs/app.log.")

    def _cargar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        pacientes = db.obtener_pacientes(self._area, self._bus.get().strip())

        if not pacientes:
            ctk.CTkLabel(self._scroll, text="Sin registros.", text_color="gray").pack(pady=10)
            return

        for pid, fec, nom, ape, ced, tipo, edad, mot, diag, trat, altura, peso, imc in pacientes:
            card = ctk.CTkFrame(self._scroll, fg_color="#F9F9F9",
                                corner_radius=8, border_width=1, border_color="#E0E0E0")
            card.pack(fill="x", pady=4, padx=2)

            # Línea superior
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(6, 2))
            ctk.CTkLabel(top, text=fec, text_color="gray",
                         font=("Helvetica", 11)).pack(side="left")
            ctk.CTkLabel(top, text=f"  {nom} {ape}".upper(), text_color="black",
                         font=("Helvetica", 12, "bold")).pack(side="left")
            ctk.CTkLabel(top, text=f"CI: {ced}", text_color="#555",
                         font=("Helvetica", 11)).pack(side="left", padx=8)
            if edad:
                ctk.CTkLabel(top, text=f"🎂 {edad} años", text_color="#666",
                             font=("Helvetica", 11)).pack(side="left", padx=4)

            # Badge tipo
            tipo_label = tipo or "—"
            bg, fg = COLOR_TIPO.get(tipo_label, ("#F0F0F0", "#555555"))
            badge = ctk.CTkFrame(top, fg_color=bg, corner_radius=8)
            badge.pack(side="left", padx=4)
            ctk.CTkLabel(badge, text=tipo_label, text_color=fg,
                         font=("Helvetica", 11, "bold")).pack(padx=8, pady=2)

            # IMC badge (solo módulos con antropometría)
            if imc:
                _, clasif = calcular_imc(peso or 0, altura or 0)
                imc_bg = "#EAFAF1" if "Normal" in (clasif or "") else "#FDEDEC"
                imc_fg = "#196F3D" if "Normal" in (clasif or "") else "#C0392B"
                imc_badge = ctk.CTkFrame(top, fg_color=imc_bg, corner_radius=8)
                imc_badge.pack(side="left", padx=4)
                ctk.CTkLabel(imc_badge, text=f"IMC {imc} {clasif}",
                             text_color=imc_fg,
                             font=("Helvetica", 10, "bold")).pack(padx=6, pady=2)

            # Botón historial
            ctk.CTkButton(top, text="📋 Historial", fg_color="#8E44AD",
                          width=95, height=24,
                          command=lambda c=ced, n=f"{nom} {ape}":
                              self._ver_historial(c, n)).pack(side="right", padx=4)

            # Motivo
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=12, pady=(2, 4))

            if altura and peso:
                ctk.CTkLabel(body, text=f"📏 Altura: {altura} cm  |  ⚖️ Peso: {peso} kg",
                             text_color="#555", font=("Helvetica", 11), anchor="w").pack(fill="x")

            ctk.CTkLabel(body, text=f"📋 Motivo: {mot}", text_color="#333",
                         font=("Helvetica", 11, "italic"), anchor="w").pack(fill="x")
            if diag:
                ctk.CTkLabel(body, text=f"🔬 Diagnóstico: {diag}", text_color="#1A5276",
                             font=("Helvetica", 11), anchor="w").pack(fill="x")
            if trat:
                ctk.CTkLabel(body, text=f"💊 Tratamiento: {trat}", text_color="#196F3D",
                             font=("Helvetica", 11), anchor="w").pack(fill="x")

            # Botones acción
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(anchor="e", padx=10, pady=(0, 6))
            ctk.CTkButton(btns, text="✏️ Editar", fg_color="#2980B9",
                          width=90, height=26,
                          command=lambda i=pid: self._editar(i)).pack(side="left", padx=4)
            ctk.CTkButton(btns, text="🗑️ Eliminar", fg_color="#E74C3C",
                          width=95, height=26,
                          command=lambda i=pid, n=f"{nom} {ape}":
                              self._eliminar(i, n)).pack(side="left", padx=4)

    def _ver_historial(self, cedula, nombre):
        VentanaHistorial(self, cedula, nombre)

    def _editar(self, pid):
        VentanaEditarPaciente(self, pid, on_save=self._cargar)

    def _eliminar(self, pid, nombre):
        if messagebox.askyesno("Confirmar",
                               f"¿Eliminar el registro de {nombre}?\n"
                               "Esta acción no se puede deshacer."):
            ok = db.eliminar_paciente(pid)
            if ok:
                db.registrar_auditoria(
                    self._usuario_actual.get("username","?"),
                    "ELIMINAR_PACIENTE",
                    f"Paciente id:{pid} eliminado de {self._area}",
                    self._area)
                self._cargar()
            else:
                messagebox.showerror("Error", "No se pudo eliminar.\nRevise logs/app.log.")

    def _borrar_todos(self):
        try:
            import sqlite3 as _sq
            c = _sq.connect('salud_unellez.db').cursor()
            c.execute("SELECT COUNT(*) FROM pacientes WHERE area_atencion = ?", (self._area,))
            total = c.fetchone()[0]
        except Exception:
            total = 0

        if total == 0:
            messagebox.showinfo("Aviso", f"No hay registros en {self._area} para eliminar.")
            return

        if not messagebox.askyesno("⚠️ Confirmar borrado total",
                                   f"Estás a punto de eliminar los {total} registro(s) del módulo:\n\n"
                                   f"  📋 {self._area}\n\n"
                                   "Esta acción NO se puede deshacer.\n\n¿Deseas continuar?"):
            return

        if not messagebox.askyesno("⚠️ Última advertencia",
                                   f"¿Estás SEGURO de eliminar TODOS los registros de {self._area}?\n\n"
                                   "Esta operación es IRREVERSIBLE."):
            return

        eliminados = db.eliminar_todos_pacientes_area(self._area)
        if eliminados >= 0:
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "BORRAR_TODO_AREA",
                f"Eliminados {eliminados} registros de {self._area}",
                self._area)
            messagebox.showinfo("Completado", f"Se eliminaron {eliminados} registro(s) de {self._area}.")
            self._cargar()
        else:
            messagebox.showerror("Error", "No se pudo completar el borrado.\nRevise logs/app.log.")


# ================================================================
#  VENTANA HISTORIAL
# ================================================================

class VentanaHistorial(ctk.CTkToplevel):
    def __init__(self, parent, cedula: str, nombre: str):
        super().__init__(parent)
        self.title(f"Historial — {nombre.upper()}")
        self.geometry("820x560")
        self.grab_set()
        self._build_ui(cedula, nombre)

    def _build_ui(self, cedula, nombre):
        # Encabezado
        head = ctk.CTkFrame(self, fg_color="#000066", corner_radius=0)
        head.pack(fill="x")

        datos = db.obtener_datos_paciente(cedula)
        info  = f"CI: {cedula}"
        if datos:
            if datos.get("fecha_nacimiento"):
                info += f"  |  Nacimiento: {datos['fecha_nacimiento']}"
            if datos.get("edad"):
                info += f"  |  Edad: {datos['edad']} años"
            if datos.get("tipo_persona"):
                info += f"  |  {datos['tipo_persona']}"
            if datos.get("telefono"):
                info += f"  |  Tel: {datos['telefono']}"

        ctk.CTkLabel(head, text=f"📋  {nombre.upper()}",
                     font=("Helvetica", 16, "bold"), text_color="white").pack(
                         anchor="w", padx=20, pady=(12, 2))
        ctk.CTkLabel(head, text=info, font=("Helvetica", 11),
                     text_color="#BDC3C7").pack(anchor="w", padx=20, pady=(0, 12))

        # Historial
        scroll = ctk.CTkScrollableFrame(self, fg_color="white")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        historial = db.obtener_historial_paciente(cedula)

        if not historial:
            ctk.CTkLabel(scroll, text="Sin registros en el historial.",
                         text_color="gray").pack(pady=20)
            return

        for i, (pid, fec, area, tipo, edad, mot, diag, trat, altura, peso, imc) in enumerate(historial):
            card = ctk.CTkFrame(scroll, fg_color="#F4F6F8",
                                corner_radius=10, border_width=1, border_color="#D5D8DC")
            card.pack(fill="x", pady=6, padx=4)

            # Cabecera visita
            cab = ctk.CTkFrame(card, fg_color="#000066", corner_radius=8)
            cab.pack(fill="x", padx=8, pady=(8, 4))
            ctk.CTkLabel(cab, text=f"Visita #{i+1}  —  {fec}",
                         font=("Helvetica", 11, "bold"), text_color="white").pack(
                             side="left", padx=12, pady=5)
            ctk.CTkLabel(cab, text=area, font=("Helvetica", 11, "bold"),
                         text_color="#E67E22").pack(side="right", padx=12)

            # Detalle
            det = ctk.CTkFrame(card, fg_color="transparent")
            det.pack(fill="x", padx=14, pady=(4, 10))

            def fila(parent, icono, label, valor, color="#333"):
                if not valor:
                    return
                f = ctk.CTkFrame(parent, fg_color="transparent")
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"{icono} {label}:", text_color="#666",
                             font=("Helvetica", 11, "bold"), width=110,
                             anchor="w").pack(side="left")
                ctk.CTkLabel(f, text=str(valor), text_color=color,
                             font=("Helvetica", 11), anchor="w",
                             wraplength=550).pack(side="left", fill="x", expand=True)

            if altura and peso:
                _, clasif = calcular_imc(float(peso), float(altura))
                fila(det, "📏", "Altura",  f"{altura} cm", "#555")
                fila(det, "⚖️", "Peso",    f"{peso} kg",  "#555")
                fila(det, "📊", "IMC",     f"{imc}  {clasif}", "#8E44AD")
            fila(det, "📋", "Motivo",      mot,  "#333")
            fila(det, "🔬", "Diagnóstico", diag, "#1A5276")
            fila(det, "💊", "Tratamiento", trat, "#196F3D")

        ctk.CTkButton(self, text="Cerrar", fg_color="#7F8C8D", width=120,
                      command=self.destroy).pack(pady=(0, 15))
