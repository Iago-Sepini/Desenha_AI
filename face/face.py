import ctypes
import random
from pathlib import Path

# Remove distorções de DPI do Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

DURACAO_PISCADA_MS = 210
INTERVALO_PISCADA = (3.0, 6.0)


class Face:
    def __init__(self, display_index=1, titulo="Desenha AI - Rosto"):
        pygame.init()
        pygame.display.set_caption(titulo)

        num_monitores = pygame.display.get_num_displays()

        # Se o monitor secundário não for encontrado, usa o principal (0)
        if display_index >= num_monitores:
            display_index = 0

        # Pega o tamanho real do monitor selecionado
        tamanhos = pygame.display.get_desktop_sizes()
        self.tamanho = tamanhos[display_index]

        # CRUCIAL: Criamos a janela informando o monitor de destino diretamente no Pygame
        self.tela = pygame.display.set_mode(
            self.tamanho, pygame.NOFRAME, display=display_index
        )

        self.relogio = pygame.time.Clock()

        self._originais = {
            "abertos": pygame.image.load(
                ASSETS_DIR / "olhos_abertos.png"
            ).convert_alpha(),
            "fechados": pygame.image.load(
                ASSETS_DIR / "olhos_fechados.png"
            ).convert_alpha(),
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
        while self._rodando:
            dt = self.relogio.tick(30)
            self._tratar_eventos()
            self._atualizar_piscada(dt)
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
        self._imagens = {
            nome: pygame.transform.smoothscale(img, self.tamanho)
            for nome, img in self._originais.items()
        }

    def _sortear_intervalo(self):
        return random.uniform(*INTERVALO_PISCADA) * 1000

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


if __name__ == "__main__":
    # display_index=1 faz o Pygame abrir a janela DIRETAMENTE no 2º monitor.
    # Se a janela abrir no notebook, mude display_index para 0.
    face = Face(display_index=1)
    face.run()