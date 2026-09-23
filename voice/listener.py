import json
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from pynput import keyboard


class Listener:
    """Escuta o microfone apenas enquanto a barra de espaço estiver premida (Push-to-Talk)."""

    def __init__(self, on_text=None, lang="pt", target_sr=16000):
        self.on_text = on_text
        self.target_sr = target_sr
        self.lang = lang
        self._recording = False
        self._audio_data = bytearray()
        self._listener_keyboard = None
        self._model = None
        self._stream = None
        
        # Deteta a taxa de amostragem nativa da placa de som/microfone
        try:
            device_info = sd.query_devices(kind='input')
            self.native_sr = int(device_info['default_samplerate'])
        except Exception:
            self.native_sr = 44100  # Taxa padrão de segurança caso não detete

    def start(self):
        """Inicializa o modelo de voz e ativa a monitorização do teclado."""
        try:
            self._model = Model(lang=self.lang)
        except Exception as e:
            print(f"[Listener] Erro ao carregar o modelo de voz Vosk: {e}")
            return

        print(f"[Listener] Push-to-Talk ativado (Taxa nativa: {self.native_sr}Hz -> {self.target_sr}Hz).")
        print("[Listener] Mantenha a BARRA DE ESPAÇO premida para falar.")

        self._listener_keyboard = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener_keyboard.start()

    def stop(self):
        """Para a monitorização do teclado."""
        if self._listener_keyboard:
            self._listener_keyboard.stop()

    def _on_press(self, key):
        if key == keyboard.Key.space and not self._recording:
            self._recording = True
            self._audio_data = bytearray()
            
            print("\n[Microfone] 🎙️ A escutar... (fale agora e solte a barra no final)")
            
            try:
                # Grava com a taxa de amostragem nativa para evitar distorções
                self._stream = sd.RawInputStream(
                    samplerate=self.native_sr,
                    blocksize=4000,
                    dtype="int16",
                    channels=1,
                    callback=self._audio_callback
                )
                self._stream.start()
            except Exception as e:
                print(f"[Microfone] Erro ao abrir o microfone: {e}")
                self._recording = False

    def _on_release(self, key):
        if key == keyboard.Key.space and self._recording:
            self._recording = False
            
            # Encerra a captura do microfone
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass

            print("[Microfone] 🛑 A processar a fala...")

            if not self._audio_data:
                print("[Microfone] Nenhum dado de áudio capturado.")
                return

            # Converte os bytes para um array numpy
            samples = np.frombuffer(bytes(self._audio_data), dtype=np.int16).astype(np.float32)
            max_volume = np.max(np.abs(samples)) if len(samples) > 0 else 0

            if max_volume < 80:
                print(f"[Microfone] ⚠️ Som muito fraco ou ausente (Volume máx: {max_volume}). Verifique se o microfone está ativo.")
                return

            # 1. Normalização do ganho (amplifica o áudio para a faixa ideal do Vosk)
            samples = samples * (24000.0 / max_volume)

            # 2. Conversão da taxa de amostragem para 16000Hz exigida pelo Vosk
            if self.native_sr != self.target_sr:
                duration = len(samples) / self.native_sr
                target_length = int(duration * self.target_sr)
                orig_indices = np.linspace(0, len(samples) - 1, num=len(samples))
                target_indices = np.linspace(0, len(samples) - 1, num=target_length)
                samples = np.interp(target_indices, orig_indices, samples)

            processed_bytes = np.clip(samples, -32768, 32767).astype(np.int16).tobytes()

            # 3. Transcrição pelo Vosk
            rec = KaldiRecognizer(self._model, self.target_sr)
            text_parts = []
            chunk_size = 4000

            for i in range(0, len(processed_bytes), chunk_size):
                chunk = processed_bytes[i:i + chunk_size]
                if rec.AcceptWaveform(chunk):
                    res = json.loads(rec.Result())
                    txt = res.get("text", "").strip()
                    if txt:
                        text_parts.append(txt)

            final_res = json.loads(rec.FinalResult())
            final_txt = final_res.get("text", "").strip()
            if final_txt:
                text_parts.append(final_txt)

            texto = " ".join(text_parts).strip().lower()

            if texto:
                print(f"[Microfone] Disse: \"{texto}\"")
                if self.on_text:
                    self.on_text(texto)
            else:
                print("[Microfone] Nenhuma palavra reconhecida. Tente falar de forma clara a uma distância constante do microfone.")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"[Listener] Status: {status}")
        if self._recording:
            self._audio_data.extend(bytes(indata))