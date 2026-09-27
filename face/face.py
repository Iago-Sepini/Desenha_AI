import random
from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

DURACAO_PISCADA_MS = 150        # quanto tempo fica com os olhos fechados
INTERVALO_PISCADA = (3.0, 6.0)  # segundos entre piscadas, sorteado


class Face:
    """Janela com o rosto do robô. Roda na thread principal (pygame exige isso).

    Arraste a janela para a tela do HDMI e aperte F11 para tela cheia nela.
    ESC sai da tela cheia; feche a janela ou aperte ESC de novo para encerrar.
    """

    def __init__(self, largura=480, altura=480, titulo="Desenha AI - Rosto"):
        pygame.init()
        pygame.display.set_caption(titulo)
        self.tamanho = (largura, altura)
        self.tela = pygame.display.set_mode(self.tamanho, pygame.RESIZABLE)
        self.relogio = pygame.time.Clock()
        self.cheia = False

        self._originais = {
            "abertos": pygame.image.load(ASSETS_DIR / "olhos_abertos.png").convert_alpha(),
            "fechados": pygame.image.load(ASSETS_DIR / "olhos_fechados.png").convert_alpha(),
        }
        self._imagens = {}
        self._escalar_imagens()

        self._quadro_atual = "abertos"
        self._piscando = False
        self._tempo_piscada = 0
        self._proxima_piscada = self._sortear_intervalo()
        self._rodando = True

    def parar(self):
        self._rodando = False

    def run(self):
        """Loop principal. Bloqueia até a janela ser fechada ou parar() ser chamado."""
        while self._rodando:
            dt = self.relogio.tick(30)  # 30 quadros por segundo
            self._tratar_eventos()
            self._atualizar_piscada(dt)
            self._desenhar()
        pygame.quit()

    # ---------- internos ----------
    def _tratar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._rodando = False
            elif evento.type == pygame.VIDEORESIZE and not self.cheia:
                self.tamanho = (evento.w, evento.h)
                self._escalar_imagens()
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_F11:
                    self._alternar_tela_cheia()
                elif evento.key == pygame.K_ESCAPE:
                    if self.cheia:
                        self._alternar_tela_cheia()
                    else:
                        self._rodando = False

    def _alternar_tela_cheia(self):
        pygame.display.toggle_fullscreen()
        self.cheia = not self.cheia
        self.tamanho = self.tela.get_size()
        self._escalar_imagens()

    def _escalar_imagens(self):
        self._imagens = {
            nome: pygame.transform.smoothscale(img, self.tamanho)
            for nome, img in self._originais.items()
        }

    def _sortear_intervalo(self):
        return random.uniform(*INTERVALO_PISCADA) * 1000  # em ms

    def _atualizar_piscada(self, dt):
        if not self._piscando:
            self._proxima_piscada -= dt
            if self._proxima_piscada <= 0:
                self._piscando = True
                self._quadro_atual = "fechados"
                self._tempo_piscada = 0
            return

        self._tempo_piscada += dt
        if self._tempo_piscada >= DURACAO_PISCADA_MS:
            self._piscando = False
            self._quadro_atual = "abertos"
            self._proxima_piscada = self._sortear_intervalo()

    def _desenhar(self):
        self.tela.fill((0, 0, 0))
        self.tela.blit(self._imagens[self._quadro_atual], (0, 0))
        pygame.display.flip()