"""
main.py — Punto de entrada de SaluDigital
Ejecutar: python main.py
"""

from views.dashboard import AppSalud

if __name__ == "__main__":
    app = AppSalud()
    app.mainloop()
