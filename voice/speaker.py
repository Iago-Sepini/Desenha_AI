import threading
import time
from concurrent.futures import CancelledError, ThreadPoolExecutor

import sounddevice as sd

from voice.text_utils import split_sentences


class Speaker:
    """Fala um texto frase por frase e permite pausar, continuar e cancelar.

    on_state(estado) recebe: "falando", "pausado" ou "parado".
    Serve para o rosto e para o state.py acompanharem a fala.
    """

    def __init__(self, engine, on_state=None):
        self.engine = engine  # qualquer objeto com .synthesize(texto) e .sample_rate
        self.on_state = on_state
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._sentences = []
        self._futures = {}
        self._index = 0
        self._paused = threading.Event()
        self._cancel = threading.Event()
        self._thread = None

    # ---------- API pública ----------
    def say(self, text: str):
        self.cancel()
        self._sentences = split_sentences(text)
        if not self._sentences:
            return
        # gera o áudio de todas as frases adiantado, em segundo plano
        self._futures = {
            i: self._pool.submit(self.engine.synthesize, s)
            for i, s in enumerate(self._sentences)
        }
        self._index = 0
        self._paused.clear()
        self._cancel.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        """Comando 'parar': interrompe agora. A frase interrompida será repetida ao continuar."""
        if self.is_speaking and not self._paused.is_set():
            self._paused.set()
            sd.stop()
            self._emit("pausado")

    def resume(self):
        """Comando 'continuar'."""
        if self._paused.is_set():
            self._paused.clear()
            self._emit("falando")

    def cancel(self):
        self._cancel.set()
        self._paused.clear()
        for f in self._futures.values():
            f.cancel()
        sd.stop()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2)

    def wait(self):
        if self._thread:
            self._thread.join()

    @property
    def is_speaking(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ---------- internos ----------
    def _run(self):
        self._emit("falando")
        try:
            while self._index < len(self._sentences) and not self._cancel.is_set():
                if self._paused.is_set():
                    time.sleep(0.05)
                    continue
                try:
                    audio = self._futures[self._index].result()
                except CancelledError:
                    break
                if self._paused.is_set() or self._cancel.is_set():
                    continue
                if self._play(audio):
                    self._index += 1
        except Exception as e:
            print(f"[Speaker] erro: {e}")
        finally:
            self._emit("parado")

    def _play(self, audio) -> bool:
        """Retorna True se a frase terminou, False se foi interrompida."""
        sr = self.engine.sample_rate
        sd.play(audio, sr)
        end = time.monotonic() + len(audio) / sr
        while time.monotonic() < end:
            if self._paused.is_set() or self._cancel.is_set():
                sd.stop()
                return False
            time.sleep(0.02)
        sd.wait()
        return True

    def _emit(self, state):
        if self.on_state:
            try:
                self.on_state(state)
            except Exception as e:
                print(f"[Speaker] erro no callback: {e}")