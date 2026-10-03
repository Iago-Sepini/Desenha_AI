import random
import threading
import time
import winsound

from ai.prompts import (
    EVENTO_NAO_IDENTIFICADO,
    montar_pedido,
    montar_pedido_desafio,
)
from server.state import FALANDO, MODO_DESAFIO, MODO_LIVRE, PENSANDO, State
from vision.svg_export import gerar_svg

PALAVRAS_DESAFIO = ["casa", "árvore", "carro", "sol", "estrela", "gato", "coração", "peixe", "flor"]


class GameManager:

    def __init__(self, state: State, watcher, llm, conversar_fn, speaker=None):
        self.state = state
        self.watcher = watcher
        self.llm = llm
        self.conversar = conversar_fn
        self.speaker = speaker
        self.thread_timer = None
        self._rodando_timer = False

    def ativar_modo_livre(self):
        self.parar_timer()
        self.state.modo = MODO_LIVRE
        self.limpar_estado()
        print("[GameManager] Modo Livre ativado")
        self.conversar("Modo livre ativado! Desenhe o que quiser no seu tempo.")

    def iniciar_desafio(self):
        self.parar_timer()
        self.state.modo = MODO_DESAFIO
        self.state.palavra_sorteada = random.choice(PALAVRAS_DESAFIO)
        self.state.desafio_em_andamento = False  # Timer ainda pausado
        self.state.aguardando_posicionamento = False
        self.state.set_tempo_restante(30)

        print(f"\n[Desafio] Sorteado: {self.state.palavra_sorteada}")

        msg_inicio = (
            f"Modo Desafio ativado! Seu objetivo é desenhar um(a) {self.state.palavra_sorteada}. "
            f"Você tem 30 segundos para desenhar na folha aí na mesa. Valendo!"
        )

        # 1. Envia a mensagem para a LLM e TTS
        self.conversar(msg_inicio)

        # 2. Aguarda a LLM gerar e o alto-falante terminar a fala por completo
        time.sleep(0.5)
        while self.state.estado in (PENSANDO, FALANDO):
            time.sleep(0.1)

        if self.speaker:
            self.speaker.wait()

        # 3. Inicia a contagem regressiva e os 30 segundos na tela APENAS AGORA
        self.state.desafio_em_andamento = True
        self._rodando_timer = True
        self.thread_timer = threading.Thread(target=self._loop_cronometro, daemon=True)
        self.thread_timer.start()

    def _loop_cronometro(self):
        tempo = 30
        while tempo > 0 and self._rodando_timer and self.state.desafio_em_andamento:
            time.sleep(1)
            tempo -= 1
            self.state.set_tempo_restante(tempo)

        if self._rodando_timer and self.state.desafio_em_andamento:
            self.state.desafio_em_andamento = False

            try:
                winsound.Beep(1000, 300)
                winsound.Beep(1200, 400)
            except Exception:
                pass

            self.state.aguardando_posicionamento = True
            print("\n[Desafio] Tempo esgotado! Aguardando posicionamento da folha...")

            self.conversar(
                "O tempo acabou! Agora coloque o seu papel embaixo da câmera e me avise quando estiver pronto!"
            )

    def confirmar_e_analisar(self, responder_fn):
        if not self.state.aguardando_posicionamento and self.state.modo != MODO_DESAFIO:
            return

        self.state.aguardando_posicionamento = False
        print("[Desafio] Capturando imagem após confirmação...")

        if not self.watcher.confirmar():
            self.conversar(EVENTO_NAO_IDENTIFICADO)

    def processar_desenho(self, objeto: str, responder_fn):
        self.parar_timer()
        self.state.objeto = objeto

        if hasattr(self.watcher, "ultimos_contornos") and self.watcher.ultimos_contornos:
            lado = self.watcher.ultimo_roi.shape[0]
            caminho = gerar_svg(self.watcher.ultimos_contornos, lado)
            print(f"[CNC] SVG gerado com sucesso: {caminho}")
            self.watcher.ultimos_contornos = None

        if self.state.modo == MODO_DESAFIO:
            palavra = self.state.palavra_sorteada
            acertou = objeto.lower().strip() == palavra.lower().strip() if palavra else False

            def gerar_resposta_desafio():
                prompt = montar_pedido_desafio(objeto, palavra, acertou)
                texto, _ = self.llm.chat(prompt)
                return texto, None

            responder_fn(gerar_resposta_desafio)

        else:
            def gerar_pergunta():
                prompt = montar_pedido(objeto)
                texto, _ = self.llm.chat(prompt)
                return texto, None

            responder_fn(gerar_pergunta)

    def limpar_estado(self):
        self.parar_timer()
        self.state.reset_desenho()
        if hasattr(self.watcher, "ultimos_contornos"):
            self.watcher.ultimos_contornos = None
        if hasattr(self.watcher, "detector"):
            self.watcher.detector.reset()

    def parar_timer(self):
        self._rodando_timer = False
        self.state.set_tempo_restante(0)

    def cancelar_timer(self):
        self.parar_timer()