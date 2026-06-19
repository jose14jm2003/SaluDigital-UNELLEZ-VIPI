"""
views/widgets.py — Ventanas modales reutilizables.
"""

from tkinter import messagebox
import tkinter as tk
from datetime import datetime, date
import customtkinter as ctk
import logging

import database as db
from views.styles import ENTRY

logger = logging.getLogger(__name__)

TIPOS = ["Estudiante", "Docente", "Personal Obrero"]


def _imc_clasif(peso, altura):
    try:
        h = float(altura) / 100
        v = round(float(peso) / (h ** 2), 1)
        if v < 18.5:   c = "Bajo peso"
        elif v < 25:   c = "Normal"
        elif v < 30:   c = "Sobrepeso"
        elif v < 35:   c = "Obesidad I"
        elif v < 40:   c = "Obesidad II"
        else:          c = "Obesidad III"
        return v, c
    except Exception:
        return None, None


def calcular_edad(fecha_str: str):
    try:
        fn  = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except Exception:
        return None


class VentanaEditarPaciente(ctk.CTkToplevel):
    def __init__(self, parent, paciente_id: int, on_save):
        super().__init__(parent)
        self.title("Editar Paciente")
        self.geometry("540x580")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save

        datos = db.obtener_paciente_por_id(paciente_id)
        if not datos:
            messagebox.showerror("Error", "No se encontró el paciente.", parent=self)
            self.destroy()
            return

        self._id = paciente_id

        ctk.CTkLabel(self, text="Editar Paciente",
                     font=("Helvetica", 18, "bold")).pack(pady=15)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=30, fill="x")

        # Campos de texto simples
        campos = [("Cédula","cedula"), ("Nombre","nombre"),
                  ("Apellido","apellido"), ("Teléfono","telefono")]
        self._entries = {}
        for label, key in campos:
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=120, anchor="w",
                         font=("Helvetica", 11, "bold")).pack(side="left")
            ent = ctk.CTkEntry(f, height=34, **ENTRY)
            ent.insert(0, datos.get(key, "") or "")
            ent.pack(side="left", fill="x", expand=True)
            self._entries[key] = ent

        # Fecha nacimiento + edad
        f_dates = ctk.CTkFrame(form, fg_color="transparent")
        f_dates.pack(fill="x", pady=3)
        ctk.CTkLabel(f_dates, text="F. Nacimiento", width=120, anchor="w",
                     font=("Helvetica", 11, "bold")).pack(side="left")
        self._ent_fnac = ctk.CTkEntry(f_dates, height=34, width=150,
                                       placeholder_text="DD/MM/AAAA", **ENTRY)
        self._ent_fnac.insert(0, datos.get("fecha_nacimiento", "") or "")
        self._ent_fnac.pack(side="left", padx=(0, 10))
        self._ent_fnac.bind("<FocusOut>", self._auto_edad)

        ctk.CTkLabel(f_dates, text="Edad", anchor="w",
                     font=("Helvetica", 11, "bold")).pack(side="left")
        self._ent_edad = ctk.CTkEntry(f_dates, height=34, width=70, **ENTRY)
        edad_val = datos.get("edad")
        self._ent_edad.insert(0, str(edad_val) if edad_val else "")
        self._ent_edad.pack(side="left", padx=(4, 0))

        # Tipo persona
        f_tipo = ctk.CTkFrame(form, fg_color="transparent")
        f_tipo.pack(fill="x", pady=3)
        ctk.CTkLabel(f_tipo, text="Tipo", width=120, anchor="w",
                     font=("Helvetica", 11, "bold")).pack(side="left")
        self._tipo_var = ctk.StringVar(value=datos.get("tipo_persona") or TIPOS[0])
        ctk.CTkSegmentedButton(
            f_tipo, values=TIPOS, variable=self._tipo_var,
            fg_color="#E8EDF2", selected_color="#E67E22",
            selected_hover_color="#CA6F1E", text_color="black",
            font=("Helvetica", 10, "bold"), height=32,
        ).pack(side="left", fill="x", expand=True)

        # Motivo, Diagnóstico, Tratamiento
        for label, key in [("Motivo","motivo"),("Diagnóstico","diagnostico"),("Tratamiento","tratamiento")]:
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=120, anchor="w",
                         font=("Helvetica", 11, "bold")).pack(side="left")
            ent = ctk.CTkEntry(f, height=34, **ENTRY)
            ent.insert(0, datos.get(key, "") or "")
            ent.pack(side="left", fill="x", expand=True)
            self._entries[key] = ent

        # Altura, Peso, IMC — solo módulos aplicables
        # Necesitamos el área del paciente para decidir
        self._ent_altura = self._ent_peso = self._lbl_imc_edit = None
        try:
            import sqlite3 as _sq
            row = _sq.connect('salud_unellez.db').execute(
                "SELECT area_atencion, altura_cm, peso_kg FROM pacientes WHERE id=?",
                (paciente_id,)).fetchone()
            area_pac = row[0] if row else ""
            alt_val  = row[1] if row else None
            pes_val  = row[2] if row else None
        except Exception:
            area_pac = ""; alt_val = pes_val = None

        if True:
            f_antro = ctk.CTkFrame(form, fg_color="transparent")
            f_antro.pack(fill="x", pady=3)
            ctk.CTkLabel(f_antro, text="Altura (cm)", width=120, anchor="w",
                         font=("Helvetica", 11, "bold")).pack(side="left")
            self._ent_altura = ctk.CTkEntry(f_antro, height=34, width=80, **ENTRY)
            self._ent_altura.insert(0, str(alt_val) if alt_val else "")
            self._ent_altura.pack(side="left", padx=(0,10))
            self._ent_altura.bind("<FocusOut>", self._auto_imc_edit)

            ctk.CTkLabel(f_antro, text="Peso (kg)", anchor="w",
                         font=("Helvetica", 11, "bold")).pack(side="left")
            self._ent_peso = ctk.CTkEntry(f_antro, height=34, width=80, **ENTRY)
            self._ent_peso.insert(0, str(pes_val) if pes_val else "")
            self._ent_peso.pack(side="left", padx=(4,10))
            self._ent_peso.bind("<FocusOut>", self._auto_imc_edit)

            self._lbl_imc_edit = ctk.CTkLabel(f_antro, text="IMC: —",
                                               font=("Helvetica", 11, "bold"),
                                               text_color="#E67E22")
            self._lbl_imc_edit.pack(side="left")
            if alt_val and pes_val:
                v, c = _imc_clasif(pes_val, alt_val)
                if v:
                    self._lbl_imc_edit.configure(text=f"IMC: {v} ({c})")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=15)
        ctk.CTkButton(btns, text="💾 Guardar", fg_color="#2ecc71",
                      width=140, command=self._guardar).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#7F8C8D",
                      width=140, command=self.destroy).pack(side="left", padx=10)

    def _auto_imc_edit(self, event=None):
        if not self._ent_altura or not self._ent_peso:
            return
        try:
            v, c = _imc_clasif(self._ent_peso.get(), self._ent_altura.get())
            if v and self._lbl_imc_edit:
                self._lbl_imc_edit.configure(text=f"IMC: {v} ({c})")
        except Exception:
            pass

    def _auto_edad(self, event=None):
        edad = calcular_edad(self._ent_fnac.get())
        if edad is not None:
            self._ent_edad.delete(0, tk.END)
            self._ent_edad.insert(0, str(edad))

    def _guardar(self):
        v = {k: e.get().strip() for k, e in self._entries.items()}
        if not v["cedula"] or not v["motivo"]:
            messagebox.showwarning("Aviso", "Cédula y Motivo son obligatorios.", parent=self)
            return
        edad_str = self._ent_edad.get().strip()
        edad = int(edad_str) if edad_str.isdigit() else None
        alt = pes = imc_v = None
        if self._ent_altura and self._ent_peso:
            try:
                alt   = float(self._ent_altura.get().replace(",",".")) or None
                pes   = float(self._ent_peso.get().replace(",","."))   or None
                if alt and pes:
                    imc_v, _ = _imc_clasif(pes, alt)
            except Exception:
                pass

        ok = db.actualizar_paciente(
            self._id, v["cedula"], v["nombre"], v["apellido"], v["telefono"],
            self._tipo_var.get(), self._ent_fnac.get().strip(), edad,
            v["motivo"], v.get("diagnostico",""), v.get("tratamiento",""),
            alt, pes, imc_v)
        if ok:
            self._on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar.\nRevise logs/app.log.", parent=self)


class VentanaEditarInsumo(ctk.CTkToplevel):
    def __init__(self, parent, insumo_id: int, nombre: str, cantidad: int, on_save):
        super().__init__(parent)
        self.title("Editar Cantidad")
        self.geometry("340x220")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self._id      = insumo_id

        ctk.CTkLabel(self, text=f"Insumo: {nombre}",
                     font=("Helvetica", 15, "bold")).pack(pady=20)
        ctk.CTkLabel(self, text="Nueva cantidad:", font=("Helvetica", 12)).pack()

        self._ent = ctk.CTkEntry(self, width=120, height=38, justify="center", **ENTRY)
        self._ent.insert(0, str(cantidad))
        self._ent.pack(pady=10)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="💾 Guardar", fg_color="#2ecc71",
                      width=120, command=self._guardar).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#7F8C8D",
                      width=120, command=self.destroy).pack(side="left", padx=8)

    def _guardar(self):
        val = self._ent.get().strip()
        if not val.isdigit() or int(val) < 0:
            messagebox.showwarning("Aviso", "Ingrese un número válido ≥ 0.", parent=self)
            return
        ok = db.actualizar_cantidad_insumo(self._id, int(val))
        if ok:
            self._on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar.\nRevise logs/app.log.", parent=self)
