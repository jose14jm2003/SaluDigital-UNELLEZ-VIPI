"""
views/dashboard.py — Shell principal de la aplicación.
Gestiona la navegación, el contenedor de vistas y la generación de PDF.
"""

from tkinter import messagebox, filedialog
import customtkinter as ctk
import logging

from logger_config import setup_logging
import database as db
import backup as bk
from security import validar_password
from security import hash_password
from views.login import LoginView
from views.vista_area import VistaArea
from views.vista_insumos import VistaInsumos
from views.vista_usuarios import VistaUsuarios
from views.vista_auditoria import VistaAuditoria

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

setup_logging()
logger = logging.getLogger(__name__)


class AppSalud(ctk.CTk):
    AZUL            = "#000066"
    AZUL_DARK       = "#000044"
    NARANJA         = "#E67E22"
    TIMEOUT_MIN     = 15          # minutos de inactividad antes de cerrar sesión
    _timeout_job_id = None        # referencia al after() del temporizador

    def __init__(self):
        super().__init__()
        self.title("SaluDigital UNELLEZ VIPI - Gestión de Salud")
        self.configure(fg_color=self.AZUL)
        self.after(0, lambda: self.wm_state('zoomed'))

        self._usuario_actual = None

        # Pie de página (siempre visible)
        footer = ctk.CTkFrame(self, height=36, fg_color=self.AZUL, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        ctk.CTkLabel(footer,
                     text="Desarrollado por: Kaira Henao y José Marcano - 2026",
                     text_color="white", font=("Helvetica", 12, "bold")).pack(expand=True)

        self._container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._container.pack(side="top", fill="both", expand=True)

        # Inicializar BD
        try:
            db.inicializar(hash_password("Admin1234!"))
        except Exception as e:
            logger.critical("Error crítico al inicializar BD: %s", e)
            messagebox.showerror("Error crítico",
                                 f"No se pudo inicializar la base de datos.\n{e}")
            self.destroy()
            return

        self._mostrar_login()

    # ----------------------------------------------------------
    #  NAVEGACIÓN DE ALTO NIVEL
    # ----------------------------------------------------------

    def _limpiar(self):
        for w in self._container.winfo_children():
            w.destroy()

    def _mostrar_login(self):
        self._limpiar()
        LoginView(self._container, on_login_success=self._on_login).pack(
            fill="both", expand=True)

    def _on_login(self, usuario: dict):
        self._usuario_actual = usuario
        dest = bk.hacer_backup()
        if dest:
            logger.info("Backup automático: %s", dest)
        db.registrar_auditoria(usuario["username"], "LOGIN", "Inicio de sesión exitoso")
        self._construir_dashboard()
        self._reset_timeout()

    def _reset_timeout(self, event=None):
        """Reinicia el temporizador de inactividad."""
        if self._timeout_job_id:
            self.after_cancel(self._timeout_job_id)
        ms = self.TIMEOUT_MIN * 60 * 1000
        self._timeout_job_id = self.after(ms, self._cerrar_por_inactividad)

    def _cerrar_por_inactividad(self):
        """Cierra sesión automáticamente por inactividad."""
        if self._usuario_actual:
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "LOGOUT_AUTO",
                f"Sesión cerrada por inactividad ({self.TIMEOUT_MIN} min)"
            )
            logger.info("Sesión cerrada por inactividad")
            from tkinter import messagebox as _mb
            _mb.showwarning("Sesión expirada",
                            f"La sesión se cerró por {self.TIMEOUT_MIN} minutos de inactividad.")
            self._cerrar_sesion()

    def _construir_dashboard(self):
        self._limpiar()

        # Barra lateral
        nav = ctk.CTkFrame(self._container, width=260, fg_color=self.AZUL_DARK)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        # Logo símbolo UNELLEZ sin fondo
        try:
            from PIL import Image as _Img
            _logo = _Img.open("assets/logo_simbolo.png").convert("RGBA")
            _logo = _logo.resize((64, 70), _Img.LANCZOS)
            self._nav_logo = ctk.CTkImage(_logo, size=(64, 70))
            ctk.CTkLabel(nav, image=self._nav_logo, text="",
                         fg_color="transparent").pack(pady=(25, 0))
        except Exception as _e:
            import logging; logging.getLogger(__name__).warning("Logo nav: %s", _e)

        ctk.CTkLabel(nav, text="SaluDigital",
                     font=("Helvetica", 20, "bold"), text_color="white").pack(pady=(4, 2))
        ctk.CTkLabel(nav, text=f"👤 {self._usuario_actual['username']}",
                     font=("Helvetica", 11), text_color="#BDC3C7").pack(pady=(0, 16))

        opciones = [
            ("🏠 Inicio",          self._vista_inicio),
            ("🩺 Servicio Médico", lambda: self._vista_area("Servicio Médico")),
            ("🧪 Laboratorio",     lambda: self._vista_area("Laboratorio")),
            ("🦷 Odontología",     lambda: self._vista_area("Odontología")),
            ("⚡ Fisioterapia",    lambda: self._vista_area("Fisioterapia")),
            ("📦 Insumos",         self._vista_insumos),
        ]
        # Gestión de usuarios solo para admin
        if self._usuario_actual.get("rol") == "admin":
            opciones.append(("🔑 Contraseña", self._vista_usuarios))
        self._nav_btns = {}
        for txt, cmd in opciones:
            btn = ctk.CTkButton(nav, text=txt,
                                command=lambda t=txt, c=cmd: self._cambiar(t, c),
                                fg_color="transparent", anchor="w",
                                font=("Helvetica", 14, "bold"))
            btn.pack(pady=4, padx=15, fill="x")
            self._nav_btns[txt] = btn

        # Con side="bottom" el primero en declararse queda más abajo
        # Orden visual de abajo a arriba: Cerrar Sesión → Backup → Restaurar

        # 1. Cerrar Sesión (más abajo de todos)
        ctk.CTkButton(nav, text="🚪 Cerrar Sesión", fg_color=self.NARANJA,
                      command=self._cerrar_sesion).pack(
                          side="bottom", pady=(0, 10), padx=15, fill="x")

        # 2. Backup y Restaurar encima (solo admin)
        if self._usuario_actual.get("rol") == "admin":
            ctk.CTkButton(nav, text="♻️ Restaurar BD",
                          fg_color="#6C3483", font=("Helvetica", 11),
                          command=self._restaurar_backup).pack(
                              side="bottom", pady=(0, 4), padx=15, fill="x")
            ctk.CTkButton(nav, text="💾 Backup BD",
                          fg_color="#1A5276", font=("Helvetica", 11),
                          command=self._hacer_backup_manual).pack(
                              side="bottom", pady=(0, 4), padx=15, fill="x")

        # Área de contenido
        main = ctk.CTkFrame(self._container, fg_color=self.AZUL)
        main.pack(side="right", fill="both", expand=True)
        self._content_card = ctk.CTkFrame(main, corner_radius=20, fg_color="white")
        self._content_card.pack(fill="both", expand=True, padx=15, pady=15)

        self._cambiar("🏠 Inicio", self._vista_inicio)

    def _hacer_backup_manual(self):
        """Backup manual con confirmación."""
        from tkinter import messagebox as _mb
        dest = bk.hacer_backup()
        if dest:
            backups = bk.listar_backups()
            _mb.showinfo("Backup Exitoso", "Backup creado.\n\nArchivo: " + str(dest))
        else:
            _mb.showerror("Error", "No se pudo crear el backup.\nRevise logs/app.log.")

    def _restaurar_backup(self):
        from tkinter import messagebox as _mb, filedialog as _fd
        import os
        ruta = _fd.askopenfilename(
            title="Seleccionar backup a restaurar",
            initialdir=os.path.join(os.getcwd(), "backups") if os.path.exists("backups") else os.getcwd(),
            filetypes=[("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        # Pedir contraseña de respaldo
        pwd_dlg = ctk.CTkToplevel(self)
        pwd_dlg.title("Contraseña de Restauración")
        pwd_dlg.geometry("360x180")
        pwd_dlg.resizable(False, False)
        pwd_dlg.grab_set()
        ctk.CTkLabel(pwd_dlg, text="Ingresa tu contraseña para continuar:",
                     font=("Helvetica", 12, "bold")).pack(pady=(20,5))
        from views.styles import ENTRY as _ENTRY
        pwd_ent = ctk.CTkEntry(pwd_dlg, show="*", width=280, height=40, **_ENTRY)
        pwd_ent.pack(pady=8)
        pwd_result = {"ok": False}
        def _confirm_pwd():
            from security import verify_password as _vp
            usr = db.obtener_usuario(self._usuario_actual["username"])
            if usr and _vp(pwd_ent.get(), usr["password_hash"]):
                pwd_result["ok"] = True
                pwd_dlg.destroy()
            else:
                ctk.CTkLabel(pwd_dlg, text="Contraseña incorrecta.",
                             text_color="red").pack()
        btn_f = ctk.CTkFrame(pwd_dlg, fg_color="transparent"); btn_f.pack(pady=8)
        ctk.CTkButton(btn_f, text="Confirmar", fg_color="#E67E22",
                      width=120, command=_confirm_pwd).pack(side="left", padx=8)
        ctk.CTkButton(btn_f, text="Cancelar", fg_color="#7F8C8D",
                      width=120, command=pwd_dlg.destroy).pack(side="left", padx=8)
        pwd_dlg.wait_window()
        if not pwd_result["ok"]:
            return

        conf1 = _mb.askyesno("Confirmar Restauracion",
                             "Vas a restaurar desde: " + nombre + "\n\n"
                             "Esto reemplazara TODOS los datos actuales.\n"
                             "Se creara un backup de seguridad primero.\n\n"
                             "Deseas continuar?")
        if not conf1:
            return
        conf2 = _mb.askyesno("Ultima advertencia",
                             "Estas SEGURO?\n\n"
                             "Los datos actuales seran reemplazados.\n"
                             "Esta accion NO se puede deshacer.")
        if not conf2:
            return
        bk.hacer_backup()
        ok = bk.restaurar_backup(ruta)
        if ok:
            _mb.showinfo("Restauracion Exitosa",
                         "Base de datos restaurada correctamente.\n\n"
                         "La aplicacion se cerrara. Por favor reiniciala.")
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "RESTAURAR_BD", "BD restaurada desde: " + ruta)
            logger.info("BD restaurada desde: %s", ruta)
            self.after(500, self.destroy)
        else:
            _mb.showerror("Error", "No se pudo restaurar.\nRevise logs/app.log.")

    def _cambiar(self, name, func):
        for k, v in self._nav_btns.items():
            v.configure(fg_color=self.NARANJA if k == name else "transparent")
        func()

    def _cerrar_sesion(self):
        if self._usuario_actual:
            db.registrar_auditoria(
                self._usuario_actual.get("username","?"),
                "LOGOUT", "Cierre de sesión manual")
            logger.info("Sesión cerrada: %s", self._usuario_actual.get("username"))
        if self._timeout_job_id:
            self.after_cancel(self._timeout_job_id)
            self._timeout_job_id = None
        self.unbind_all("<Motion>")
        self.unbind_all("<KeyPress>")
        self.unbind_all("<Button>")
        self._usuario_actual = None
        self._mostrar_login()

    # ----------------------------------------------------------
    #  VISTAS
    # ----------------------------------------------------------

    def _limpiar_content(self):
        for w in self._content_card.winfo_children():
            w.destroy()

    def _vista_inicio(self):
        self._limpiar_content()

        # Scrollable main frame
        outer = ctk.CTkScrollableFrame(self._content_card, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=0, pady=0)
        frame = ctk.CTkFrame(outer, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        p_mes   = db.contar_pacientes_mes()
        b_stock = db.contar_insumos_bajo_stock()

        # ── Tarjetas estadísticas ─────────────────────────────
        stats = ctk.CTkFrame(frame, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 10))

        def card(parent, titulo, valor, icono):
            c = ctk.CTkFrame(parent, fg_color="#F4F6F7", corner_radius=15,
                             border_width=1, border_color="#D5D8DC")
            c.pack(side="left", fill="x", expand=True, padx=10)
            ctk.CTkLabel(c, text=icono, font=("Helvetica", 35),
                         text_color="#2C3E50").pack(pady=(15, 3))
            ctk.CTkLabel(c, text=titulo, font=("Helvetica", 12, "bold"),
                         text_color="#2C3E50").pack()
            ctk.CTkLabel(c, text=str(valor), font=("Helvetica", 26, "bold"),
                         text_color=self.NARANJA).pack(pady=(3, 15))

        card(stats, "Pacientes Atendidos (Mes)", p_mes,   "📊")
        card(stats, "Insumos en Stock Bajo",     b_stock, "⚠️")

        ctk.CTkButton(frame, text="📄 GENERAR REPORTE PDF GLOBAL",
                      fg_color="#001831", height=38, width=280,
                      font=("Helvetica", 11, "bold"),
                      command=lambda: self._generar_pdf()
                      ).pack(pady=(5, 15))

        # ── GRÁFICAS ──────────────────────────────────────────
        sep1 = ctk.CTkFrame(frame, height=2, fg_color="#E0E0E0")
        sep1.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(frame, text="📈 Estadísticas del Sistema",
                     font=("Helvetica", 15, "bold"), text_color="#2C3E50").pack(anchor="w")

        graficas_row = ctk.CTkFrame(frame, fg_color="transparent")
        graficas_row.pack(fill="x", pady=8)

        self._dibujar_graficas(graficas_row)

        # ── Buscador global ───────────────────────────────────
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="#E0E0E0")
        sep2.pack(fill="x", pady=(10, 8))
        ctk.CTkLabel(frame, text="🔍 Buscador General de Pacientes",
                     font=("Helvetica", 14, "bold"), text_color="#2C3E50").pack(anchor="w")

        bus_frame = ctk.CTkFrame(frame, fg_color="transparent")
        bus_frame.pack(fill="x", pady=6)
        self._bus_global = ctk.CTkEntry(
            bus_frame,
            placeholder_text="Buscar por nombre, cédula, apellido o motivo en todos los módulos...",
            height=38, fg_color="#F0F4F8", border_color="#B0BEC5",
            border_width=1, text_color="#1A1A2E")
        self._bus_global.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._bus_global.bind("<KeyRelease>", lambda e: self._buscar_global())
        ctk.CTkButton(bus_frame, text="Buscar", width=90, height=38,
                      fg_color=self.NARANJA,
                      command=self._buscar_global).pack(side="left")

        self._scroll_global = ctk.CTkScrollableFrame(
            frame, fg_color="white", border_width=1, height=200)
        self._scroll_global.pack(fill="both", expand=True, pady=5)
        ctk.CTkLabel(self._scroll_global,
                     text="Escribe para buscar pacientes en todos los módulos.",
                     text_color="gray", font=("Helvetica", 11)).pack(pady=15)

    def _dibujar_graficas(self, parent):
        """Dibuja 3 gráficas usando tkinter Frame nativo como contenedor."""
        import tkinter as _tk
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        AZUL    = "#000066"
        NARANJA = "#E67E22"
        COLORES = ["#2980B9","#E67E22","#27AE60","#8E44AD","#E74C3C","#F39C12"]

        # Contenedor nativo tkinter para las 3 gráficas
        tk_row = _tk.Frame(parent, bg="white")
        tk_row.pack(fill="both", expand=True)

        def make_tk_frame(parent, titulo):
            """Frame nativo con título CTkLabel encima."""
            outer = ctk.CTkFrame(parent, fg_color="white", corner_radius=12,
                                 border_width=1, border_color="#E0E0E0")
            outer.pack(side="left", fill="both", expand=True, padx=6)
            ctk.CTkLabel(outer, text=titulo, font=("Helvetica", 11, "bold"),
                         text_color="#2C3E50").pack(pady=(8, 2))
            # Frame tkinter nativo para matplotlib
            inner = _tk.Frame(outer, bg="white")
            inner.pack(padx=8, pady=(0, 8))
            return inner

        # ── Gráfica 1: Por módulo ─────────────────────────────
        f1 = make_tk_frame(parent, "Atenciones por Módulo")
        datos_mod = db.estadisticas_por_modulo()
        fig1, ax1 = plt.subplots(figsize=(3.4, 2.8))
        fig1.patch.set_facecolor("white")
        if datos_mod:
            areas  = [r[0] for r in datos_mod]
            totals = [r[1] for r in datos_mod]
            bars   = ax1.barh(areas, totals,
                              color=COLORES[:len(areas)], edgecolor="white")
            ax1.bar_label(bars, padding=3, fontsize=8, fontweight="bold")
            ax1.set_facecolor("#F8F9FA")
            ax1.tick_params(labelsize=7)
            ax1.spines[["top","right","bottom"]].set_visible(False)
        else:
            ax1.text(0.5, 0.5, "Sin datos\ndisponibles", ha="center", va="center", transform=ax1.transAxes, color="gray", fontsize=10)
            ax1.axis("off")
        fig1.tight_layout(pad=1.0)
        c1 = FigureCanvasTkAgg(fig1, master=f1)
        c1.draw(); c1.get_tk_widget().pack()
        plt.close(fig1)

        # ── Gráfica 2: Por tipo de persona ────────────────────
        f2 = make_tk_frame(parent, "Por Tipo de Persona")
        datos_tipo = db.estadisticas_por_tipo()
        fig2, ax2 = plt.subplots(figsize=(3.4, 2.8))
        fig2.patch.set_facecolor("white")
        if datos_tipo:
            tipos = [r[0] for r in datos_tipo]
            vals  = [r[1] for r in datos_tipo]
            wedges, texts, autotexts = ax2.pie(
                vals, labels=tipos, autopct="%1.0f%%",
                colors=COLORES[:len(tipos)],
                startangle=90, textprops={"fontsize": 7})
            for at in autotexts:
                at.set_fontsize(8); at.set_fontweight("bold")
        else:
            ax2.text(0.5, 0.5, "Sin datos\ndisponibles", ha="center", va="center", transform=ax2.transAxes, color="gray", fontsize=10)
            ax2.axis("off")
        fig2.tight_layout(pad=1.0)
        c2 = FigureCanvasTkAgg(fig2, master=f2)
        c2.draw(); c2.get_tk_widget().pack()
        plt.close(fig2)

        # ── Gráfica 3: Por mes ────────────────────────────────
        f3 = make_tk_frame(parent, "Atenciones por Mes")
        datos_mes = db.estadisticas_por_mes(6)
        fig3, ax3 = plt.subplots(figsize=(3.4, 2.8))
        fig3.patch.set_facecolor("white")
        if datos_mes:
            meses  = [r[0] for r in datos_mes]
            totals = [r[1] for r in datos_mes]
            ax3.plot(meses, totals, marker="o", linewidth=2,
                     color=AZUL, markerfacecolor=NARANJA,
                     markersize=7, markeredgecolor="white", markeredgewidth=1.5)
            ax3.fill_between(meses, totals, alpha=0.12, color=AZUL)
            ax3.set_facecolor("#F8F9FA")
            ax3.tick_params(axis="x", labelsize=7, rotation=30)
            ax3.tick_params(axis="y", labelsize=7)
            ax3.spines[["top","right"]].set_visible(False)
            for x, y in zip(meses, totals):
                ax3.annotate(str(y), (x, y), textcoords="offset points",
                             xytext=(0, 6), ha="center", fontsize=8, fontweight="bold")
        else:
            ax3.text(0.5, 0.5, "Sin datos\ndisponibles", ha="center", va="center", transform=ax3.transAxes, color="gray", fontsize=10)
            ax3.axis("off")
        fig3.tight_layout(pad=1.0)
        c3 = FigureCanvasTkAgg(fig3, master=f3)
        c3.draw(); c3.get_tk_widget().pack()
        plt.close(fig3)
    def _buscar_global(self):
        for w in self._scroll_global.winfo_children():
            w.destroy()

        termino = self._bus_global.get().strip()
        if not termino:
            ctk.CTkLabel(self._scroll_global,
                         text="Escribe para buscar pacientes en todos los módulos.",
                         text_color="gray", font=("Helvetica", 11)).pack(pady=15)
            return

        resultados = db.buscar_pacientes_global(termino)

        if not resultados:
            ctk.CTkLabel(self._scroll_global,
                         text=f"Sin resultados para: {termino}",
                         text_color="gray", font=("Helvetica", 11)).pack(pady=15)
            return

        # Cabecera
        cab = ctk.CTkFrame(self._scroll_global, fg_color="#000066", corner_radius=6)
        cab.pack(fill="x", padx=2, pady=(4, 2))
        for txt, w in [("Fecha", 130), ("Nombre", 180), ("Cédula", 100),
                       ("Tipo", 120), ("Módulo", 130), ("Motivo", 0)]:
            ctk.CTkLabel(cab, text=txt, text_color="white",
                         font=("Helvetica", 10, "bold"),
                         width=w, anchor="w").pack(side="left", padx=6, pady=5)

        COLOR_TIPO = {
            "Estudiante":      ("#EAF4FB", "#2980B9"),
            "Docente":         ("#EAFAF1", "#27AE60"),
            "Personal Obrero": ("#FEF9E7", "#D4AC0D"),
        }

        for i, (pid, fec, nom, ape, ced, tipo, area, mot) in enumerate(resultados):
            bg = "#F9F9F9" if i % 2 == 0 else "#FFFFFF"
            row = ctk.CTkFrame(self._scroll_global, fg_color=bg,
                               corner_radius=0, border_width=0)
            row.pack(fill="x", padx=2, pady=1)

            ctk.CTkLabel(row, text=fec, text_color="gray",
                         font=("Helvetica", 9), width=130, anchor="w").pack(side="left", padx=6, pady=6)
            ctk.CTkLabel(row, text=f"{nom} {ape}".upper(), text_color="black",
                         font=("Helvetica", 10, "bold"), width=180, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=ced, text_color="#555",
                         font=("Helvetica", 10), width=100, anchor="w").pack(side="left")

            # Badge tipo
            tipo_txt = tipo or "—"
            tbg, tfg = COLOR_TIPO.get(tipo_txt, ("#F0F0F0", "#555"))
            badge = ctk.CTkFrame(row, fg_color=tbg, corner_radius=6, width=120)
            badge.pack(side="left", padx=4)
            ctk.CTkLabel(badge, text=tipo_txt, text_color=tfg,
                         font=("Helvetica", 9, "bold")).pack(padx=6, pady=3)

            ctk.CTkLabel(row, text=area, text_color=self.NARANJA,
                         font=("Helvetica", 10, "bold"), width=130, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=mot, text_color="#333",
                         font=("Helvetica", 10, "italic"),
                         wraplength=250, anchor="w").pack(side="left", padx=4, fill="x", expand=True)

    def _vista_area(self, area):
        self._limpiar_content()
        VistaArea(self._content_card, area, self._generar_pdf,
                  self._usuario_actual).pack(fill="both", expand=True)

    def _vista_insumos(self):
        self._limpiar_content()
        VistaInsumos(self._content_card).pack(fill="both", expand=True)

    def _vista_usuarios(self):
        self._limpiar_content()
        VistaUsuarios(self._content_card,
                      self._usuario_actual).pack(fill="both", expand=True)

    def _vista_auditoria(self):
        self._limpiar_content()
        VistaAuditoria(self._content_card).pack(fill="both", expand=True)

    # ----------------------------------------------------------
    #  PDF
    # ----------------------------------------------------------

    def _generar_pdf(self, area=None):
        """Genera PDF con filtro opcional de rango de fechas."""
        from datetime import datetime as _dt

        # Ventana de filtro de fechas
        dlg = ctk.CTkToplevel(self)
        dlg.title("Filtro de Reporte")
        dlg.geometry("380x240")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="📅 Rango de Fechas (opcional)",
                     font=("Helvetica", 14, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dlg, text="Dejar vacío para incluir todos los registros.",
                     font=("Helvetica", 10), text_color="gray").pack()

        from views.styles import ENTRY
        row1 = ctk.CTkFrame(dlg, fg_color="transparent"); row1.pack(pady=10)
        ctk.CTkLabel(row1, text="Desde:", width=60, anchor="w",
                     font=("Helvetica", 11, "bold")).pack(side="left")
        ent_ini = ctk.CTkEntry(row1, placeholder_text="DD/MM/AAAA",
                               width=130, height=36, **ENTRY)
        ent_ini.pack(side="left", padx=(4, 20))
        ctk.CTkLabel(row1, text="Hasta:", width=60, anchor="w",
                     font=("Helvetica", 11, "bold")).pack(side="left")
        ent_fin = ctk.CTkEntry(row1, placeholder_text="DD/MM/AAAA",
                               width=130, height=36, **ENTRY)
        ent_fin.pack(side="left", padx=4)

        resultado = {"ok": False, "ini": None, "fin": None}

        def confirmar():
            resultado["ini"] = ent_ini.get().strip()
            resultado["fin"] = ent_fin.get().strip()
            resultado["ok"]  = True
            dlg.destroy()

        btns = ctk.CTkFrame(dlg, fg_color="transparent"); btns.pack(pady=10)
        ctk.CTkButton(btns, text="📄 Generar PDF", fg_color="#001831",
                      width=150, command=confirmar).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#7F8C8D",
                      width=100, command=dlg.destroy).pack(side="left", padx=8)

        dlg.wait_window()
        if not resultado["ok"]:
            return

        fecha_str = _dt.now().strftime("%d-%m-%Y")
        sufijo    = ""
        if resultado["ini"] and resultado["fin"]:
            ini_s = resultado["ini"].replace("/", "-")
            fin_s = resultado["fin"].replace("/", "-")
            sufijo = f"_{ini_s}_al_{fin_s}"

        if area:
            nombre_sugerido = f"{area.replace(' ', '_')}{sufijo}_{fecha_str}.pdf"
        else:
            nombre_sugerido = f"Reporte_Global{sufijo}_{fecha_str}.pdf"

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=nombre_sugerido,
            filetypes=[("PDF files", "*.pdf")])
        if not filename:
            return

        # Determinar datos según filtro
        usa_rango = bool(resultado["ini"] and resultado["fin"])
        try:
            doc    = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            elems  = []
            from datetime import datetime as _dt2
            ahora  = _dt2.now().strftime("%d/%m/%Y %H:%M")
            titulo = "Reporte General SaluDigital" if not area else f"Reporte: {area}"
            elems.append(Paragraph(f"<b>{titulo}</b>", styles['Title']))
            elems.append(Paragraph(
                f"Generado: {ahora}  |  SaluDigital UNELLEZ VIPI",
                styles['Normal']
            ))
            elems.append(Spacer(1, 15))

            if usa_rango:
                rows = db.obtener_pacientes_rango(
                    resultado["ini"], resultado["fin"], area)
                rango_txt = f"{resultado['ini']} al {resultado['fin']}"
            else:
                rows = db.obtener_pacientes_por_area(area) if area else db.obtener_todos_pacientes()
                rango_txt = "Todos los registros"

            total = len(rows)
            elems.append(Paragraph(
                f"Período: <b>{rango_txt}</b>  |  Total de registros: <b>{total}</b>",
                styles['Normal']
            ))
            elems.append(Spacer(1, 10))

            data = [["FECHA", "CÉDULA", "NOMBRE", "APELLIDO", "TIPO", "MOTIVO/ÁREA"]]
            for row in rows:
                data.append(list(row))

            t = Table(data, colWidths=[85, 75, 85, 85, 90, 110])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor("#000066")),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.whitesmoke),
                ('FONTNAME',      (0, 0), (-1, 0),  "Helvetica-Bold"),
                ('GRID',          (0, 0), (-1,-1),  0.5, colors.grey),
                ('FONTSIZE',      (0, 0), (-1,-1),  8),
                ('ROWBACKGROUNDS',(0, 1), (-1,-1),  [colors.white, colors.HexColor("#F4F6F7")]),
            ]))
            elems.append(t)
            doc.build(elems)
            logger.info("PDF generado: %s", filename)
            messagebox.showinfo("PDF", "Reporte generado con éxito.")
        except PermissionError:
            logger.error("Permiso denegado al escribir PDF: %s", filename)
            messagebox.showerror("Error", "No se pudo guardar el PDF.\n"
                                          "Verifique que el archivo no esté abierto.")
        except Exception as e:
            logger.error("Error al generar PDF: %s", e)
            messagebox.showerror("Error", "No se pudo crear el PDF.\nRevise logs/app.log.")
