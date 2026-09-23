import json
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from pynput import keyboard

TARGET_SR = 16000  # taxa exigida pelo Vosk


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
    """Microfones disponíveis, um item por dispositivo de entrada.

    A taxa que o Windows informa não é confiável: a API MME devolve 44100 para
    todos os aparelhos, por ser um valor genérico, enquanto a taxa real aparece
    nas APIs nativas. Por isso, em vez de acreditar no valor informado, cada
    aparelho é testado de verdade em 16000 Hz, que é a taxa que o Vosk exige.
    """
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
    """Converte a escolha do utilizador num índice de dispositivo.

    Aceita None (usa o padrão do sistema), um índice, ou parte do nome do
    aparelho - assim o .env pode trazer MIC_DEVICE=QCY em vez de um número,
    que muda de posição quando se liga ou desliga um aparelho.
    """
    if device is None or device == "":
        return None

    texto = str(device).strip()
    if isinstance(device, int) or texto.isdigit():
        return _validar_indice(int(texto))

    alvo = texto.lower()
    for indice, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and alvo in d["name"].lower():
            return indice
    raise ValueError(f"nenhum microfone com '{texto}' no nome")


def _validar_indice(indice: int) -> int:
    dispositivos = sd.query_devices()
    if not 0 <= indice < len(dispositivos):
        raise ValueError(f"não existe dispositivo com índice {indice}")
    if dispositivos[indice]["max_input_channels"] < 1:
        raise ValueError(f"o dispositivo {indice} não é um microfone, não tem entrada de áudio")
    return indice


def nome_do_microfone(device) -> str:
    try:
        d = sd.query_devices(kind="input") if device is None else sd.query_devices(device)
        return d["name"]
    except Exception:
        return "desconhecido"


class Listener:
    """Escuta o microfone apenas enquanto a barra de espaço estiver premida (Push-to-Talk)."""

    def __init__(self, on_text=None, lang="pt", device=None):
        self.on_text = on_text
        self.target_sr = TARGET_SR
        self.lang = lang
        self._recording = False
        self._audio_data = bytearray()
        self._listener_keyboard = None
        self._model = None
        self._stream = None

        # None = microfone padrão do sistema. A taxa não é detetada aqui: cada
        # gravação abre o aparelho na melhor taxa que ele aceitar (ver _abrir_stream).
        self.device = None
        self.sample_rate = None
        if device is not None and device != "":
            try:
                self.device = resolver_microfone(device)
            except ValueError as e:
                print(f"[Listener] {e}. A usar o microfone padrão.")

    def start(self):
        """Inicializa o modelo de voz e ativa a monitorização do teclado."""
        try:
            self._model = Model(lang=self.lang)
        except Exception as e:
            print(f"[Listener] Erro ao carregar o modelo de voz Vosk: {e}")
            return

        print(f"[Listener] Push-to-Talk ativado. Microfone: {nome_do_microfone(self.device)}")
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
        """Troca o microfone em uso. Devolve (deu certo, mensagem).

        Não precisa reiniciar nada: o aparelho só é aberto no momento da
        gravação, então a próxima vez que a barra de espaço for premida já usa
        o microfone novo.
        """
        if self._recording:
            return False, "gravação em andamento, solte a barra de espaço primeiro"
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
        """Abre o microfone na melhor taxa que ele aceitar.

        A ordem importa: 16000 Hz vem primeiro porque é a taxa que o Vosk exige,
        e gravar direto nela dispensa qualquer reamostragem. As outras são
        tentativas de recurso para aparelhos que recusem 16000.
        """
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
        raise RuntimeError(f"nenhuma taxa aceita por '{nome_do_microfone(self.device)}': {erro}")

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

            # 2. Conversão da taxa de amostragem para 16000Hz exigida pelo Vosk.
            # Normalmente não corre: _abrir_stream() já tenta gravar direto em 16000.
            if self.sample_rate != self.target_sr:
                duration = len(samples) / self.sample_rate
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