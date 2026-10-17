import threading
import time

import cv2
import numpy as np

from vision.config_camera import abrir_camera, ler_frame, proximo_modo, recortar_quadrado
from vision.detector import Detector, sem_acento, texto_contorno, visao_pb

class DrawingWatcher:
    """Roda a câmera e o Detector continuamente, mostrando uma janela com o
    que está sendo reconhecido no momento. NÃO avisa o Max sozinho: quem
    decide a hora certa é quem chama confirmar().

    A janela segue a "visao" do camera_config.json: "normal", "pb" (preto e
    branco: branco = o que vira SVG) ou "ambos". Na janela, a tecla B alterna."""

    def __init__(self, on_desenho, modelo="model.h5", classes="classes.json", mostrar_janela=True):
        self.on_desenho = on_desenho
        self.detector = Detector(modelo, classes)
        self.mostrar_janela = mostrar_janela
        self._rodando = False
        self._thread = None

        # Atualizados continuamente; "congelam" no último desenho válido
        # quando a mão passa na frente ou o papel sai por um instante.
        self.ultimo_roi = None
        self.ultimos_contornos = None
        self.nome_atual = None
        self.confianca_atual = 0.0

    def start(self):
        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._rodando = False
        if self._thread:
            self._thread.join(timeout=2)

    def confirmar(self) -> bool:
        """Chamer quando o visitante disser que terminou de desenhar.
        Manda para o Max o que estiver reconhecido agora. Retorna False
        se não havia nada reconhecido ainda."""
        if self.nome_atual:
            self.on_desenho(self.nome_atual)
            return True
        return False

    def _loop(self):
        cap, cfg = abrir_camera()
        try:
            while self._rodando:
                frame = ler_frame(cap, cfg)
                if frame is None:
                    time.sleep(0.1)
                    continue

                roi, caixa = recortar_quadrado(frame, cfg)
                r = self.detector.detectar(roi)

                if r.tem_desenho:
                    self.ultimo_roi = roi.copy()
                    self.ultimos_contornos = r.contornos
                self.nome_atual = r.estavel
                self.confianca_atual = r.confianca if r.estavel else 0.0

                if self.mostrar_janela:
                    self._desenhar_janela(frame, r, caixa, cfg)

                time.sleep(0.03)
        finally:
            cap.release()
            if self.mostrar_janela:
                cv2.destroyAllWindows()

    # ---------- janela ----------
    def _texto_deteccao(self):
        if self.nome_atual:
            texto = f"Detectando: {sem_acento(self.nome_atual)} {self.confianca_atual * 100:.0f}%"
            return texto, (0, 255, 0)
        return "Detectando: ...", (0, 200, 255)

    def _vista_normal(self, frame, caixa):
        """A janela de sempre: câmera + quadrado verde + texto."""
        x0, y0, lado = caixa
        cv2.rectangle(frame, (x0, y0), (x0 + lado, y0 + lado), (0, 255, 0), 2)
        texto, cor = self._texto_deteccao()
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)
        return frame

    def _vista_pb(self, frame, r, caixa):
        """Preto e branco: BRANCO = o que a visão enxerga como traço (vira SVG)."""
        vista = visao_pb(frame, r, caixa)
        texto, cor = self._texto_deteccao()
        texto_contorno(vista, texto, (10, 58), 0.8, cor)   # abaixo da legenda "BRANCO = vira SVG"
        return vista

    def _desenhar_janela(self, frame, r, caixa, cfg):
        modo = cfg.get("visao", "normal")
        if modo == "pb":
            vista = self._vista_pb(frame, r, caixa)
        elif modo == "ambos":
            vista = np.hstack([self._vista_normal(frame.copy(), caixa),
                               self._vista_pb(frame, r, caixa)])
        else:
            vista = self._vista_normal(frame, caixa)

        cv2.imshow("Camera - Desenha AI", vista)
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("b"):                     # alterna normal -> pb -> ambos
            cfg["visao"] = proximo_modo(modo)