import threading

PARADO = "parado"
CAPTURANDO = "capturando"
DESENHANDO = "desenhando"
PENSANDO = "pensando"
FALANDO = "falando"
PAUSADO = "pausado"


class State:

    def __init__(self):
        self._lock = threading.Lock()
        self._estado = PARADO
        self.objeto = None
        self._listeners = []

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

    def subscribe(self, fn):
        """fn(estado) é chamada a cada mudança."""
        self._listeners.append(fn)