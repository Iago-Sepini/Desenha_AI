<div align="center">

![](https://capsule-render.vercel.app/api?type=waving&color=gradient&height=185&section=header&text=Desenha%20AI&fontSize=55)

**Um desenho à mão, reconhecido por visão computacional, explicado por uma IA e redesenhado por uma máquina CNC.**

![Status](https://img.shields.io/badge/Status-Em_desenvolvimento-red)
![Version](https://img.shields.io/badge/Version-0.3.2--beta-purple?style=flat-square)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)
[![Ultimo Update](https://img.shields.io/github/last-commit/Iago-Sepini/Desenha_AI?label=Ultimo%20Update&style=classic)](https://github.com/Iago-Sepini/Desenha_AI)

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/solar.png" width="100%">

## 📖 Sobre o projeto

O **Desenha AI** é um sistema que une visão computacional, inteligência artificial e automação física. Um desenho feito à mão no papel é capturado por uma câmera, que identifica o traço e reconhece do que se trata. A partir disso, uma inteligência artificial pesquisa sobre o objeto e responde **em voz** com informações relevantes: material, curiosidades e contexto.

Em paralelo, o mesmo desenho é reproduzido fisicamente por uma **máquina CNC**, que interpreta o traço e o redesenha de forma automatizada.

> ♻️ **Reaproveitamento:** a CNC usada no projeto estava parada e foi reaproveitada especificamente para esta aplicação, mostrando como equipamentos ociosos podem ganhar nova utilidade quando integrados a sistemas de inteligência artificial e visão computacional.

## 🎯 Aplicação prática

O principal objetivo é **auxiliar crianças em fase de aprendizado de escrita e desenho**, oferecendo um retorno imediato — **visual, físico e falado** — sobre aquilo que produzem. Ver o próprio traço sendo reconhecido e redesenhado por uma máquina reforça o aprendizado de forma lúdica e concreta.

## 🧩 Como funciona

O sistema é dividido em cinco módulos:

| # | Módulo | Descrição |
|---|--------|-----------|
| 1 | 📷 **Captura e identificação** | Câmera + OpenCV detectam o contorno do desenho no papel e o convertem para SVG. |
| 2 | 🤖 **Execução física** | O SVG é enviado a uma CNC controlada por Arduino, que redesenha o traço na máquina. |
| 3 | 🧠 **Pesquisa e fala** | O objeto identificado é enviado a uma LLM, que retorna um resumo; um TTS converte esse texto em voz. |
| 4 | 🎤 **Controle por voz** | Um microfone monitora comandos simples (*continuar* / *parar*) para controlar a fala em andamento. |
| 5 | 🙂 **Interface visual** | Um rosto 3D na tela reage ao estado da fala (falando/parado), servindo de interface com o visitante. |

### Fluxo geral

```mermaid
flowchart LR
    A["📷 Módulo 1<br/>Captura e identificação"] --> B["🤖 Módulo 2<br/>CNC + Arduino"]
    A --> C["🧠 Módulo 3<br/>LLM + TTS"]
    C --> E["🙂 Módulo 5<br/>Rosto 3D"]
    D["🎤 Módulo 4<br/>Controle por voz"] -. regula .-> C
```

O Módulo 1 alimenta os Módulos 2 e 3 **em paralelo**; o Módulo 3 alimenta o Módulo 5; e o Módulo 4 regula o Módulo 3.

## 🔌 Arquitetura extensível

A identificação do desenho foi pensada para ser **independente da máquina**. A mesma identificação pode ser conectada a outras máquinas além da CNC, permitindo automatizar diferentes tipos de ação a partir do mesmo reconhecimento visual — abrindo espaço para aplicações futuras além do desenho em si.

## 🛠️ Tecnologias


<div align="center">
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white" height="50" alt="Python" />
<img src="https://img.shields.io/badge/OpenCV-5C3EE8.svg?style=for-the-badge&logo=OpenCV&logoColor=white" height="50" alt="OpenCV" />
<img src="https://img.shields.io/badge/Groq-f55036?style=for-the-badge" height="50" alt="Groq" />
<img src="https://img.shields.io/badge/-Piper%20TTS-2EA44F?style=for-the-badge" height="50" alt="Piper" />
<img src="https://img.shields.io/badge/Arduino-00878F.svg?style=for-the-badge&logo=Arduino&logoColor=white" height="50" alt="Arduino" />
<img src="https://img.shields.io/badge/SVG-FFB13B.svg?style=for-the-badge&logo=SVG&logoColor=black" height="50" alt="SVG" />
 
</div>

## 📁 Estrutura do repositório

```
desenha-ai/
├── vision/      # captura, contorno e conversão para SVG
├── ai/          # integração com a LLM e prompts
├── voice/       # TTS e comandos de voz
├── server/      # estado da fala e comunicação com o rosto 3D
├── hardware/    # firmware Arduino e envio de G-code
├── face3d/      # rosto 3D da interface
├── docs/        # imagens, vídeo demonstrativo e materiais
├── main.py
└── .env.example
```

## 🚀 Como executar

> **Python 3.10** (o projeto usa o 3.10.11). Funciona do 3.10 ao 3.12; fora disso o TensorFlow, o Keras ou o numpy não instalam.
>
> A voz usa o `piper.exe` que já vem em `voice/piper/`. Não é preciso instalar o pacote `piper-tts`.

```bash
# 1. Clone o repositório
git clone https://github.com/Iago-Sepini/Desenha_AI.git
cd Desenha_AI

# 2. Crie o ambiente com Python 3.10 e instale as dependências
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure as variáveis de ambiente
cp .env.example .env
# edite o .env e adicione sua chave da Groq

# 4. Execute (sempre da raiz do projeto)
python main.py
```

## 📋 Requisitos
 
| Item | Função no projeto | Modelo |
|------|-------------------|--------|
| Câmera | Captura do desenho no papel | `Câmera USB C72` |
| Microfone | Comandos de voz (*continuar* / *parar*) | `[preencher]` |
| Caixa de som | Saída da voz do assistente | `Caixa de Som bluetooth` |
| Tela / monitor | Exibe o rosto 3D | <a href="https://www.makerhero.com/produto/display-compativel-raspberry-pi-touchscreen-5/?srsltid=AU7gw4VXneuPh6IYfOxRHZ24Os_GXvWyjQjwWg9B2a1CLV7JlWn0u0cTlpk">5 Inch HDMI display</a> |
| Máquina CNC | Redesenha o traço no papel | `[preencher]` |
| Placa Arduino | Controla a CNC | <a href="https://www.eletrogate.com/uno-r3-smd-ch340?utm_source=Site&utm_medium=GoogleMerchant&utm_campaign=GoogleMerchant&srsltid=AU7gw4U_AABZHFo7u28QLj07QFP_yPp35lSp72aXPbpfFGL_Wccl-l7C_hc">Arduino Nano</a> |
| Drivers de motor | Acionam os motores da CNC | <a href="https://www.eletrogate.com/cnc-shield-v4-para-arduino-nano?utm_source=Site&utm_medium=GoogleMerchant&utm_campaign=GoogleMerchant&srsltid=AU7gw4WofJhx-iAhHbC9jVka05pDxL8XJbis7FhIia1VyhvgEfCdAorm01s">CNC Shield Arduino</a> |
| Motores | Movimentam os eixos da CNC | <a href="https://www.mercadolivre.com.br/motor-de-passo-nema-23-toque-126kgf-28a-p-cnc-3gou/p/MLB2053967721?matt_tool=18956390&utm_source=google_shopping&utm_medium=organic&pdp_filters=item_id%3AMLB7712697988&from=gshop">3x Motor de passo 12V</a> |
| Fonte de alimentação | Alimenta a CNC e os motores | `Fonte 12V` |

## 🎬 Demonstração

>
> `docs/demo.mp4`

## 👥 Equipe

Projeto desenvolvido por estudantes de Informática, divididos em três frentes:

### 💻 Software
| Nome |
|------|
| Iago Diniz Sepini Nunes |
| Vinicius Yuji Ozawa |
| Marcos Dias Sepini |
| Augusto Gonçalves Lemos |

### 🔧 Hardware
| Nome |
|------|
| Davi Vinagre Dias |
| Thales Silva Garcia | 
| Mateus Gonçalves Tavares |

### 🎨 Design
| Nome |
|------|
| Higor Machado Miranda |
| João Gabriel Prado de Souza |
| Gustavo Porto Pereira|

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%">

## 🗺️ Roadmap

- [x] Módulo 1 — captura, contorno e SVG
- [ ] Módulo 2 — CNC redesenhando o traço
- [x] Módulo 3 — LLM + voz
- [ ] Módulo 4 — comandos *continuar* / *parar*
- [ ] Módulo 5 — rosto 3D reagindo à fala
- [ ] Integração completa dos módulos
- [ ] Suporte a outras máquinas além da CNC
