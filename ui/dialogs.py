import tkinter as tk
from tkinter import messagebox


def confirmar_operador_cnc() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        resposta = messagebox.askyesno(
            "Confirmação de Segurança - CNC",
            "Max solicitou o início da CNC.\n\nDeseja realmente autorizar e iniciar a impressão?",
        )
        root.destroy()
        return resposta
    except Exception as e:
        print(f"[CNC] Erro ao abrir janela de confirmação: {e}")
        return False