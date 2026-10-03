import threading

PARADO = "parado"
CAPTURANDO = "capturando"
DESENHANDO = "desenhando"
PENSANDO = "pensando"
FALANDO = "falando"
PAUSADO = "pausado"

MODO_LIVRE = "livre"
MODO_DESAFIO = "desafio"


class State:

    def __init__(self):
        self._lock = threading.Lock()
        self._estado = PARADO
        self.objeto = None
        self._listeners = []

        # Estado do jogo e cronômetro
        self.modo = MODO_LIVRE
        self.palavra_sorteada = None
        self.desafio_em_andamento = False
        self.tempo_restante = 0
        self.aguardando_posicionamento = False  # NOVO: Aguarda colocar na câmera

    @property
    def estado(self) -> str:
        return self._estado

    def set(self, novo: str):
        with self._lock:
            if novo == self._estado:
                return
            self._estado = novo
        for fn in list(self._listeners):
            try:
                fn(novo)
            except Exception as e:
                print(f"[State] erro em listener: {e}")

    def set_tempo_restante(self, tempo: int):
        with self._lock:
            self.tempo_restante = tempo

    def subscribe(self, fn):
        self._listeners.append(fn)

    def reset_desenho(self):
        with self._lock:
            self.objeto = None
            self.palavra_sorteada = None
            self.desafio_em_andamento = False
            self.tempo_restante = 0
            self.aguardando_posicionamento = False