import threading

import config
from ai.llm import GroqLLM
from ai.prompts import EVENTO_CNC_INICIOU, EVENTO_CNC_TERMINOU, EVENTO_NAO_IDENTIFICADO
from face.face import Face
from server.state import PARADO, PENSANDO, State
from voice.listener import Listener, listar_microfones, nome_do_microfone
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
Microfone:
  /mics               lista os microfones e testa qual funciona
  /mic <n|nome>       troca o microfone (ex.: /mic 14   ou   /mic QCY)
  /mic                mostra o microfone em uso
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

    # O console e o push-to-talk rodam em threads diferentes e os dois chegam
    # aqui. Sem a trava, duas perguntas simultâneas mexiam no llm.history ao
    # mesmo tempo. É RLock porque o CNC_SIM chama responder() de novo, de
    # dentro dela, e um Lock comum travaria a si mesmo.
    trava = threading.RLock()

    def responder(gerar):
        with trava:
            speaker.cancel()
            state.set(PENSANDO)
            texto, comando = gerar()
            print(f"[IA] {texto}")
            if comando:
                print(f"[Comando detetado] {comando}")

            speaker.say(texto)

            if comando == "CNC_SIM":
                # Espera a confirmação acabar de ser falada antes de encadear o evento.
                # responder() começa com speaker.cancel(), e speaker.say() também cancela
                # a fala anterior: sem esta espera o áudio da confirmação era cortado
                # antes de o Piper sequer sintetizar a primeira frase, e o visitante
                # ouvia silêncio justo depois de dizer que sim.
                speaker.wait()
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
        with trava:
            llm.reset()
            state.objeto = None
            state.set(PARADO)
        print("[sistema] conversa zerada")

    def mostrar_microfones():
        """Lista os microfones e testa cada um, para saber qual usar."""
        print("\n[microfone] a testar os aparelhos...")
        for m in listar_microfones():
            marca = "16k ok " if m["aceita_16k"] else "16k nao"
            atual = "  <== em uso" if m["indice"] == listener.device else ""
            print(f"  [{m['indice']:2d}] {marca}  {m['nome'][:38]:38s} {m['api']}{atual}")

        if listener.device is None:
            print(f"\n  em uso: padrão do sistema -> {nome_do_microfone(None)}")
        print("\n  Troque com /mic <número>. Prefira os marcados '16k ok':")
        print("  esses gravam direto na taxa do Vosk, sem reamostragem.\n")

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
                elif baixo == "/mics":
                    mostrar_microfones()
                elif baixo == "/mic":
                    print(f"[microfone] em uso: {nome_do_microfone(listener.device)}")
                elif baixo.startswith("/mic "):
                    ok, msg = listener.set_device(entrada[len("/mic "):].strip())
                    print(f"[microfone] {'agora a usar: ' + msg if ok else 'não trocou: ' + msg}")
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

    # Inicia o módulo de escuta por voz (Módulo 4)
    listener = Listener(on_text=comando_voz, device=config.MIC_DEVICE)
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