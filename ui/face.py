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

try:
    from comtypes import CLSCTX_ALL, CoCreateInstance
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.pycaw import IAudioMeterInformation, IMMDeviceEnumerator
    PYCAW_OK = True
except Exception:
    PYCAW_OK = False

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

DURACAO_PISCADA_MS = 180
INTERVALO_PISCADA = (3.0, 6.0)
INTERVALO_BOCA_MS = (120, 220)  # troca da boca aberta/fechada enquanto fala

# Detecção de som saindo do PC
LIMIAR_SOM = 0.01        # pico (0.0 a 1.0) acima do qual considera que há som
TOLERANCIA_SILENCIO_MS = 350  # mantém a boca mexendo nas pausas curtas da fala

# Texto do modo desafio (com contagem rolando) fica 20% menor
ESCALA_TEXTO_DESAFIO = 0.8

# Expressão de cada estado do State. Estados sem entrada usam a neutra.
EXPRESSAO_DO_ESTADO = {
    PARADO: "neutro",
    PENSANDO: "pensando",
    FALANDO: "falando",
    PAUSADO: "pausado",
}


class MedidorDeSom:
    """Lê o pico de áudio do dispositivo de saída padrão do Windows."""

    def __init__(self):
        self._medidor = None
        if not PYCAW_OK:
            return
        try:
            enumerador = CoCreateInstance(
                CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL
            )
            dispositivo = enumerador.GetDefaultAudioEndpoint(0, 1)  # render, multimedia
            interface = dispositivo.Activate(
                IAudioMeterInformation._iid_, CLSCTX_ALL, None
            )
            self._medidor = interface.QueryInterface(IAudioMeterInformation)
        except Exception as e:
            print(f"[Face] Não foi possível iniciar o medidor de som: {e}")
            self._medidor = None

    @property
    def disponivel(self):
        return self._medidor is not None

    def pico(self):
        try:
            return self._medidor.GetPeakValue()
        except Exception:
            return 0.0


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

        e = ESCALA_TEXTO_DESAFIO
        self.fonte_timer = pygame.font.SysFont("Arial", round(56 * e), bold=True)
        self.fonte_desafio = pygame.font.SysFont("Arial", round(32 * e), bold=True)
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

        self._medidor = MedidorDeSom()
        self._silencio_ms = TOLERANCIA_SILENCIO_MS  # começa em silêncio

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

    def _som_tocando(self, dt):
        # Sem o pycaw, cai no comportamento antigo (só segue o estado).
        if not self._medidor.disponivel:
            return True
        if self._medidor.pico() > LIMIAR_SOM:
            self._silencio_ms = 0
        else:
            self._silencio_ms += dt
        return self._silencio_ms < TOLERANCIA_SILENCIO_MS

    def _atualizar_quadro(self, dt):
        estado = self.state.estado if self.state else PARADO
        expressao = EXPRESSAO_DO_ESTADO.get(estado, "neutro")

        if expressao == "neutro":
            self._quadro_atual = self._atualizar_piscada(dt)
        elif expressao == "falando":
            if self._som_tocando(dt):
                self._quadro_atual = self._atualizar_boca(dt)
            else:
                # Estado "falando" mas ainda sem som: rosto parado, boca fechada.
                self._boca_aberta = True
                self._proxima_troca_boca = 0
                self._quadro_atual = "neutro"
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

        # 1. MODO DESAFIO COM O TEMPO ROLANDO (texto e faixa 20% menores)
        if self.state.modo == MODO_DESAFIO and self.state.desafio_em_andamento:
            tempo = self.state.tempo_restante
            palavra = self.state.palavra_sorteada or ""

            e = ESCALA_TEXTO_DESAFIO
            altura_faixa = round(140 * e)

            overlay_surface = pygame.Surface((largura_tela, altura_faixa), pygame.SRCALPHA)
            overlay_surface.fill((10, 20, 45, 210))
            self.tela.blit(overlay_surface, (0, 0))

            cor_tempo = (255, 60, 60) if tempo <= 5 else (0, 220, 255)
            pygame.draw.line(
                self.tela, cor_tempo, (0, altura_faixa), (largura_tela, altura_faixa), width=4
            )

            # Cronômetro Ex: 00:25
            txt_tempo = self.fonte_timer.render(f"00:{tempo:02d}", True, cor_tempo)
            rect_tempo = txt_tempo.get_rect(center=(largura_tela // 2, round(45 * e)))
            self.tela.blit(txt_tempo, rect_tempo)

            # Instrução Ex: DESENHE: CASA
            txt_palavra = self.fonte_desafio.render(
                f"DESENHE UM(A): {palavra.upper()}", True, (255, 255, 255)
            )
            rect_palavra = txt_palavra.get_rect(center=(largura_tela // 2, round(105 * e)))
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