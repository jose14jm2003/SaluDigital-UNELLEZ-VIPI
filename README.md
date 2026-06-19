# 🏥 SaluDigital UNELLEZ VIPI
### Sistema de Gestión de Salud Estudiantil

> Aplicación de escritorio desarrollada en Python para la gestión de atenciones médicas, inventario de insumos y estadísticas del Servicio de Salud de la Universidad Nacional Experimental de los Llanos Occidentales Ezequiel Zamora — Núcleo VIPI.

---

## 📋 Descripción

SaluDigital centraliza el registro de pacientes de cuatro áreas médicas (Servicio Médico, Laboratorio, Odontología y Fisioterapia), controla el inventario de insumos, genera reportes en PDF y muestra estadísticas gráficas en tiempo real. Incluye autenticación segura, cifrado de datos sensibles y sistema de respaldo automático.

---

## 🖥️ Capturas de Pantalla

| Login | Dashboard |
|-------|-----------|
| Pantalla de inicio con foto del campus y logo UNELLEZ | Panel principal con estadísticas y gráficas |

---

## ⚙️ Requisitos del Sistema

- **Sistema Operativo:** Windows 10 / 11
- **Python:** 3.11 o superior → https://www.python.org/downloads/
- **pip:** incluido con Python

---

## 🚀 Instalación y Ejecución

### Paso 1 — Descargar el proyecto

Opción A — Con Git:
```bash
git clone https://github.com/TU_USUARIO/SaluDigital-UNELLEZ-VIPI.git
cd SaluDigital-UNELLEZ-VIPI
```

Opción B — Sin Git:
1. Clic en el botón verde **"Code"** → **"Download ZIP"**
2. Extraer el ZIP en una carpeta de tu preferencia
3. Abrir esa carpeta

---

### Paso 2 — Instalar las dependencias

Abre una terminal (cmd) dentro de la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt
```

Esto instalará automáticamente:
- `customtkinter` — interfaz gráfica moderna
- `Pillow` — manejo de imágenes
- `reportlab` — generación de PDF
- `matplotlib` — gráficas estadísticas

---

### Paso 3 — Ejecutar la aplicación

```bash
python main.py
```

La base de datos se crea automáticamente en la primera ejecución. No se requiere ninguna configuración adicional.

---

## 🔐 Credenciales por Defecto

| Campo | Valor |
|-------|-------|
| **Usuario** | `admin` |
| **Contraseña** | `Admin1234!` |

> ⚠️ Se recomienda cambiar la contraseña desde el menú **🔑 Contraseña** después del primer inicio de sesión.

---

## 📁 Estructura del Proyecto

```
SaluDigital-UNELLEZ-VIPI/
│
├── main.py                  ← Punto de entrada
├── database.py              ← Capa de datos (SQL)
├── security.py              ← Autenticación y cifrado
├── backup.py                ← Respaldo y restauración
├── logger_config.py         ← Configuración de logs
├── requirements.txt         ← Dependencias
│
├── views/
│   ├── dashboard.py         ← Panel principal
│   ├── login.py             ← Pantalla de acceso
│   ├── vista_area.py        ← Módulos médicos
│   ├── vista_insumos.py     ← Inventario
│   ├── vista_usuarios.py    ← Cambio de contraseña
│   ├── vista_auditoria.py   ← Registro de auditoría
│   ├── widgets.py           ← Ventanas modales
│   └── styles.py            ← Estilos globales
│
├── assets/
│   ├── logo_unellez.png     ← Logo institucional
│   └── fondo_unellez.png    ← Foto del campus
│
├── backups/                 ← Copias de seguridad (auto-generada)
└── logs/                    ← Registro de eventos (auto-generada)
```

---

## 🧩 Módulos del Sistema

| Módulo | Descripción |
|--------|-------------|
| 🏠 **Inicio** | Panel con estadísticas, gráficas y buscador global |
| 🩺 **Servicio Médico** | Registro y gestión de consultas médicas |
| 🧪 **Laboratorio** | Registro de análisis y resultados |
| 🦷 **Odontología** | Atenciones odontológicas |
| ⚡ **Fisioterapia** | Sesiones de fisioterapia |
| 📦 **Insumos** | Inventario con alertas y historial de movimientos |
| 🔑 **Contraseña** | Cambio de contraseña del usuario activo |
| 🔍 **Auditoría** | Registro de todas las acciones críticas (solo admin) |

---

## 🔒 Características de Seguridad

- Contraseñas almacenadas con **PBKDF2-SHA256** (260,000 iteraciones)
- Bloqueo tras **3 intentos fallidos** de inicio de sesión
- **Cierre automático** de sesión por 15 minutos de inactividad
- Cifrado de campos sensibles (cédula, diagnóstico, tratamiento) con **XOR + Base64**
- **Registro de auditoría** de todas las acciones críticas
- **Backup automático** al iniciar sesión (conserva los últimos 5)
- Restauración de backup protegida con **confirmación de contraseña**
- Validación de contraseña segura: mínimo 8 caracteres, mayúscula, número y símbolo

---

## 📊 Funcionalidades Destacadas

- ✅ Cálculo automático de **edad** desde la fecha de nacimiento
- ✅ Cálculo automático de **IMC** con clasificación OMS (Bajo peso / Normal / Sobrepeso / Obesidad I-III)
- ✅ **Historial clínico** por paciente en todos los módulos
- ✅ **Buscador global** de pacientes por nombre, cédula o motivo
- ✅ Generación de **reportes PDF** con filtro por rango de fechas
- ✅ **Alertas automáticas** de insumos con stock bajo
- ✅ **Gráficas estadísticas** en tiempo real (barras, torta, línea temporal)

---

## 🛠️ Tecnologías Utilizadas

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| Python | 3.11+ | Lenguaje principal |
| CustomTkinter | 5.x | Interfaz gráfica |
| SQLite3 | (incluido) | Base de datos local |
| ReportLab | 4.x | Generación de PDF |
| Matplotlib | 3.x | Gráficas estadísticas |
| Pillow | 10.x | Procesamiento de imágenes |

---

## 👩‍💻 Desarrollado por

**Kaira Henao y José Marcano**
Universidad Nacional Experimental de los Llanos Occidentales Ezequiel Zamora — UNELLEZ VIPI
Proyecto de Planificación de Proyectos · 2026

---

## 📄 Licencia

Este proyecto fue desarrollado con fines académicos para la UNELLEZ VIPI.
