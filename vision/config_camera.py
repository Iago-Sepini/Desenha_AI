"""
CONFIGURAÇÃO DA CÂMERA

Como módulo (no seu código principal):
    from config_camera import abrir_camera, ler_frame, recortar_quadrado
    cap, cfg = abrir_camera()               # lê camera_config.json (ou usa o padrão)
    frame = ler_frame(cap, cfg)             # já espelha se estiver configurado
    roi, caixa = recortar_quadrado(frame, cfg)

Como programa (para configurar):
    py -3.10 vision/config_camera.py --listar              lista os índices de câmera que abrem
    py -3.10 vision/config_camera.py --testar              abre o preview para ajustar e salvar
    py -3.10 vision/config_camera.py --testar --cam 1      testa a câmera de índice 1

Teclas no preview:
    n = próxima câmera | m = espelhar | + / - = tamanho do quadrado
    s = SALVAR em camera_config.json | q = sair
"""
import argparse
import json
import os
import platform

import cv2

ARQUIVO_CONFIG = "camera_config.json"

PADRAO = {
    "indice": 0,              # número da câmera (0 = primeira, 1 = segunda...)
    "largura": 1280,          # resolução pedida à câmera
    "altura": 720,
    "espelhar": False,        # inverte esquerda/direita
    "tamanho_quadrado": 0.6,  # tamanho da área de leitura (fração do menor lado, 0.2 a 0.95)
}


# ---------------------------------------------------------------- config
def carregar_config(caminho=ARQUIVO_CONFIG):
    cfg = dict(PADRAO)
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"Aviso: não consegui ler {caminho} ({e}). Usando o padrão.")
    return cfg


def salvar_config(cfg, caminho=ARQUIVO_CONFIG):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------- câmera
def _backend():
    # CAP_DSHOW abre mais rápido e com menos erros no Windows
    return cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY


def listar_cameras(maximo=10):
    """Retorna [(indice, largura, altura), ...] das câmeras que realmente entregam imagem."""
    achadas = []
    for i in range(maximo):
        cap = cv2.VideoCapture(i, _backend())
        if cap.isOpened():
            ok, frame = cap.read()
            if ok:
                achadas.append((i, frame.shape[1], frame.shape[0]))
        cap.release()
    return achadas


def abrir_camera(cfg=None):
    """Abre a câmera conforme a configuração. Retorna (cap, cfg)."""
    cfg = cfg or carregar_config()
    cap = cv2.VideoCapture(int(cfg["indice"]), _backend())
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(
            f"Não consegui abrir a câmera {cfg['indice']}. "
            "Rode: py -3.10 config_camera.py --listar"
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cfg["largura"]))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cfg["altura"]))
    return cap, cfg


def ler_frame(cap, cfg):
    """Lê um frame (espelhado se configurado). Retorna None se falhar."""
    ok, frame = cap.read()
    if not ok:
        return None
    if cfg.get("espelhar"):
        frame = cv2.flip(frame, 1)
    return frame


def recortar_quadrado(frame, cfg):
    """Recorta o quadrado central. Retorna (roi, (x0, y0, lado))."""
    H, W = frame.shape[:2]
    lado = int(min(H, W) * float(cfg["tamanho_quadrado"]))
    x0, y0 = (W - lado) // 2, (H - lado) // 2
    return frame[y0:y0 + lado, x0:x0 + lado], (x0, y0, lado)


# ---------------------------------------------------------------- preview
def testar(cfg):
    cap, cfg = abrir_camera(cfg)
    print("Preview aberto. n=próxima câmera | m=espelhar | +/-=tamanho | s=salvar | q=sair")
    while True:
        frame = ler_frame(cap, cfg)
        if frame is None:
            print("Sem imagem da câmera.")
            break
        _, (x0, y0, lado) = recortar_quadrado(frame, cfg)
        cv2.rectangle(frame, (x0, y0), (x0 + lado, y0 + lado), (0, 255, 0), 2)
        info = (f"cam {cfg['indice']} | {frame.shape[1]}x{frame.shape[0]} | "
                f"quadrado {cfg['tamanho_quadrado']:.2f} | espelho {'ON' if cfg['espelhar'] else 'OFF'}")
        cv2.putText(frame, info, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, "n=camera m=espelhar +/-=tamanho s=salvar q=sair", (10, frame.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.imshow("Config camera", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("m"):
            cfg["espelhar"] = not cfg["espelhar"]
        elif key in (ord("+"), ord("=")):
            cfg["tamanho_quadrado"] = min(0.95, round(cfg["tamanho_quadrado"] + 0.05, 2))
        elif key == ord("-"):
            cfg["tamanho_quadrado"] = max(0.2, round(cfg["tamanho_quadrado"] - 0.05, 2))
        elif key == ord("s"):
            salvar_config(cfg)
            print(f"Salvo em {ARQUIVO_CONFIG}: {cfg}")
        elif key == ord("n"):
            antigo = cfg["indice"]
            cfg["indice"] = (antigo + 1) % 10
            cap.release()
            try:
                cap, cfg = abrir_camera(cfg)
            except RuntimeError:
                cfg["indice"] = antigo
                cap, cfg = abrir_camera(cfg)
                print("Essa câmera não abriu; voltei para a anterior.")
    cap.release()
    cv2.destroyAllWindows()


def main():
    p = argparse.ArgumentParser(description="Configuração da câmera")
    p.add_argument("--listar", action="store_true", help="lista as câmeras disponíveis")
    p.add_argument("--testar", action="store_true", help="preview para ajustar e salvar")
    p.add_argument("--cam", type=int, help="índice da câmera")
    p.add_argument("--largura", type=int)
    p.add_argument("--altura", type=int)
    args = p.parse_args()

    if args.listar:
        cams = listar_cameras()
        if not cams:
            print("Nenhuma câmera encontrada. Feche Zoom/Teams/navegador e confira a privacidade do Windows.")
        for i, w, h in cams:
            print(f"Câmera {i}: OK ({w}x{h})")
        return

    cfg = carregar_config()
    if args.cam is not None:
        cfg["indice"] = args.cam
    if args.largura:
        cfg["largura"] = args.largura
    if args.altura:
        cfg["altura"] = args.altura

    if args.testar:
        testar(cfg)
    else:
        print("Configuração atual:", json.dumps(cfg, indent=2))
        print("\nUse --listar para ver as câmeras ou --testar para ajustar e salvar.")


if __name__ == "__main__":
    main()