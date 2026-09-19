import config
from ai.llm import GroqLLM
from ai.prompts import EVENTO_CNC_INICIOU, EVENTO_CNC_TERMINOU, EVENTO_NAO_IDENTIFICADO
from server.state import PARADO, PENSANDO, State
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
    speaker = Speaker(tts, on_state=state.set)  # o Speaker atualiza o estado sozinho
    llm = GroqLLM()

    def responder(gerar):
        """Interrompe a fala atual, mostra 'pensando', gera a resposta e fala."""
        speaker.cancel()
        state.set(PENSANDO)
        texto = gerar()
        print(f"[IA] {texto}")
        speaker.say(texto)

    # --- pontos de entrada (no projeto final, outros módulos chamam estas funções) ---
    def processar_desenho(objeto: str):  # Módulo 1 (visão)
        state.objeto = objeto
        responder(lambda: llm.describe(objeto))

    def conversar(mensagem: str):  # fala do visitante ou aviso do sistema
        responder(lambda: llm.chat(mensagem))

    def comando_voz(cmd: str):  # Módulo 4 (microfone)
        if cmd == "parar":
            speaker.pause()
        elif cmd == "continuar":
            speaker.resume()

    def novo_visitante():
        speaker.cancel()
        llm.reset()
        state.objeto = None
        state.set(PARADO)
        print("[sistema] conversa zerada")

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
        speaker.cancel()


if __name__ == "__main__":
    main()