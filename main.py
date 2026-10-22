# main.py
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import config
from ai.llm import GroqLLM
from ai.prompts import EVENTO_CNC_INICIOU, EVENTO_CNC_TERMINOU, EVENTO_NAO_IDENTIFICADO
from firmware.cnc import converter_svg_para_gcode, executar_cnc
from server.state import PARADO, PENSANDO, State
from ui.dialogs import confirmar_operador_cnc
from ui.face import Face
from ui.manager import GameManager
from vision.svg_export import gerar_svg
from vision.watcher import DrawingWatcher
from voice.listener import Listener, listar_microfones, nome_do_microfone
from voice.speaker import Speaker
from voice.tts import PiperTTS
from server.state import FALANDO, PARADO, PENSANDO, State

# Caminho do script de retrato (fica na pasta "tests", ao lado do main.py)
SCRIPT_RETRATO = Path(__file__).parent / "tests" / "captura_e_gcode.py"

AJUDA = """
Digite o que o visitante diria (ex.: oi, quem é você, sim, não).
Modos de Jogo:
  /modo livre        ativa o modo livre (sem tempo limite)
  /desafio           inicia o desafio rápido (30s para desenhar um item sorteado)

Retrato:
  imprimir           tira um retrato com a webcam e desenha na CNC
                     (também funciona por voz: diga "imprimir")

Simulações:
  /desenho <nome>    simula a visão identificando um desenho (ex.: /desenho casa)
  /naoidentificado   a visão não conseguiu identificar
  /cnc inicio        a CNC começou a desenhar
  /cnc fim           a CNC terminou
  /novo              novo visitante (zera a conversa e o reconhecimento)

Microfone:
  /mics              lista os microfones e testa qual funciona
  /mic <n|nome>      troca o microfone (ex.: /mic 14   ou   /mic QCY)
  /mic               mostra o microfone em uso
Fala:  parar | continuar
Sair:  sair
"""

FRASES_DESAFIO = (
    "iniciar desafio",
    "modo desafio",
    "jogar desafio",
    "desafio",
)
FRASES_LIVRE = (
    "modo livre",
    "desenho livre",
    "cancelar desafio",
)
FRASES_PRONTO = (
    "pronto",
    "pode olhar",
    "coloquei",
)
def eh_pedido_imprimir(texto: str) -> bool:
    """True só para pedidos curtos como 'imprimir' ou 'imprimir retrato'.

    Frases longas (como a fala do próprio Max dizendo "vou imprimir seu
    desenho", captada pelo microfone) NÃO disparam o retrato.
    """
    palavras = texto.lower().strip().split()
    return 0 < len(palavras) <= 3 and any(p.startswith("imprim") for p in palavras)


def main():
    state = State()
    state.subscribe(lambda e: print(f"[estado] {e}"))

    face = Face(state=state, display_index=1)

    tts = PiperTTS(
        config.PIPER_EXE,
        config.PIPER_MODEL,
        length_scale=config.PIPER_LENGTH_SCALE,
        sentence_silence=config.PIPER_SENTENCE_SILENCE,
    )
    speaker = Speaker(tts, on_state=state.set)
    llm = GroqLLM()

    trava = threading.RLock()

    # Evita abrir dois retratos ao mesmo tempo
    retrato_em_andamento = threading.Event()

    # Callback de atalho para conversas diretas
    def conversar(mensagem: str):
        responder(lambda: llm.chat(mensagem))

    # Função intermediária para congelar e salvar o SVG no exato momento da detecção
    def ao_detectar_desenho(obj):
        if watcher.ultimos_contornos:
            try:
                gerar_svg(watcher.ultimos_contornos, tamanho=300, caminho="desenho.svg")
                print("[sistema] Desenho congelado e salvo em desenho.svg com sucesso!")
            except Exception as e:
                print(f"[aviso] Erro ao salvar SVG prévio: {e}")
        game_manager.processar_desenho(obj, responder)

    # Inicialização da Visão e do Gerenciador de Jogos
    watcher = DrawingWatcher(on_desenho=ao_detectar_desenho)
    watcher.start()

    game_manager = GameManager(
        state=state,
        watcher=watcher,
        llm=llm,
        conversar_fn=conversar,
        speaker=speaker,
    )

    # ------------------------------------------------------------------
    # RETRATO: executa captura_e_gcode.py como processo separado
    # ------------------------------------------------------------------
    def iniciar_retrato():
        if retrato_em_andamento.is_set():
            print("[retrato] já existe um retrato em andamento.")
            return

        if not SCRIPT_RETRATO.exists():
            print(f"[retrato] script não encontrado: {SCRIPT_RETRATO}")
            return

        def trabalhar():
            nonlocal watcher
            retrato_em_andamento.set()
            try:
                speaker.cancel()
                speaker.say("Certo! Vou abrir a câmera para o seu retrato. "
                            "Aperte espaço para tirar a foto.")
                speaker.wait()

                # Libera a webcam para o outro script
                watcher.stop()
                time.sleep(1.0)  # dá tempo de a câmera ser liberada pelo sistema

                print("[retrato] executando captura_e_gcode.py ...")
                subprocess.run([sys.executable, str(SCRIPT_RETRATO)], check=False)
                print("[retrato] script finalizado.")
            except Exception as e:
                print(f"[retrato] erro: {e}")
            finally:
                # Religa a visão (novo objeto, pois o anterior foi parado)
                try:
                    watcher = DrawingWatcher(on_desenho=ao_detectar_desenho)
                    if hasattr(game_manager, "watcher"):
                        game_manager.watcher = watcher
                    watcher.start()
                except Exception as e:
                    print(f"[retrato] erro ao religar a visão: {e}")
                game_manager.limpar_estado()
                retrato_em_andamento.clear()

        threading.Thread(target=trabalhar, daemon=True).start()

    def responder(gerar):
        with trava:
            speaker.cancel()
            state.set(PENSANDO)
            texto, comando = gerar()

            # 1. Identifica marcadores de intenção retornados pela IA
            tem_confirmar_desenho = "[[CONFIRMAR_DESENHO]]" in texto
            tem_desafio_sim = "[[DESAFIO_SIM]]" in texto
            tem_desafio_nao = "[[DESAFIO_NAO]]" in texto
            tem_cnc_sim = "[[CNC_SIM]]" in texto or comando == "CNC_SIM"
            tem_cnc_nao = "[[CNC_NAO]]" in texto or comando == "CNC_NAO"

            # 2. Limpa todos os marcadores para o Max NÃO lê-los em voz alta
            texto_limpo = texto
            for tag in [
                "[[CONFIRMAR_DESENHO]]",
                "[[DESAFIO_SIM]]",
                "[[DESAFIO_NAO]]",
                "[[CNC_SIM]]",
                "[[CNC_NAO]]",
            ]:
                texto_limpo = texto_limpo.replace(tag, "").strip()

            print(f"[IA] {texto_limpo}")
            speaker.say(texto_limpo)

            # 3. Executa as ações associadas aos marcadores
            if tem_confirmar_desenho:
                print("[Controle] Marcador [[CONFIRMAR_DESENHO]] detectado! Solicitando captura...")
                if not watcher.confirmar():
                    conversar(EVENTO_NAO_IDENTIFICADO)

            elif tem_desafio_sim:
                print("[Controle] Marcador [[DESAFIO_SIM]] detectado! Iniciando novo desafio...")
                threading.Thread(target=game_manager.iniciar_desafio, daemon=True).start()

            elif tem_desafio_nao:
                print("[Controle] Marcador [[DESAFIO_NAO]] detectado! Retornando ao Modo Livre.")
                game_manager.ativar_modo_livre()

            elif tem_cnc_sim:
                speaker.wait()
                if confirmar_operador_cnc():
                    print("[CNC] Operador confirmou o início!")
                    conversar(EVENTO_CNC_INICIOU)
                    enviar_para_cnc()  # Converte o SVG salvo -> G-code -> Envia para a CNC
                else:
                    print("[CNC] Operador CANCELOU a operação.")
                    conversar("O envio para a CNC foi cancelado pelo operador. Avise o visitante de forma simpática.")
                    game_manager.limpar_estado()

                game_manager.limpar_estado()

    def comando_voz(texto: str):
        txt = texto.lower().strip()

        # Durante o retrato o Max não deve reagir a nada (nem à própria voz)
        if retrato_em_andamento.is_set():
            return

        if txt == "parar":
            speaker.pause()
        elif txt == "continuar":
            speaker.resume()
        elif eh_pedido_imprimir(txt):
            iniciar_retrato()
        elif state.aguardando_posicionamento and any(f in txt for f in FRASES_PRONTO):
            game_manager.confirmar_e_analisar(responder)
        elif any(f in txt for f in FRASES_DESAFIO):
            game_manager.iniciar_desafio()
        elif any(f in txt for f in FRASES_LIVRE):
            game_manager.ativar_modo_livre()
        else:
            conversar(texto)

    def novo_visitante():
        speaker.cancel()
        with trava:
            llm.reset()
            game_manager.limpar_estado()
            game_manager.ativar_modo_livre()
            state.set(PARADO)
        print("[sistema] conversa zerada (Modo Livre ativado)")

    def mostrar_microfones():
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
                elif eh_pedido_imprimir(baixo):
                    iniciar_retrato()   # nunca chega na IA
                elif baixo in ("parar", "continuar"):
                    comando_voz(baixo)
                elif baixo == "/modo livre":
                    game_manager.ativar_modo_livre()
                elif baixo == "/desafio":
                    game_manager.iniciar_desafio()
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
                    game_manager.processar_desenho(entrada[len("/desenho "):].strip(), responder)
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
            face.parar()

    def enviar_para_cnc():
        svg_path = "desenho.svg"
        if not os.path.exists(svg_path):
            conversar("Não encontrei um desenho salvo para mandar à CNC. "
                      "Avise o visitante com simpatia e sugira desenhar de novo.")
            game_manager.limpar_estado()
            return

        def trabalhar():
            try:
                # Converte o SVG fixo do disco para G-code e envia para a CNC com segurança
                gcode_path = converter_svg_para_gcode(svg_path)
                executar_cnc(gcode_path)
            except Exception as e:
                print(f"[CNC] erro: {e}")
                conversar("Algo deu errado ao desenhar na CNC. Avise o "
                          "visitante com calma e sugira chamar um estudante da equipe.")
            else:
                conversar(EVENTO_CNC_TERMINOU)
            finally:
                game_manager.limpar_estado()

        threading.Thread(target=trabalhar, daemon=True).start()

    listener = Listener(on_text=comando_voz, device=config.MIC_DEVICE)
    listener.start()

    thread_console = threading.Thread(target=loop_console, daemon=True)
    thread_console.start()

    try:
        face.run()
    finally:
        game_manager.parar_timer()
        watcher.stop()
        listener.stop()
        speaker.cancel()


if __name__ == "__main__":
    main()