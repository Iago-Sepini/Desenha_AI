"""
simulador_cnc.py — Simulador visual de G-code para plotter/CNC GRBL
com controle manual por botões e função de resete completo de posição.
"""

import re
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

try:
    import serial  # pip install pyserial
except ImportError:
    serial = None

# Limites físicos da CNC (em mm) — 11 cm x 19 cm
MAX_X = 110.0
MAX_Y = 190.0
MAX_Z = 15.0

Z_UP = 0.0
Z_DOWN = 3.0

CANVAS_MARGIN = 42

PORTA_PADRAO = "COM20"
BAUDRATE = 115200
FEED_JOG = 200
PASSO_JOG_PADRAO = 1.0
INTERVALO_MIN_JOG = 0.05

DIRECOES = {
    "Up":    ("NORTE", 0, +1, 0),
    "Down":  ("SUL",   0, -1, 0),
    "Right": ("LESTE", +1, 0, 0),
    "Left":  ("OESTE", -1, 0, 0),
}


def ler_gcode(caminho):
    comandos = []
    x, y, z = 0.0, 0.0, Z_UP
    modo_absoluto = True
    modo_atual = 0  # 0 para G0, 1 para G1 (suporte modal)

    with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
        for numero_linha, original in enumerate(arquivo, start=1):
            linha = original.split(";", 1)[0].strip()
            if not linha or linha.startswith("("):
                continue
            linha = re.sub(r"\([^)]*\)", "", linha).strip()
            if not linha:
                continue

            upper = linha.upper()
            if re.search(r"\bG90\b", upper): modo_absoluto = True
            if re.search(r"\bG91\b", upper): modo_absoluto = False

            match_modo = re.search(r"\bG0?([01])\b", upper)
            if match_modo:
                modo_atual = int(match_modo.group(1))

            valores = {}
            for eixo in ("X", "Y", "Z"):
                m = re.search(rf"\b{eixo}\s*(-?\d+(?:\.\d+)?)", upper)
                if m: valores[eixo] = float(m.group(1))

            if not valores:
                continue

            if modo_absoluto:
                novo_x = valores.get("X", x)
                novo_y = valores.get("Y", y)
                novo_z = valores.get("Z", z)
            else:
                novo_x = x + valores.get("X", 0.0)
                novo_y = y + valores.get("Y", 0.0)
                novo_z = z + valores.get("Z", 0.0)

            pen_baixada_antes = z >= (Z_DOWN / 2)
            pen_baixada_depois = novo_z >= (Z_DOWN / 2)

            comandos.append({
                "linha": numero_linha,
                "modo": modo_atual,
                "gcode_raw": linha,
                "x0": x, "y0": y, "x1": novo_x, "y1": novo_y,
                "z0": z, "z1": novo_z,
                "desenho": pen_baixada_antes and pen_baixada_depois and modo_atual == 1,
            })
            x, y, z = novo_x, novo_y, novo_z

    if not comandos:
        raise ValueError("Não encontrei movimentos válidos no arquivo G-code.")
    return comandos


class SimuladorCNC:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador CNC / GRBL - Resete de Posição")
        self.root.geometry("1120x800")
        self.root.minsize(850, 650)

        self.comandos = []
        self.indice = 0
        self.executando = False
        self.after_id = None
        self.caminho = None
        self.velocidade = tk.IntVar(value=35)

        self.serial = None
        self.jog_x = 0.0
        self.jog_y = 0.0
        self.jog_z = Z_UP
        self.ultimo_jog = 0.0
        self.passo_jog = tk.DoubleVar(value=PASSO_JOG_PADRAO)
        self.porta = tk.StringVar(value=PORTA_PADRAO)

        self._montar_interface()
        self._desenhar_grade()
        self._atualizar_status()

        self.canvas.focus_set()
        for tecla in DIRECOES:
            self.canvas.bind(f"<{tecla}>", self._tecla_direcao)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        self.root.bind_all("<ButtonRelease-1>", self._devolver_foco)
        self.root.protocol("WM_DELETE_WINDOW", self._fechar)

    def _montar_interface(self):
        barra = ttk.Frame(self.root, padding=8)
        barra.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(barra, text="Abrir G-code…", command=self.abrir_arquivo, takefocus=False).pack(side=tk.LEFT, padx=(0, 6))
        self.btn_iniciar = ttk.Button(barra, text="▶ Simular", command=self.iniciar, takefocus=False)
        self.btn_iniciar.pack(side=tk.LEFT, padx=4)
        self.btn_pausar = ttk.Button(barra, text="⏸ Pausar", command=self.pausar, state=tk.DISABLED, takefocus=False)
        self.btn_pausar.pack(side=tk.LEFT, padx=4)
        ttk.Button(barra, text="⏭ Próximo", command=self.proximo, takefocus=False).pack(side=tk.LEFT, padx=4)
        ttk.Button(barra, text="↺ Reiniciar", command=self.reiniciar, takefocus=False).pack(side=tk.LEFT, padx=4)
        
        # BOTÃO DE RESETE COMPLETO NA BARRA SUPERIOR
        ttk.Button(barra, text="🔄 Resete Geral (0,0,0)", command=self.resete_completo, takefocus=False).pack(side=tk.LEFT, padx=12)

        velocidade_frame = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        velocidade_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(velocidade_frame, text="Velocidade:").pack(side=tk.LEFT)
        ttk.Scale(velocidade_frame, from_=5, to=150, variable=self.velocidade, orient=tk.HORIZONTAL, length=180, takefocus=False).pack(side=tk.LEFT, padx=8)
        self.lbl_arquivo = ttk.Label(velocidade_frame, text="Nenhum arquivo carregado")
        self.lbl_arquivo.pack(side=tk.LEFT, padx=12)

        corpo = ttk.Frame(self.root, padding=(8, 2, 8, 8))
        corpo.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(corpo, background="#101820", highlightthickness=1, highlightbackground="#566575", takefocus=True)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._redesenhar_tudo)

        lateral = ttk.Frame(corpo, width=270, padding=(12, 4))
        lateral.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(lateral, text="ESTADO", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
        self.lbl_estado = ttk.Label(lateral, text="Aguardando conexão", wraplength=245, foreground="#00aa00")
        self.lbl_estado.pack(anchor="w", pady=2)

        self.lbl_posicao = ttk.Label(lateral, text="X: 0.000 | Y: 0.000 | Z: 0.000", justify=tk.LEFT)
        self.lbl_posicao.pack(anchor="w", pady=2)

        ttk.Separator(lateral).pack(fill=tk.X, pady=6)
        ttk.Label(lateral, text="CONEXÃO E COMANDOS GRBL", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))

        linha_porta = ttk.Frame(lateral)
        linha_porta.pack(anchor="w", fill=tk.X, pady=2)
        entrada_porta = ttk.Entry(linha_porta, textvariable=self.porta, width=8)
        entrada_porta.pack(side=tk.LEFT)
        self.btn_conectar = ttk.Button(linha_porta, text="Conectar", command=self.alternar_conexao, takefocus=False)
        self.btn_conectar.pack(side=tk.LEFT, padx=4)

        linha_grbl = ttk.Frame(lateral)
        linha_grbl.pack(anchor="w", fill=tk.X, pady=2)
        ttk.Button(linha_grbl, text="Destravar ($X)", command=lambda: self.enviar_direto("$X"), takefocus=False).pack(side=tk.LEFT, padx=2)
        ttk.Button(linha_grbl, text="Status (?)", command=lambda: self.enviar_direto("?"), takefocus=False).pack(side=tk.LEFT, padx=2)
        
        # BOTÃO PARA ZERAR NA LATERAL
        ttk.Button(linha_grbl, text="Zerar Aqui", command=self.resete_completo, takefocus=False).pack(side=tk.LEFT, padx=2)

        linha_passo = ttk.Frame(lateral)
        linha_passo.pack(anchor="w", pady=4)
        ttk.Label(linha_passo, text="Passo (mm):").pack(side=tk.LEFT)
        spin_passo = ttk.Spinbox(linha_passo, from_=0.1, to=10.0, increment=1.0, textvariable=self.passo_jog, width=5, takefocus=False)
        spin_passo.pack(side=tk.LEFT, padx=6)

        frame_botoes = ttk.LabelFrame(lateral, text="Movimento Manual (Jog)", padding=6)
        frame_botoes.pack(anchor="w", fill=tk.X, pady=4)

        ttk.Button(frame_botoes, text="▲ Y+", width=6, command=lambda: self.mover("NORTE", 0, +1, 0), takefocus=False).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(frame_botoes, text="Z+", width=6, command=lambda: self.mover("Z+", 0, 0, +1), takefocus=False).grid(row=0, column=3, padx=(8, 2), pady=2)

        ttk.Button(frame_botoes, text="◀ X-", width=6, command=lambda: self.mover("OESTE", -1, 0, 0), takefocus=False).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(frame_botoes, text="⟳", width=4, command=self.resete_completo, takefocus=False).grid(row=1, column=1, padx=2, pady=2)
        ttk.Button(frame_botoes, text="X+ ▶", width=6, command=lambda: self.mover("LESTE", +1, 0, 0), takefocus=False).grid(row=1, column=2, padx=2, pady=2)
        ttk.Button(frame_botoes, text="Z-", width=6, command=lambda: self.mover("Z-", 0, 0, -1), takefocus=False).grid(row=1, column=3, padx=(8, 2), pady=2)

        ttk.Button(frame_botoes, text="▼ Y-", width=6, command=lambda: self.mover("SUL", 0, -1, 0), takefocus=False).grid(row=2, column=1, padx=2, pady=2)

        self.lbl_jog = ttk.Label(lateral, text="Jog: X 0.0  Y 0.0  Z 0.0", wraplength=245, justify=tk.LEFT)
        self.lbl_jog.pack(anchor="w", pady=4)

        self.barra_progresso = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.barra_progresso.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))

    def _devolver_foco(self, evento):
        if isinstance(evento.widget, (tk.Entry, ttk.Entry, ttk.Spinbox)):
            return
        self.canvas.focus_set()

    def _area(self):
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        margem = CANVAS_MARGIN
        escala = min((w - 2 * margem) / MAX_X, (h - 2 * margem) / MAX_Y)
        return (w - MAX_X * escala) / 2, (h - MAX_Y * escala) / 2, escala

    def _xy_canvas(self, x, y):
        x0, y0, escala = self._area()
        return x0 + x * escala, y0 + (MAX_Y - y) * escala

    def _desenhar_grade(self):
        self.canvas.delete("grade")
        x0, y0, escala = self._area()
        x1, y1 = x0 + MAX_X * escala, y0 + MAX_Y * escala

        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#8fa3b8", width=2, tags="grade")
        for x in range(0, int(MAX_X) + 1, 10):
            px, _ = self._xy_canvas(x, 0)
            self.canvas.create_line(px, y0, px, y1, fill="#263746", tags="grade")
        for y in range(0, int(MAX_Y) + 1, 10):
            _, py = self._xy_canvas(0, y)
            self.canvas.create_line(x0, py, x1, py, fill="#263746", tags="grade")

    def _redesenhar_tudo(self, event=None):
        self.canvas.delete("all")
        self._desenhar_grade()
        self._desenhar_trajetoria()
        jx, jy = self._xy_canvas(self.jog_x, self.jog_y)
        self.canvas.create_rectangle(jx - 5, jy - 5, jx + 5, jy + 5, outline="#4cc9f0", width=2, tags="jog")

    def _desenhar_trajetoria(self):
        for cmd in self.comandos[:self.indice]:
            x0, y0 = self._xy_canvas(cmd["x0"], cmd["y0"])
            x1, y1 = self._xy_canvas(cmd["x1"], cmd["y1"])
            cor = "#42d392" if cmd["desenho"] else "#f0b45a"
            self.canvas.create_line(x0, y0, x1, y1, fill=cor, width=2, tags="trajetoria")

    def abrir_arquivo(self):
        self.pausar()
        caminho = filedialog.askopenfilename(title="Selecione o G-code", filetypes=[("G-code", "*.gcode *.nc"), ("Todos", "*.*")])
        if not caminho: return
        try:
            self.comandos = ler_gcode(caminho)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self.caminho = caminho
        self.indice = 0
        self.lbl_arquivo.config(text=Path(caminho).name)
        self._redesenhar_tudo()

    def _atualizar_status(self):
        if self.comandos:
            self.barra_progresso["value"] = 100 * self.indice / len(self.comandos)

    def iniciar(self):
        if not self.comandos: return
        self.executando = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_pausar.config(state=tk.NORMAL)
        self._passo_animacao()

    def _passo_animacao(self):
        if not self.executando: return
        if self.indice >= len(self.comandos):
            self.pausar()
            return

        cmd = self.comandos[self.indice]
        if self.serial and self.serial.is_open:
            try:
                self.serial.write((cmd["gcode_raw"] + "\n").encode("ascii"))
            except Exception:
                pass

        self.indice += 1
        self._redesenhar_tudo()
        self._atualizar_status()
        
        delay = max(5, int(200 / max(1, self.velocidade.get())))
        self.after_id = self.root.after(delay, self._passo_animacao)

    def pausar(self):
        self.executando = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_pausar.config(state=tk.DISABLED)

    def proximo(self):
        self.pausar()
        if self.indice < len(self.comandos):
            cmd = self.comandos[self.indice]
            if self.serial and self.serial.is_open:
                try: self.serial.write((cmd["gcode_raw"] + "\n").encode("ascii"))
                except: pass
            self.indice += 1
            self._redesenhar_tudo()

    def reiniciar(self):
        self.pausar()
        self.indice = 0
        self._redesenhar_tudo()

    def alternar_conexao(self):
        if self.serial:
            self._desconectar()
            return
        if serial is None:
            messagebox.showerror("Erro", "Instale o pyserial: pip install pyserial")
            return
        try:
            self.serial = serial.Serial(self.porta.get().strip(), BAUDRATE, timeout=0.1)
            time.sleep(2)
            self.serial.reset_input_buffer()
            self.btn_conectar.config(text="Desconectar")
            self.lbl_estado.config(text="Conectado com sucesso!")
        except Exception as e:
            self.serial = None
            messagebox.showerror("Erro de Conexão", str(e))

    def _desconectar(self):
        if self.serial:
            try: self.serial.close()
            except: pass
        self.serial = None
        self.btn_conectar.config(text="Conectar")
        self.lbl_estado.config(text="Desconectado")

    def _fechar(self):
        self._desconectar()
        self.root.destroy()

    def enviar_direto(self, cmd):
        if not self.serial:
            messagebox.showwarning("Aviso", "Conecte à porta serial primeiro!")
            return
        try:
            self.serial.write((cmd + "\n").encode("ascii"))
            time.sleep(0.1)
            resposta = self.serial.read_all().decode(errors="replace")
            self.lbl_estado.config(text=f"Resp: {resposta.strip() or 'OK'}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _tecla_direcao(self, evento):
        if evento.keysym in DIRECOES:
            nome, dx, dy, dz = DIRECOES[evento.keysym]
            self.mover(nome, dx, dy, dz)
        return "break"

    def mover(self, nome, dx, dy, dz):
        agora = time.monotonic()
        if agora - self.ultimo_jog < INTERVALO_MIN_JOG:
            return
        self.ultimo_jog = agora

        try:
            passo = float(self.passo_jog.get())
        except:
            return

        novo_x = self.jog_x + dx * passo
        novo_y = self.jog_y + dy * passo
        novo_z = self.jog_z + dz * passo

        eixos = []
        if dx != 0: eixos.append(f"X{dx * passo:.3f}")
        if dy != 0: eixos.append(f"Y{dy * passo:.3f}")
        if dz != 0: eixos.append(f"Z{dz * passo:.3f}")

        if not eixos: return

        comando = f"G91 G1 {' '.join(eixos)} F{FEED_JOG}"

        if self.serial:
            try:
                self.serial.write((comando + "\nG90\n").encode("ascii"))
                time.sleep(0.02)
                resp = self.serial.read_all().decode(errors="replace").strip()
                if "error" in resp or "ALARM" in resp:
                    self.lbl_estado.config(text=f"GRBL Rejeitou: {resp}")
                    return
            except Exception as e:
                messagebox.showerror("Erro Serial", str(e))
                self._desconectar()
                return

        self.jog_x, self.jog_y, self.jog_z = novo_x, novo_y, novo_z
        self.lbl_posicao.config(text=f"X: {self.jog_x:.3f} | Y: {self.jog_y:.3f} | Z: {self.jog_z:.3f}")
        self.lbl_jog.config(text=f"Enviado: {comando}")
        self._redesenhar_tudo()

    # FUNÇÃO DE RESETE COMPLETO DA POSIÇÃO ATUAL
    def resete_completo(self):
        # 1. Zera as variáveis de rastreio interno do simulador na posição atual
        self.jog_x = 0.0
        self.jog_y = 0.0
        self.jog_z = Z_UP
        
        # 2. Se houver conexão serial, envia o comando G92 para definir a posição física atual como zero no GRBL
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(b"G92 X0 Y0 Z0\n")
                time.sleep(0.05)
                self.serial.read_all()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao enviar resete para a CNC: {e}")

        # 3. Reseta o índice de simulação / progresso do G-code se necessário
        self.indice = 0
        self.barra_progresso["value"] = 0

        # 4. Atualiza os textos da interface e limpa a tela de traços antigos
        self.lbl_posicao.config(text=f"X: {self.jog_x:.3f} | Y: {self.jog_y:.3f} | Z: {self.jog_z:.3f}")
        self.lbl_jog.config(text="Resete geral aplicado (0,0,0 na posição atual)")
        self._redesenhar_tudo()


def main():
    root = tk.Tk()
    SimuladorCNC(root)
    root.mainloop()

if __name__ == "__main__":
    main()