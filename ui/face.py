import ctypes
import random
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame
from server.state import FALANDO, MODO_DESAFIO, PARADO, PAUSADO, PENSANDO, State

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

DURACAO_PISCADA_MS = 210
INTERVALO_PISCADA = (3.0, 6.0)
INTERVALO_BOCA_MS = (120, 220)  # troca da boca aberta/fechada enquanto fala

# Expressão de cada estado do State. Estados sem entrada usam a neutra.
EXPRESSAO_DO_ESTADO = {
    PARADO: "neutro",
    PENSANDO: "pensando",
    FALANDO: "falando",
    PAUSADO: "pausado",
}


class Face:
    def __init__(self, state: State = None, display_index=1, titulo="Desenha AI - Rosto"):
        self.state = state

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(titulo)

        num_monitores = pygame.display.get_num_displays()
        if display_index >= num_monitores:
            display_index = 0

        tamanhos = pygame.display.get_desktop_sizes()
        self.tamanho = tamanhos[display_index]

        self.tela = pygame.display.set_mode(
            self.tamanho, pygame.NOFRAME, display=display_index
        )

        self.relogio = pygame.time.Clock()

        self.fonte_timer = pygame.font.SysFont("Arial", 56, bold=True)
        self.fonte_desafio = pygame.font.SysFont("Arial", 32, bold=True)
        self.fonte_alerta = pygame.font.SysFont("Arial", 36, bold=True)

        self._originais = {
            nome: pygame.image.load(ASSETS_DIR / f"rosto_{nome}.png").convert_alpha()
            for nome in ("neutro", "piscando", "falando", "pausado", "pensando")
        }
        self._imagens = {}
        self._posicao = (0, 0)
        self._escalar_imagens()

        self._quadro_atual = "neutro"
        self._piscando = False
        self._tempo_piscada = 0
        self._proxima_piscada = self._sortear_intervalo()
        self._boca_aberta = True
        self._proxima_troca_boca = 0
        self._rodando = True

    def parar(self):
        self._rodando = False

    def run(self):
        while self._rodando:
            dt = self.relogio.tick(30)
            self._tratar_eventos()
            self._atualizar_quadro(dt)
            self._desenhar()
        pygame.quit()

    def _tratar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._rodando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self._rodando = False

    def _escalar_imagens(self):
        # As imagens são 16:9 e o display do HDMI não é: escala mantendo a
        # proporção e centraliza. O fundo das imagens já é preto.
        largura, altura = self.tamanho
        img_l, img_a = next(iter(self._originais.values())).get_size()
        escala = min(largura / img_l, altura / img_a)
        tamanho_img = (round(img_l * escala), round(img_a * escala))
        self._posicao = ((largura - tamanho_img[0]) // 2, (altura - tamanho_img[1]) // 2)
        self._imagens = {
            nome: pygame.transform.smoothscale(img, tamanho_img)
            for nome, img in self._originais.items()
        }

    def _sortear_intervalo(self):
        return random.uniform(*INTERVALO_PISCADA) * 1000

    def _atualizar_quadro(self, dt):
        estado = self.state.estado if self.state else PARADO
        expressao = EXPRESSAO_DO_ESTADO.get(estado, "neutro")

        if expressao == "neutro":
            self._quadro_atual = self._atualizar_piscada(dt)
        elif expressao == "falando":
            self._quadro_atual = self._atualizar_boca(dt)
        else:
            self._quadro_atual = expressao

        # Fora do neutro não pisca: a imagem da piscada tem a boca do neutro.
        if expressao != "neutro":
            self._piscando = False

    def _atualizar_piscada(self, dt):
        if not self._piscando:
            self._proxima_piscada -= dt
            if self._proxima_piscada <= 0:
                self._piscando = True
                self._tempo_piscada = 0
        else:
            self._tempo_piscada += dt
            if self._tempo_piscada >= DURACAO_PISCADA_MS:
                self._piscando = False
                self._proxima_piscada = self._sortear_intervalo()
        return "piscando" if self._piscando else "neutro"

    def _atualizar_boca(self, dt):
        self._proxima_troca_boca -= dt
        if self._proxima_troca_boca <= 0:
            self._boca_aberta = not self._boca_aberta
            self._proxima_troca_boca = random.uniform(*INTERVALO_BOCA_MS)
        return "falando" if self._boca_aberta else "neutro"

    def _desenhar(self):
        self.tela.fill((0, 0, 0))
        self.tela.blit(self._imagens[self._quadro_atual], self._posicao)

        self._desenhar_overlay_desafio()

        pygame.display.flip()

    def _desenhar_overlay_desafio(self):
        if not self.state:
            return

        largura_tela, _ = self.tamanho

        # 1. MODO DESAFIO COM O TEMPO ROLANDO
        if self.state.modo == MODO_DESAFIO and self.state.desafio_em_andamento:
            tempo = self.state.tempo_restante
            palavra = self.state.palavra_sorteada or ""

            overlay_surface = pygame.Surface((largura_tela, 140), pygame.SRCALPHA)
            overlay_surface.fill((10, 20, 45, 210))
            self.tela.blit(overlay_surface, (0, 0))

            cor_tempo = (255, 60, 60) if tempo <= 5 else (0, 220, 255)
            pygame.draw.line(self.tela, cor_tempo, (0, 140), (largura_tela, 140), width=4)

            # Cronômetro Ex: 00:25
            txt_tempo = self.fonte_timer.render(f"00:{tempo:02d}", True, cor_tempo)
            rect_tempo = txt_tempo.get_rect(center=(largura_tela // 2, 45))
            self.tela.blit(txt_tempo, rect_tempo)

            # Instrução Ex: DESENHE: CASA
            txt_palavra = self.fonte_desafio.render(
                f"DESENHE UM(A): {palavra.upper()}", True, (255, 255, 255)
            )
            rect_palavra = txt_palavra.get_rect(center=(largura_tela // 2, 105))
            self.tela.blit(txt_palavra, rect_palavra)

        # 2. TEMPO ACABOU: AVISO PARA COLOCAR O PAPEL NA CÂMERA
        elif self.state.aguardando_posicionamento:
            overlay_surface = pygame.Surface((largura_tela, 120), pygame.SRCALPHA)
            overlay_surface.fill((180, 40, 40, 220))
            self.tela.blit(overlay_surface, (0, 0))

            txt_alerta = self.fonte_alerta.render(
                "COLOQUE O PAPEL DEBAIXO DA CÂMERA E AVISE!", True, (255, 255, 255)
            )
            rect_alerta = txt_alerta.get_rect(center=(largura_tela // 2, 60))
            self.tela.blit(txt_alerta, rect_alerta)


if __name__ == "__main__":
    face = Face(display_index=1)
    face.run()