import os
import tempfile
import wave
import threading

import numpy as np
import sounddevice as sd
from groq import Groq
from pynput import keyboard

TARGET_SR = 16000  # Taxa ideal para processamento de áudio


def _testar_taxa(device, taxa: int) -> bool:
    """Tenta abrir o microfone nessa taxa. Só responde se dá ou não."""
    try:
        stream = sd.RawInputStream(
            device=device,
            samplerate=taxa,
            blocksize=4000,
            dtype="int16",
            channels=1,
            callback=lambda *a: None,
        )
        stream.start()
        stream.stop()
        stream.close()
        return True
    except Exception:
        return False


def listar_microfones(testar=True) -> list[dict]:
    """Microfones disponíveis, um item por dispositivo de entrada."""
    apis = sd.query_hostapis()
    microfones = []
    for indice, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] < 1:
            continue
        microfones.append({
            "indice": indice,
            "nome": d["name"],
            "api": apis[d["hostapi"]]["name"],
            "canais": d["max_input_channels"],
            "taxa_informada": int(d["default_samplerate"]),
            "aceita_16k": _testar_taxa(indice, TARGET_SR) if testar else None,
        })
    return microfones


def resolver_microfone(device):
    """Converte a escolha do utilizador num índice de dispositivo."""
    if device is None or device == "":
        return None

    texto = str(device).strip()
    if isinstance(device, int) or texto.isdigit():
        return _validar_indice(int(texto))

    alvo = texto.lower()
    for indice, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and alvo in d["name"].lower():
            return indice
    raise ValueError(f"Nenhum microfone com '{texto}' no nome")


def _validar_indice(indice: int) -> int:
    dispositivos = sd.query_devices()
    if not 0 <= indice < len(dispositivos):
        raise ValueError(f"Não existe dispositivo com índice {indice}")
    if dispositivos[indice]["max_input_channels"] < 1:
        raise ValueError(f"O dispositivo {indice} não é um microfone, não tem entrada de áudio")
    return indice


def nome_do_microfone(device) -> str:
    try:
        d = sd.query_devices(kind="input") if device is None else sd.query_devices(device)
        return d["name"]
    except Exception:
        return "desconhecido"


class Listener:
    """Escuta o microfone apenas enquanto a barra de espaço estiver premida (Push-to-Talk)
    e transcreve a fala através da API Groq Whisper.
    """

    def __init__(self, on_text=None, lang="pt", device=None):
        self.on_text = on_text
        self.target_sr = TARGET_SR
        self.lang = lang
        self._recording = False
        self._audio_data = bytearray()
        self._listener_keyboard = None
        self._stream = None

        # Inicializa o cliente da Groq (lê a GROQ_API_KEY do ficheiro .env)
        self.client = Groq()

        self.device = None
        self.sample_rate = None
        if device is not None and device != "":
            try:
                self.device = resolver_microfone(device)
            except ValueError as e:
                print(f"[Listener] {e}. A usar o microfone padrão.")

    def start(self):
        """Ativa a monitorização do teclado para o Push-to-Talk."""
        print(f"[Listener] Push-to-Talk ativado (Groq Whisper). Microfone: {nome_do_microfone(self.device)}")
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

    def set_device(self, device) -> tuple[bool, str]:
        """Troca o microfone em uso. Devolve (deu certo, mensagem)."""
        if self._recording:
            return False, "Gravação em andamento, solte a barra de espaço primeiro"
        try:
            resolvido = resolver_microfone(device)
        except ValueError as e:
            return False, str(e)

        if not _testar_taxa(resolvido, TARGET_SR) and not _testar_taxa(resolvido, None):
            return False, f"'{nome_do_microfone(resolvido)}' não abriu, pode estar em uso por outro programa"

        self.device = resolvido
        self.sample_rate = None
        return True, nome_do_microfone(resolvido)

    def _taxa_informada(self) -> int:
        try:
            d = sd.query_devices(kind="input") if self.device is None else sd.query_devices(self.device)
            return int(d["default_samplerate"])
        except Exception:
            return 44100

    def _abrir_stream(self):
        """Abre o microfone na melhor taxa que ele aceitar."""
        candidatas = dict.fromkeys([TARGET_SR, self._taxa_informada(), 48000, 44100])
        erro = None
        for taxa in candidatas:
            try:
                stream = sd.RawInputStream(
                    device=self.device,
                    samplerate=taxa,
                    blocksize=4000,
                    dtype="int16",
                    channels=1,
                    callback=self._audio_callback,
                )
                stream.start()
                self.sample_rate = taxa
                return stream
            except Exception as e:
                erro = e
        raise RuntimeError(f"Nenhuma taxa aceite por '{nome_do_microfone(self.device)}': {erro}")

    def _on_press(self, key):
        if key == keyboard.Key.space and not self._recording:
            self._recording = True
            self._audio_data = bytearray()

            print("\n[Microfone] 🎙️ A escutar... (fale agora e solte a barra no final)")

            try:
                self._stream = self._abrir_stream()
            except Exception as e:
                print(f"[Microfone] Erro ao abrir o microfone: {e}")
                self._recording = False

    def _on_release(self, key):
        if key == keyboard.Key.space and self._recording:
            self._recording = False

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass

            print("[Microfone] 🛑 A processar a fala com Groq Whisper...")

            if not self._audio_data:
                print("[Microfone] Nenhum dado de áudio capturado.")
                return

            threading.Thread(
                target=self._transcrever,
                args=(bytes(self._audio_data), self.sample_rate),
                daemon=True,
            ).start()

    def _transcrever(self, audio: bytes, sample_rate: int):
        samples = np.frombuffer(audio, dtype=np.int16)
        max_volume = np.max(np.abs(samples)) if len(samples) > 0 else 0

        if max_volume < 50:
            print(f"[Microfone] ⚠️ Som muito fraco ou ausente (Volume máx: {max_volume}).")
            return

        # 1. Cria um ficheiro .wav temporário com o áudio capturado
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_filename = temp_wav.name
            with wave.open(temp_filename, "wb") as wf:
                wf.setnchannels(1)        # Mono
                wf.setsampwidth(2)        # 16-bit (2 bytes por sample)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)

        try:
            # 2. Envia para a API do Groq Whisper
            with open(temp_filename, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(temp_filename, file.read()),
                    model="whisper-large-v3-turbo",
                    language="pt",
                    prompt="Comandos de voz para aplicação gráfica, CNC e desenho."
                )

            texto = transcription.text.strip().lower()

            if texto:
                print(f"[Microfone - Whisper] Disse: \"{texto}\"")
                if self.on_text:
                    self.on_text(texto)
            else:
                print("[Microfone] Nenhuma palavra reconhecida.")

        except Exception as e:
            print(f"[Microfone] Erro ao transcrever via Groq Whisper: {e}")

        finally:
            # 3. Apaga o ficheiro temporário
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"[Listener] Status: {status}")
        if self._recording:
            self._audio_data.extend(bytes(indata))