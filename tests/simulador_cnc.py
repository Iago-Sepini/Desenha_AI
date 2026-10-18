"""
simulador_cnc.py — Simulador visual de G-code para plotter/CNC GRBL.

Não conecta à porta serial e NÃO movimenta a máquina real.
Abre uma janela, carrega um arquivo .gcode, desenha a trajetória XY
e simula a caneta levantada/abaixada.

Execute no Windows:
    py -3.10 tests/simulador_cnc.py

Configuração padrão:
    Área física X = 16 mm, Y = 24 mm
    Z0 = caneta levantada
    Z20 = caneta abaixada
"""

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


# Limites da área da sua máquina (mm)
MAX_X = 16.0
MAX_Y = 24.0

# Convenção informada para seu eixo Z
Z_UP = 0.0
Z_DOWN = 20.0

# Margem interna da área de desenho na janela
CANVAS_MARGIN = 42


def ler_gcode(caminho):
    """Lê G-code simples em coordenadas absolutas (G90), G0/G1, X/Y/Z."""
    comandos = []
    x, y, z = 0.0, 0.0, Z_UP
    modo_absoluto = True

    with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
        for numero_linha, original in enumerate(arquivo, start=1):
            linha = original.split(";", 1)[0].strip()
            if not linha or linha.startswith("("):
                continue

            # Remove comentários entre parênteses
            linha = re.sub(r"\([^)]*\)", "", linha).strip()
            if not linha:
                continue

            upper = linha.upper()
            if re.search(r"\bG90\b", upper):
                modo_absoluto = True
            if re.search(r"\bG91\b", upper):
                modo_absoluto = False

            match_modo = re.search(r"\bG0?([01])\b", upper)
            if not match_modo:
                continue

            modo = int(match_modo.group(1))
            valores = {}
            for eixo in ("X", "Y", "Z"):
                m = re.search(rf"\b{eixo}\s*(-?\d+(?:\.\d+)?)", upper)
                if m:
                    valores[eixo] = float(m.group(1))

            novo_x = valores.get("X", x)
            novo_y = valores.get("Y", y)
            novo_z = valores.get("Z", z)

            if not modo_absoluto:
                novo_x = x + valores.get("X", 0.0)
                novo_y = y + valores.get("Y", 0.0)
                novo_z = z + valores.get("Z", 0.0)

            pen_baixada_antes = z >= (Z_DOWN / 2)
            pen_baixada_depois = novo_z >= (Z_DOWN / 2)

            # Só cria segmento quando houver deslocamento XY.
            if "X" in valores or "Y" in valores:
                comandos.append({
                    "linha": numero_linha,
                    "modo": modo,
                    "x0": x, "y0": y,
                    "x1": novo_x, "y1": novo_y,
                    "z0": z, "z1": novo_z,
                    "desenho": pen_baixada_antes and pen_baixada_depois and modo == 1,
                })

            x, y, z = novo_x, novo_y, novo_z

    if not comandos:
        raise ValueError("Não encontrei movimentos G0/G1 com coordenadas X/Y no arquivo.")
    return comandos


class SimuladorCNC:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador CNC / GRBL — sem conexão com a máquina")
        self.root.geometry("1050x720")
        self.root.minsize(800, 560)

        self.comandos = []
        self.indice = 0
        self.executando = False
        self.after_id = None
        self.caminho = None
        self.velocidade = tk.IntVar(value=35)

        self._montar_interface()
        self._desenhar_grade()
        self._atualizar_status()

    def _montar_interface(self):
        barra = ttk.Frame(self.root, padding=8)
        barra.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(barra, text="Abrir G-code…", command=self.abrir_arquivo).pack(side=tk.LEFT, padx=(0, 6))
        self.btn_iniciar = ttk.Button(barra, text="▶ Simular", command=self.iniciar)
        self.btn_iniciar.pack(side=tk.LEFT, padx=4)
        self.btn_pausar = ttk.Button(barra, text="⏸ Pausar", command=self.pausar, state=tk.DISABLED)
        self.btn_pausar.pack(side=tk.LEFT, padx=4)
        ttk.Button(barra, text="⏭ Próximo movimento", command=self.proximo).pack(side=tk.LEFT, padx=4)
        ttk.Button(barra, text="↺ Reiniciar", command=self.reiniciar).pack(side=tk.LEFT, padx=4)

        velocidade_frame = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        velocidade_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(velocidade_frame, text="Velocidade da simulação:").pack(side=tk.LEFT)
        ttk.Scale(
            velocidade_frame, from_=5, to=150, variable=self.velocidade,
            orient=tk.HORIZONTAL, length=220
        ).pack(side=tk.LEFT, padx=8)
        self.lbl_arquivo = ttk.Label(velocidade_frame, text="Nenhum arquivo carregado")
        self.lbl_arquivo.pack(side=tk.LEFT, padx=12)

        corpo = ttk.Frame(self.root, padding=(8, 2, 8, 8))
        corpo.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(corpo, background="#101820", highlightthickness=1,
                                highlightbackground="#566575")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._redesenhar_tudo)

        lateral = ttk.Frame(corpo, width=235, padding=(12, 4))
        lateral.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(lateral, text="ESTADO DA SIMULAÇÃO", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))
        self.lbl_estado = ttk.Label(lateral, text="Aguardando G-code", wraplength=215)
        self.lbl_estado.pack(anchor="w", pady=3)

        self.lbl_progresso = ttk.Label(lateral, text="Movimentos: 0 / 0")
        self.lbl_progresso.pack(anchor="w", pady=3)

        self.lbl_posicao = ttk.Label(lateral, text="X: 0.000 mm\nY: 0.000 mm\nZ: 0.000 mm", justify=tk.LEFT)
        self.lbl_posicao.pack(anchor="w", pady=8)

        ttk.Separator(lateral).pack(fill=tk.X, pady=10)
        ttk.Label(lateral, text="LEGENDA", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 7))
        self._legenda(lateral, "#42d392", "Traço desenhado (caneta baixa)")
        self._legenda(lateral, "#f0b45a", "Deslocamento (caneta levantada)")
        self._legenda(lateral, "#ff5d73", "Posição atual da caneta")

        ttk.Separator(lateral).pack(fill=tk.X, pady=10)
        ttk.Label(lateral, text="ÁREA DA MÁQUINA", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        ttk.Label(lateral, text="X: 0 a 16 mm\nY: 0 a 24 mm\nZ0 = levantada\nZ20 = abaixada", justify=tk.LEFT).pack(anchor="w")

        ttk.Separator(lateral).pack(fill=tk.X, pady=10)
        ttk.Label(
            lateral,
            text="Este programa apenas simula o arquivo. Não envia comandos para COM18 e não controla a CNC real.",
            wraplength=215, foreground="#a04400", justify=tk.LEFT
        ).pack(anchor="w")

        self.barra_progresso = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.barra_progresso.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))

    def _legenda(self, parent, cor, texto):
        linha = tk.Frame(parent)
        linha.pack(anchor="w", padx=5, pady=2)

        amostra = tk.Canvas(
            linha,
            width=24,
            height=12,
            highlightthickness=0,
            background="#20242b"
        )
        amostra.pack(side="left", padx=(0, 6))

        amostra.create_line(
            2, 6, 22, 6,
            fill=cor,
            width=3
        )

        tk.Label(
            linha,
            text=texto,
            background="#20242b",
            foreground="#ffffff"
        ).pack(side="left")
    def _area(self):
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        margem = CANVAS_MARGIN
        escala = min((w - 2 * margem) / MAX_X, (h - 2 * margem) / MAX_Y)
        largura = MAX_X * escala
        altura = MAX_Y * escala
        x0 = (w - largura) / 2
        y0 = (h - altura) / 2
        return x0, y0, escala

    def _xy_canvas(self, x, y):
        x0, y0, escala = self._area()
        return x0 + x * escala, y0 + (MAX_Y - y) * escala

    def _desenhar_grade(self):
        self.canvas.delete("grade")
        x0, y0, escala = self._area()
        x1 = x0 + MAX_X * escala
        y1 = y0 + MAX_Y * escala

        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#8fa3b8", width=2, tags="grade")
        for x in range(int(MAX_X) + 1):
            px, _ = self._xy_canvas(x, 0)
            self.canvas.create_line(px, y0, px, y1, fill="#263746", tags="grade")
            if x % 2 == 0:
                self.canvas.create_text(px, y1 + 15, text=str(x), fill="#d4e0ea", font=("Segoe UI", 8), tags="grade")
        for y in range(int(MAX_Y) + 1):
            _, py = self._xy_canvas(0, y)
            self.canvas.create_line(x0, py, x1, py, fill="#263746", tags="grade")
            if y % 2 == 0:
                self.canvas.create_text(x0 - 17, py, text=str(y), fill="#d4e0ea", font=("Segoe UI", 8), tags="grade")
        self.canvas.create_text((x0 + x1) / 2, max(12, y0 - 18), text="Área de trabalho: 16 × 24 mm",
                                fill="#e7eef5", font=("Segoe UI", 10, "bold"), tags="grade")

    def _redesenhar_tudo(self, event=None):
        self.canvas.delete("all")
        self._desenhar_grade()
        self._desenhar_trajetoria()

    def _desenhar_trajetoria(self):
        # Trajetória percorrida até o índice atual.
        for i, cmd in enumerate(self.comandos[:self.indice]):
            x0, y0 = self._xy_canvas(cmd["x0"], cmd["y0"])
            x1, y1 = self._xy_canvas(cmd["x1"], cmd["y1"])
            if cmd["desenho"]:
                cor, largura, dash = "#42d392", 2.4, None
            else:
                cor, largura, dash = "#f0b45a", 1.1, (4, 4)
            kwargs = {"fill": cor, "width": largura, "tags": "trajetoria"}
            if dash:
                kwargs["dash"] = dash
            self.canvas.create_line(x0, y0, x1, y1, **kwargs)

        if self.comandos and self.indice > 0:
            cmd = self.comandos[self.indice - 1]
            px, py = self._xy_canvas(cmd["x1"], cmd["y1"])
            self.canvas.create_oval(px - 5, py - 5, px + 5, py + 5,
                                    fill="#ff5d73", outline="white", width=1, tags="posicao")
            self.lbl_posicao.config(
                text=f"X: {cmd['x1']:.3f} mm\nY: {cmd['y1']:.3f} mm\nZ: {cmd['z1']:.3f} mm"
            )
            self.lbl_estado.config(text="Caneta abaixada / desenhando" if cmd["desenho"] else "Deslocamento / caneta levantada")
        elif not self.comandos:
            self.lbl_posicao.config(text=f"X: 0.000 mm\nY: 0.000 mm\nZ: {Z_UP:.3f} mm")
            self.lbl_estado.config(text="Aguardando G-code")
        else:
            self.lbl_posicao.config(text=f"X: {self.comandos[0]['x0']:.3f} mm\nY: {self.comandos[0]['y0']:.3f} mm\nZ: {self.comandos[0]['z0']:.3f} mm")
            self.lbl_estado.config(text="Pronto para iniciar")

    def abrir_arquivo(self):
        self.pausar()
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo G-code",
            filetypes=[("Arquivos G-code", "*.gcode *.gc *.nc *.tap"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return
        try:
            self.comandos = ler_gcode(caminho)
        except Exception as erro:
            messagebox.showerror("Erro ao ler G-code", str(erro))
            return
        self.caminho = caminho
        self.indice = 0
        self.lbl_arquivo.config(text=Path(caminho).name)
        self.barra_progresso["value"] = 0
        self._redesenhar_tudo()
        self._atualizar_status()

    def _atualizar_status(self):
        self.lbl_progresso.config(text=f"Movimentos: {self.indice} / {len(self.comandos)}")
        if self.comandos:
            self.barra_progresso["value"] = 100 * self.indice / len(self.comandos)
        else:
            self.barra_progresso["value"] = 0

    def iniciar(self):
        if not self.comandos:
            messagebox.showinfo("Abrir G-code", "Clique em 'Abrir G-code…' e selecione seu arquivo.")
            return
        if self.indice >= len(self.comandos):
            self.indice = 0
            self._redesenhar_tudo()
        self.executando = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_pausar.config(state=tk.NORMAL)
        self._passo_animacao()

    def _passo_animacao(self):
        if not self.executando:
            return
        if self.indice >= len(self.comandos):
            self.pausar()
            self.lbl_estado.config(text="Simulação concluída")
            return
        self.indice += 1
        self._redesenhar_tudo()
        self._atualizar_status()
        atraso = max(5, int(5000 / max(5, self.velocidade.get())))
        self.after_id = self.root.after(atraso, self._passo_animacao)

    def pausar(self):
        self.executando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_pausar.config(state=tk.DISABLED)

    def proximo(self):
        self.pausar()
        if self.indice < len(self.comandos):
            self.indice += 1
            self._redesenhar_tudo()
            self._atualizar_status()

    def reiniciar(self):
        self.pausar()
        self.indice = 0
        self._redesenhar_tudo()
        self._atualizar_status()


def main():
    root = tk.Tk()
    SimuladorCNC(root)
    root.mainloop()


if __name__ == "__main__":
    main()
