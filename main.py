import threading

import config
from ai.llm import GroqLLM
from ai.prompts import EVENTO_CNC_INICIOU, EVENTO_CNC_TERMINOU, EVENTO_NAO_IDENTIFICADO
from face.face import Face
from server.state import PARADO, PENSANDO, State
from voice.listener import Listener
from voice.speaker import Speaker
from voice.tts import PiperTTS

AJUDA = """
Digite o que o visitante diria (ex.: oi, quem é você, sim, não).
Simulações:
  /desenho <nome>     a visão identificou um desenho (ex.: /desenho bob esponja)
  /naoidentificado    a visão não conseguiu identificar
  /cnc inicio         a CNC começou a desenhar
  /cnc fim            a CNC terminou
  /novo               novo visitante (zera a conversa)
Fala:  parar | continuar
Sair:  sair

Janela do rosto: arraste para a tela do HDMI e aperte F11 para tela cheia.
"""


def main():
    state = State()
    state.subscribe(lambda e: print(f"[estado] {e}"))

    tts = PiperTTS(
        config.PIPER_EXE,
        config.PIPER_MODEL,
        length_scale=config.PIPER_LENGTH_SCALE,
        sentence_silence=config.PIPER_SENTENCE_SILENCE,
    )
    speaker = Speaker(tts, on_state=state.set)
    llm = GroqLLM()
    face = Face()

    def responder(gerar):
        speaker.cancel()
        state.set(PENSANDO)
        texto, comando = gerar()
        print(f"[IA] {texto}")
        if comando:
            print(f"[Comando detetado] {comando}")

        speaker.say(texto)

        if comando == "CNC_SIM":
            conversar(EVENTO_CNC_INICIOU)

    def processar_desenho(objeto: str):
        state.objeto = objeto
        responder(lambda: llm.describe(objeto))

    def conversar(mensagem: str):
        responder(lambda: llm.chat(mensagem))

    def comando_voz(texto: str):
        txt = texto.lower().strip()
        if txt == "parar":
            speaker.pause()
        elif txt == "continuar":
            speaker.resume()
        else:
            conversar(texto)

    def novo_visitante():
        speaker.cancel()
        llm.reset()
        state.objeto = None
        state.set(PARADO)
        print("[sistema] conversa zerada")

    def loop_console():
        print(AJUDA)
        try:
            while True:
                entrada = input("> ").strip()
                if not entrada:
                    continue
                baixo = entrada.lower()

                if baixo == "sair":
                    break
                elif baixo in ("parar", "continuar"):
                    comando_voz(baixo)
                elif baixo == "/novo":
                    novo_visitante()
                elif baixo.startswith("/desenho "):
                    processar_desenho(entrada[len("/desenho "):].strip())
                elif baixo == "/naoidentificado":
                    conversar(EVENTO_NAO_IDENTIFICADO)
                elif baixo == "/cnc inicio":
                    conversar(EVENTO_CNC_INICIOU)
                elif baixo == "/cnc fim":
                    conversar(EVENTO_CNC_TERMINOU)
                else:
                    conversar(entrada)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            face.parar()  # fechar o console também fecha o rosto

    listener = Listener(on_text=comando_voz)
    listener.start()

    thread_console = threading.Thread(target=loop_console, daemon=True)
    thread_console.start()

    try:
        face.run()  # bloqueia aqui, na thread principal
    finally:
        listener.stop()
        speaker.cancel()


if __name__ == "__main__":
    main()