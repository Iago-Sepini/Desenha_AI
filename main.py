import config
from ai.llm import GroqLLM
from ai.prompts import EVENTO_CNC_INICIOU, EVENTO_CNC_TERMINOU, EVENTO_NAO_IDENTIFICADO
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

    def responder(gerar):
        """Interrompe a fala atual, mostra 'pensando', gera a resposta e fala."""
        speaker.cancel()
        state.set(PENSANDO)
        texto, comando = gerar()
        print(f"[IA] {texto}")
        if comando:
            print(f"[Comando detetado] {comando}")

        speaker.say(texto)

        # Se a IA detetou a autorização do visitante para a CNC começar
        if comando == "CNC_SIM":
            # Espera a confirmação acabar de ser falada antes de encadear o evento.
            # responder() começa com speaker.cancel(), e speaker.say() também cancela
            # a fala anterior: sem esta espera o áudio da confirmação era cortado
            # antes de o Piper sequer sintetizar a primeira frase, e o visitante
            # ouvia silêncio justo depois de dizer que sim.
            speaker.wait()
            conversar(EVENTO_CNC_INICIOU)

    # --- pontos de entrada ---
    def processar_desenho(objeto: str):
        state.objeto = objeto
        responder(lambda: llm.describe(objeto))

    def conversar(mensagem: str):
        responder(lambda: llm.chat(mensagem))

    def comando_voz(texto: str):
        """Processa tanto os comandos de controlo da fala como a fala direta do visitante."""
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

    # Inicia o módulo de escuta por voz (Módulo 4)
    listener = Listener(on_text=comando_voz)
    listener.start()

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
        listener.stop()
        speaker.cancel()


if __name__ == "__main__":
    main()