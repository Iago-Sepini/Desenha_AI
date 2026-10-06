# Histórico de commits

O que cada commit fez no projeto, quem fez e por quê. Os commits de correção
trazem também o **sintoma**, a **causa** e a **correção**, para que o problema
seja reconhecido rápido se voltar a aparecer.

A ordem é cronológica, dividida em fases. Novos commits entram no fim da fase
atual ou numa fase nova.

> Este arquivo substitui o antigo `docs/correcoes.md`. Todas as entradas dele
> continuam aqui, dentro do commit que fez cada correção.

---

## Quem fez o quê

| Autor no git | Frente | Principais contribuições |
|--------------|--------|--------------------------|
| **Iago** (aparece como `Iago Nunes`, `Iago Sepini` e `Iago-Sepini`; é a mesma pessoa, com o mesmo e-mail) | Software, líder | Estrutura inicial, README, voz com Piper, IA com a Groq, push-to-talk com Vosk, rosto em pygame, persona do Max, visão com 100+ classes do QuickDraw, listener com Whisper, integração da visão com a LLM, modos Livre e Desafio |
| **Japola** | Software, IA e voz | Branch `feat/llm-voz`: correções no fluxo da CNC, no histórico da LLM e no cache, seleção de microfone, troca da voz para "faber", imagens novas do rosto, `requirements.txt` com TensorFlow 2.20 e sem o `piper-tts` |
| **Marcos Dias Sepini** | Software, visão | Merge do PR #1 e módulo de visão (reconhecimento de desenhos pela câmera) |
| **Vinicius Ozawa** | Revisão | Merge dos PRs #2, #3 e #4 na `main` |

## Linha do tempo

| Data | Commit | Autor | Resumo |
|------|--------|-------|--------|
| 18/09 | `9363362` | Iago | Criação do repositório |
| 18/09 | `f7512b4` | Iago | `main.py` vazio |
| 19/09 | `a9086e3` | Iago | README completo do projeto |
| 19/09 | `ccebc98` | Iago | Ajuste do roadmap no README |
| 19/09 | `1008066` | Iago | Estrutura de pastas e `.env.example` |
| 19/09 | `1b44888` | Iago | Voz: Piper TTS e `Speaker` |
| 19/09 | `b6335d0` | Iago | IA: Groq, prompts, cache, estado e console |
| 23/09 | `2c6205e` | Iago | Push-to-talk com Vosk e marcadores da CNC |
| 23/09 | `1d3a602` | Japola | Início da branch `feat/llm-voz` |
| 23/09 | `3e4393e` | Japola | fix: `pynput` no `requirements.txt` |
| 23/09 | `aa391c1` | Japola | fix: lixo no prompt e import sem uso |
| 23/09 | `455d41a` | Japola | fix: confirmação da CNC era cortada |
| 23/09 | `b20f8e7` | Japola | fix: marcador da CNC fora do histórico |
| 23/09 | `e11a04b` | Japola | fix: nome antigo no cache |
| 23/09 | `f373537` | Japola | feat: seleção de microfone e 16 kHz |
| 24/09 | `6b82a33` | Iago | Rosto em pygame |
| 25/09 | `2aa43ad` | Iago | Persona brincalhona e menção ao líder |
| 27/09 | `28e6694` | Iago | Merge da `main` na `feat/llm-voz` |
| 28/09 | `25b16c9` | Marcos | Merge do PR #1 na `main` |
| 29/09 | `84ab4c4` | Marcos | Módulo de visão |
| 30/09 | `89a0347` | Japola | docs: este histórico de commits |
| 30/09 | `9a205a2` | Vinicius Ozawa | Merge do PR #2 na `main` |
| 30/09 | `7b82f19` | Japola | fix: dois loops de console e dois `Listener` |
| 30/09 | `46e5d4f` | Japola | fix: fala e console chamavam a LLM ao mesmo tempo |
| 30/09 | `1407715` | Japola | fix: recria o `.env.example` |
| 30/09 | `9077b04` | Japola | fix: "naturally" e gênero trocado no prompt |
| 30/09 | `efd5921` | Japola | docs: correções da integração neste histórico |
| 30/09 | `c95551f` | Vinicius Ozawa | Merge do PR #3 na `main` |
| 01/10 | `e45fc62` | Japola | feat: voz do Piper trocada de "jeff" para "faber" |
| 01/10 | `9c84e37` | Vinicius Ozawa | Merge do PR #4 na `main` |
| 01/10 | `1764e51` | Japola | docs: troca da voz neste histórico |
| 01/10 | `5aadeb9` | Japola | Merge da `docs/historico-voz-faber` na `main` |
| 01/10 | `fe46ad8` | Japola | feat: imagens novas do rosto |
| 02/10 | `eafb490` | Iago | Visão num programa só (`vision/main.py`) |
| 02/10 | `3dcadae` | Iago | Primeiro `model.h5` e `classes.json`, Keras direto |
| 02/10 | `7a5a9c0` | Iago | `.gitignore`: `.npy` vira `*.npy` |
| 02/10 | `d20f1f2` | Iago | Visão com 100 classes e tela cheia |
| 02/10 | `58004c2` | Iago | Listener com Groq Whisper |
| 02/10 | `4b54f30` | Iago | Lista de classes do QuickDraw em português |
| 03/10 | `88eac6c` | Iago | Modelos do hardware no README |
| 03/10 | `8722ab4` | Iago | Rosto abre direto no segundo monitor |
| 03/10 | `631d058` | Iago | Visão integrada à LLM, modos Livre e Desafio |
| 03/10 | `d1de809` | Iago | Roadmap: Módulos 1 e 3 concluídos |
| 03/10 | `d72c029` | Iago | Corrige o selo de último update do README |
| 04/10 | `e552817` | Iago | Frase "desafio" inicia o modo Desafio |
| 06/10 | `334c64b` | Japola | fix: TensorFlow 2.20, Keras 3.12 e sem `piper-tts` |

### Como as branches se juntaram

```
main         9363362 ... 2c6205e ──┬── 6b82a33 ── 2aa43ad ──────────────┬── 25b16c9 ── 84ab4c4
                                   │   (rosto)                          │   (PR #1)     (visão)
feat/llm-voz                       └── 1d3a602 ... f373537 ── 28e6694 ──┘
                                       (correções e microfone)  (merge)
```

A `feat/llm-voz` saiu do commit `2c6205e`. Enquanto ela recebia as correções, a
`main` recebeu o rosto. As duas se encontraram no merge `28e6694`.

---

## Fase 1: início do repositório

### `9363362` · Initial commit

**Iago** · 18/09/2026

Repositório criado pelo GitHub com `.gitignore` de Python, licença MIT e um
README de duas linhas.

### `f7512b4` · Create main.py

**Iago** · 18/09/2026

Cria o `main.py` vazio, só para reservar o ponto de entrada.

### `a9086e3` · Revise README with project details and structure

**Iago** · 19/09/2026

Escreve o README do projeto: objetivo, os cinco módulos (visão, CNC, LLM com
voz, controle por voz e rosto), o diagrama do fluxo, as tecnologias, a
estrutura de pastas, como executar, a lista de hardware e a equipe.

### `ccebc98` · Update roadmap and remove unnecessary text

**Iago** · 19/09/2026

Enxuga o roadmap do README.

### `1008066` · first Structure

**Iago** · 19/09/2026

Cria o esqueleto das pastas com arquivos vazios (`ai/llm.py`, `ai/prompts.py`,
`config.py`, `voice/listener.py`, `voice/tts.py`) e adiciona:

- `.env.example` com `GROQ_API_KEY`, `GROQ_MODEL`, `CAMERA_INDEX`,
  `SERIAL_PORT`, `SERIAL_BAUD` e `PIPER_VOICE`;
- `requirements.txt` com as dependências previstas para todos os módulos;
- `docs/cncBefore.jpeg`, foto da CNC antes do reaproveitamento;
- `modelos3D/exemplo.stl`, modelo 3D de exemplo.

---

## Fase 2: voz e IA

### `1b44888` · piper init

**Iago** · 19/09/2026

Implementa a fala do assistente:

- `voice/tts.py`: classe `PiperTTS`, que chama o `piper.exe` e devolve o áudio
  como array. Corta o silêncio do começo e do fim e encurta pausas longas.
- `voice/speaker.py`: classe `Speaker`, que fala frase por frase. Sintetiza
  todas as frases adiantado em segundo plano e permite pausar, continuar e
  cancelar. Avisa o estado (`falando`, `pausado`, `parado`) por callback.
- `voice/text_utils.py`: remove links, markdown e emojis antes da fala e divide
  o texto em frases de tamanho bom para a entonação.
- `voice/demo_tts.py`: teste da voz com pausa e retomada.
- Binários do Piper para Windows (`voice/piper/`, por isso o pacote
  `piper-tts` do pip nunca foi necessário; ver `334c64b`) e a voz em português
  `voice/models/br.onnx`, de cerca de 63 MB (dataset "jeff", trocado pelo
  "faber" em `e45fc62`).
- `config.py` com os caminhos do Piper.
- `vision/camera.py` vazio, reservado para a visão.

### `b6335d0` · llm

**Iago** · 19/09/2026

Implementa a IA:

- `ai/llm.py`: classe `GroqLLM`, que conversa com a Groq guardando o histórico
  de um visitante (até 20 mensagens). `chat()` responde falas e avisos,
  `describe()` descreve um desenho e `reset()` zera a conversa para o próximo
  visitante. Se a API falhar, `describe()` usa a resposta guardada em
  `data/cache/respostas.json` como plano B.
- `ai/prompts.py`: a persona do assistente para a feira de ciências e os avisos
  `[SISTEMA]` que simulam os outros módulos.
- `server/state.py`: classe `State`, que guarda o estado atual (`parado`,
  `pensando`, `falando` etc.) e avisa quem estiver inscrito.
- `main.py`: console que simula os outros módulos com `/desenho`,
  `/naoidentificado`, `/cnc inicio`, `/cnc fim` e `/novo`.
- `config.py`: chave, modelo (`openai/gpt-oss-120b`) e timeout da Groq.

---

## Fase 3: push-to-talk e CNC

### `2c6205e` · implementacao voz ai

**Iago** · 23/09/2026

- `voice/listener.py`: classe `Listener`, push-to-talk com Vosk. Grava enquanto
  a barra de espaço estiver apertada, normaliza o volume e transcreve.
- O assistente passa a se chamar **Max** (antes era Jubiscreudo).
- `REGRAS_DE_CONTROLE` entra no `SYSTEM_PROMPT`: a IA escreve `[[CNC_SIM]]` ou
  `[[CNC_NAO]]` quando o visitante responde se quer ver a máquina desenhar.
- `ai/llm.py` passa a devolver `(texto, comando)`, e o `main.py` encadeia o
  aviso "a CNC começou" quando o comando é `CNC_SIM`.

**Efeitos colaterais**, corrigidos depois ou ainda em aberto:

- o histórico da LLM guardava o texto com o marcador (corrigido em `b20f8e7`);
- a confirmação da CNC era cancelada antes de ser falada (corrigido em `455d41a`);
- entrou um `z` perdido no prompt (corrigido em `aa391c1` e em `2aa43ad`);
- a palavra "naturalmente" virou **"naturally"** no prompt (ainda em aberto).

---

## Fase 4: branch `feat/llm-voz`

### `1d3a602` · init branch feat/llm-voz

**Japola** · 23/09/2026

Abre a branch de trabalho da IA e da voz. O commit **apaga o `.env.example`**.
Desde então, o README e a mensagem de erro do `ai/llm.py` mandam copiar um
arquivo que não existe mais (ainda em aberto).

### `3e4393e` · fix: corrigido erro de import do pynput

**Japola** · 23/09/2026

**Sintoma:** o programa não abria, com `ModuleNotFoundError: pynput`.
**Causa:** o `listener.py` usa o `pynput` para ler a barra de espaço, mas ele
não estava no `requirements.txt`.
**Correção:** `pynput` adicionado ao `requirements.txt`.

### `aa391c1` · fix: correção dentro do prompt e llm com import sem usar

**Japola** · 23/09/2026

Remove o `z` perdido que tinha entrado no meio do prompt e o `import re` sem uso
do `ai/llm.py`.

### `455d41a` · fix: confirmação da CNC era cortada antes de ser falada

**Japola** · 23/09/2026 · `main.py`

#### Sintoma

A criança dizia "sim, quero" e ouvia **silêncio total**. O assistente só voltava a
falar 1 a 2 segundos depois, já sobre o processo da CNC. A resposta de confirmação
aparecia no terminal com `[IA]` mas nunca chegava à caixa de som.

Parecia que o programa tinha travado no momento mais importante da demonstração.

#### Causa

Dentro de `responder()`:

```python
speaker.say(texto)                      # começa a falar a confirmação

if comando == "CNC_SIM":
    conversar(EVENTO_CNC_INICIOU)       # -> responder() -> speaker.cancel()
```

O `speaker.say()` **não bloqueia** — só dispara uma thread e retorna na hora. E o
`responder()` começa com `speaker.cancel()`. O intervalo entre começar a falar e
cancelar era de microssegundos, antes de o Piper terminar de sintetizar a primeira
frase. O áudio nem chegava a existir.

#### Correção

`speaker.wait()` antes de encadear o evento, para a confirmação terminar de ser
falada.

#### Efeito colateral aceito

Durante os segundos da confirmação a thread que chamou fica bloqueada: o `>` do
terminal não volta e o push-to-talk não responde. E se alguém disser "parar" nesse
intervalo, o `wait()` só retorna quando disserem "continuar" — o `Speaker.wait()`
não tem timeout.

### `b20f8e7` · fix: marcador da CNC não entra mais no histórico da conversa

**Japola** · 23/09/2026 · `ai/llm.py`

#### Sintoma

A CNC podia disparar **sozinha**, sem ninguém ter autorizado, depois de algumas
trocas de conversa.

#### Causa

Em `_enviar()`, o texto guardado no histórico como resposta do assistant era o
texto **cru**, ainda com o marcador `[[CNC_SIM]]` dentro:

```python
self.history.append({"role": "assistant", "content": texto})  # cru
```

O texto limpo ia para a voz, mas o sujo ficava no contexto. Nas rodadas seguintes
o modelo via que ele mesmo tinha escrito `[[CNC_SIM]]` antes, e isso funciona como
exemplo — ele passava a repetir o marcador fora de hora. Como o `main.py` trata o
marcador como autorização do visitante, a máquina ligava no meio da conversa.

O prompt pede para não repetir o marcador (`REGRAS_DE_CONTROLE`, em
`ai/prompts.py`), mas exemplo no histórico costuma ganhar de instrução.

#### Correção

`_enviar()` agora processa a resposta antes de guardar, e devolve
`(texto limpo, comando)`. O histórico nunca vê marcador. O `_save_cache()` também
passou a gravar o texto limpo.

Este commit também criou o antigo `docs/correcoes.md`, que deu origem a este
arquivo.

#### Atenção

Quem mexer aqui pode "simplificar" de volta para guardar o texto cru, porque
parece mais fiel. Não é: o histórico tem que ficar limpo. O caminho do comando é
o valor de retorno, não o histórico.

Se o sintoma voltar, quem estiver no Arduino vai procurar o erro no código serial
— e a causa está no `ai/llm.py`.

### `e11a04b` · fix: cache guardava o nome antigo do assistente

**Japola** · 23/09/2026 · `data/cache/respostas.json`

#### Sintoma

Com a Groq fora do ar, o plano B entrava e o assistente se apresentava como
**Iago** — nome antigo do projeto. Hoje ele se chama Max (`NOME_ASSISTENTE`, em
`ai/prompts.py`).

Só acontece quando a API falha, então passa despercebido em teste normal e
aparece justo na feira, se a internet cair.

#### Causa

As respostas foram gravadas quando o assistente ainda se chamava Iago. O cache
guarda o **texto pronto**, então não acompanha mudanças no prompt.

Havia também uma entrada `"bob_esponja"` (com underline) cujo conteúdo era a
resposta de "não entendi seu desenho" — um plano B que já nascia falhando. Repare
que ela convivia com `"bob esponja"` (com espaço): o `_key()` normaliza espaços,
mas underline não é espaço, então as duas são chaves diferentes.

#### Correção

Nome atualizado nas três entradas que o citavam, e a entrada `"bob_esponja"`
removida. O conteúdo das demais foi preservado em vez de apagar o arquivo, para
não ficar sem plano B nenhum.

#### Atenção

O cache não se atualiza sozinho quando o prompt muda. Ao mexer no
`ai/prompts.py` — principalmente em nome, tom ou regras de apresentação — vale
conferir se as respostas guardadas ainda combinam.

Vale também para o Módulo 1: se a visão devolver rótulos com underline
(`bob_esponja`), eles viram chaves separadas das com espaço e o cache racha em
duas entradas para o mesmo desenho.

### `f373537` · feat: seleção de microfone e gravação direto em 16 kHz

**Japola** · 23/09/2026 · `voice/listener.py`, `config.py`, `main.py`

#### Sintoma

O Vosk captava mal a fala, de forma intermitente. Palavras parecidas eram
confundidas, principalmente as que têm **s, ch, x, z**.

#### Causa

Duas coisas somadas.

**1. A taxa que o Windows informa não é confiável.** O `listener.py` lia
`sd.query_devices(kind='input')['default_samplerate']` e gravava nessa taxa. Só
que esse valor vem da API MME, que devolve **44100 para todos os aparelhos** por
ser um valor genérico. A taxa real aparece nas APIs nativas. Medido nesta
máquina, no mesmo microfone embutido:

```
MME    diz: 44100 Hz     <- o que o código lia
WASAPI diz: 48000 Hz     <- a taxa real
```

Resultado: gravava-se numa taxa que não era a do aparelho, e depois reduzia-se
para os 16000 Hz do Vosk com `np.interp`, **sem filtro passa-baixa**. Sem esse
filtro, as frequências acima de 8 kHz dobram para dentro da banda da voz — e quem
mais sofre são os sibilantes. Dois resamples para voltar ao ponto de partida, o
segundo deles adicionando distorção.

**2. Não havia como escolher o microfone.** Usava-se sempre o padrão do sistema,
sem forma de testar ou trocar.

#### Correção

Em vez de adivinhar a taxa, o aparelho é aberto **direto em 16000 Hz**, que é a
que o Vosk exige — assim não há reamostragem nenhuma. Se o aparelho recusar,
`_abrir_stream()` tenta a taxa informada, 48000 e 44100, nessa ordem, e só então
o resample antigo entra em ação.

Para escolher o microfone:

| Onde | Como |
|------|------|
| `.env` | `MIC_DEVICE=QCY` ou `MIC_DEVICE=14` (vazio = padrão do sistema) |
| No programa | `/mics` lista e testa, `/mic <n\|nome>` troca, `/mic` mostra o atual |

O `/mics` não confia no valor informado: abre cada aparelho de verdade e marca
`16k ok` ou `16k nao`. Prefira sempre os `16k ok`.

Trocar não exige reiniciar: o aparelho só é aberto no instante da gravação, então
o próximo aperto da barra de espaço já usa o novo.

O nome é aceito além do índice porque o índice **muda de posição** quando se liga
ou desliga um dispositivo — `MIC_DEVICE=14` pode virar outro aparelho no dia
seguinte.

#### Ainda em aberto

Outros três problemas de captação foram diagnosticados e **deixados para depois**:

1. **Normalização pelo pico** (`listener.py`, no `_on_release`): o clique da barra
   de espaço vira um pico maior que a voz, e o `24000 / max_volume` reduz a fala
   junto, deixando-a quase inaudível para o Vosk. Intermitente por natureza —
   depende de bater ou acariciar a tecla. Piora com microfone embutido, que fica
   no mesmo chassi do teclado. Correção: normalizar por RMS.
2. **Primeira sílaba cortada**: o aviso "A escutar" é impresso *antes* de abrir o
   stream, que leva de 25 a 138 ms. Perde-se o início de "sim" ou "parar".
3. **Barra de espaço é hook global**: ao digitar `/desenho bob esponja` no
   terminal, cada espaço inicia e para uma gravação.

#### Sobre o hardware

Fone Bluetooth é o pior caso para reconhecimento de voz. O perfil alterna entre
A2DP (tocar o Piper) e HFP (microfone), e o Windows renegocia a cada troca —
durante a renegociação o áudio simplesmente cai. É a causa mais provável da
intermitência que não vem do código. Microfone direcional com fio resolve isso e
ainda ajuda com o ruído da feira.

---

## Fase 5: rosto (na `main`)

### `6b82a33` · introduce face

**Iago** · 24/09/2026

- `face/face.py`: classe `Face`, janela em pygame com os olhos do Max. Pisca
  sozinha a cada 3 a 6 segundos, aceita redimensionar, F11 alterna a tela cheia
  e ESC sai.
- Imagens em `face/assets/` (olhos abertos, olhos fechados e `cncAtiva.png`,
  ainda não usada) e cópias em `docs/`.
- `main.py`: o pygame exige a thread principal, então o console foi para uma
  thread separada (`loop_console`) e o `face.run()` passou a bloquear o `main()`.
- Prompt: se perguntarem quem vai ganhar a feira, o Max responde que é o Desenha AI.

O rosto ainda não reage à fala: ele não está inscrito no `State`.

### `2aa43ad` · Update prompts.py

**Iago** · 25/09/2026

- O Max fica brincalhão e solta piadinhas leves.
- O prompt passa a citar o Iago como líder do grupo.
- Remove o `z` perdido do prompt (a mesma correção do `aa391c1`, feita na `main`).

---

## Fase 6: integração

### `28e6694` · Merge branch 'main' into feat/llm-voz

**Iago** · 27/09/2026

Traz o rosto da `main` para dentro da `feat/llm-voz`.

O conflito no `main.py` foi resolvido **mantendo os dois lados**. O arquivo
ficou com o loop de console antigo (com `/mics` e `/mic`) e o `loop_console`
novo, um depois do outro. Consequências, ainda em aberto:

- a janela do rosto é criada, mas só é desenhada depois que alguém digita
  `sair` no primeiro loop. Até lá o Windows mostra "Não está respondendo";
- depois do `sair`, um **segundo `Listener`** é criado sem parar o primeiro, e
  sem o `MIC_DEVICE`. Cada aperto da barra de espaço grava duas vezes e chama a
  LLM duas vezes;
- o `loop_console` não tem os comandos `/mics` e `/mic`.

### `25b16c9` · Merge pull request #1 from Iago-Sepini/feat/llm-voz

**Marcos Dias Sepini** · 28/09/2026

Leva a `feat/llm-voz` (correções da CNC, do histórico e do cache, e a seleção de
microfone) para a `main`, junto com o `main.py` do merge anterior.

---

## Fase 7: visão

### `84ab4c4` · Add files via upload

**Marcos Dias Sepini** · 29/09/2026

Primeira versão do Módulo 1, enviada pela interface do GitHub. Roda separado do
`main.py`, que ainda não chama a visão.

- `vision/train.py`: baixa 9 classes do Google QuickDraw (bola, guarda-chuva,
  cachorro, gato, casa, carro, sol, maçã e peixe), 5000 desenhos de cada, e
  treina uma rede neural pequena com bitmaps 28x28. Gera `model.h5` e
  `classes.json`.
- `vision/camera.py`: reconhece o desenho pela câmera, 100% local. Recorta o
  quadrado do meio da imagem, separa a tinta do papel, centraliza, engrossa o
  traço como no QuickDraw e reduz para 28x28. Faz a média das últimas 6
  previsões e mostra `?` abaixo de 55% de confiança. Teclas: `q` sai, `m`
  espelha, `+` e `-` mudam o tamanho do quadrado.
- `vision/bibliotecas.txt`: instalação com Python 3.11, `numpy 1.26.4`,
  `tensorflow 2.15.0`, `opencv-python 4.9.0.80` e `tensorflowjs 4.17.0`.

Pontos de atenção:

- `model.h5` e `classes.json` não estão no repositório. É preciso rodar o
  `train.py` antes, na mesma pasta de onde se roda o `camera.py`;
- a docstring do `train.py` ainda fala em exportar para TensorFlow.js e servir
  com `http.server`, restos de uma versão para o navegador;
- o `train.py` cria uma pasta `data/` relativa à pasta atual. Rodado da raiz do
  projeto, ele mistura os arquivos do QuickDraw com o `data/` do cache da LLM;
- os rótulos que a visão devolve precisam casar com as chaves do cache (ver a
  atenção do `e11a04b`).

---

## Fase 8: documentação e correções da integração

### `89a0347` · docs: transforma o registro de correções em histórico de commits

**Japola** · 30/09/2026

Transforma o antigo `docs/correcoes.md` neste arquivo. Entrou na `main` pelo
PR #2 (`9a205a2`, merge de **Vinicius Ozawa**).

### `7b82f19` · fix: main.py tinha dois loops de console e dois Listener

**Japola** · 30/09/2026 · `main.py`

#### Sintoma

A janela do rosto abria e ficava "Não está respondendo". Depois de digitar
`sair`, o rosto voltava, mas cada aperto da barra de espaço gravava duas vezes e
o Max respondia duas vezes à mesma fala. E `/mics` e `/mic` paravam de funcionar.

#### Causa

O merge `28e6694` manteve os dois lados do conflito no `main.py`. O loop antigo
rodava na thread principal e prendia o programa antes do `face.run()`. Quando
ele terminava, um segundo `Listener` era criado sem parar o primeiro e sem o
`MIC_DEVICE`, e começava o `loop_console` novo, que não tinha os comandos do
microfone.

#### Correção

Um único `loop_console`, com todos os comandos, e um único `Listener`, criado
com `config.MIC_DEVICE`. O `face.run()` volta a ocupar a thread principal logo
no início.

#### Atenção

Ao resolver conflito no `main.py`, não mantenha os dois lados. O pygame precisa
da thread principal: todo loop de console tem que ir para dentro do
`loop_console`.

### `46e5d4f` · fix: fala e console chamavam a LLM ao mesmo tempo

**Japola** · 30/09/2026 · `main.py`, `voice/listener.py`

#### Sintoma

Se alguém falasse pelo push-to-talk enquanto uma pergunta digitada ainda
esperava a Groq, as respostas podiam sair trocadas ou fora de contexto. E,
enquanto a IA pensava, o teclado podia ficar lento.

#### Causa

O console e o push-to-talk rodam em threads diferentes e os dois chamam
`responder()`, sem nenhuma trava. As duas chamadas mexiam no `llm.history` ao
mesmo tempo.

A transcrição do Vosk e a resposta da IA também rodavam dentro do callback do
`pynput` (`_on_release`), o que segurava o hook do teclado por vários segundos.

#### Correção

- `main.py`: `responder()` e `novo_visitante()` rodam dentro de um
  `threading.RLock`. Uma pergunta que chega durante outra espera a vez.
- `voice/listener.py`: `_on_release()` só fecha o microfone e entrega o áudio a
  uma thread nova (`_transcrever`). O áudio e a taxa são copiados antes, porque
  uma nova gravação ou um `/mic` podem trocá-los enquanto a thread trabalha.

#### Atenção

Tem que ser `RLock`, não `Lock`: o `CNC_SIM` chama `responder()` de novo, de
dentro dela. Com um `Lock` comum, o programa trava para sempre justo quando o
visitante aceita ver a máquina desenhar.

### `1407715` · fix: recria o .env.example

**Japola** · 30/09/2026 · `.env.example`

O `1d3a602` apagou o arquivo, mas o README e o `ai/llm.py` continuavam mandando
copiá-lo. Ele volta só com o que o `config.py` lê hoje: `GROQ_API_KEY` e
`MIC_DEVICE`. As variáveis antigas (`CAMERA_INDEX`, `SERIAL_PORT`,
`SERIAL_BAUD`, `PIPER_VOICE` e `GROQ_MODEL`) ficaram de fora porque nenhum
código as usa. Quando a visão e a CNC passarem a ler alguma delas, ela volta
junto.

### `9077b04` · fix: "naturally" em inglês e gênero trocado no prompt do Max

**Japola** · 30/09/2026 · `ai/prompts.py`

- "naturally" volta a ser "naturalmente" (a troca veio do `2c6205e`).
- "criada" e "Seja honesta" passam para o masculino, como o resto da persona
  ("o Max", "brincalhão"), para o modelo não alternar o gênero ao falar de si.
- A regra do campeão da feira ganha acento e pontuação.
- Duas linhas só com espaços viram uma linha vazia.

Nenhuma regra de comportamento mudou. O cache não precisou ser refeito: nenhuma
resposta guardada fala do Max no feminino.

### `efd5921` · docs: registra as correções da integração no histórico de commits

**Japola** · 30/09/2026

Registra neste arquivo os commits `7b82f19`, `46e5d4f`, `1407715` e `9077b04`.
Os quatro entraram na `main` pelo PR #3 (`c95551f`, merge de **Vinicius
Ozawa**).

---

## Fase 9: voz nova

### `e45fc62` · feat: troca a voz do Piper de jeff para faber

**Japola** · 01/10/2026 · `voice/models/br.onnx`, `voice/models/br.onnx.json`

Troca a voz pt-BR do Max, que era do dataset "jeff" (desde o `1b44888`), pela do
dataset "faber", mais natural.

- `br.onnx`: o modelo novo, com cerca de 63 MB, o mesmo tamanho do anterior.
- `br.onnx.json`: a configuração do modelo novo.
  - ganha `phoneme_map` (`c` → `k`) e `speaker_id_map`;
  - o `phoneme_id_map` vai até o id 151 (o do "jeff" ia até o 160);
  - `piper_version` passa de 1.3.0 para 1.0.0, a versão com que o "faber" foi
    treinado;
  - os parâmetros de inferência continuam iguais (`noise_scale` 0.667,
    `length_scale` 1, `noise_w` 0.8).

Os nomes dos arquivos não mudaram, então o `config.py` e o `voice/tts.py`
continuam funcionando sem alteração. Entrou na `main` pelo PR #4 (`9c84e37`,
merge de **Vinicius Ozawa**).

#### Atenção

O `.onnx` e o `.json` andam juntos. Trocar só um dos dois faz o Piper ler os
fonemas com a tabela errada: a fala sai embolada ou o Piper falha ao abrir o
modelo.

O GitHub avisou no push que o `br.onnx` passa de 50 MB, o limite recomendado.
Cada troca de voz soma mais cerca de 60 MB ao histórico do repositório, e o
`git clone` fica mais lento para todo mundo. Se a voz for trocada de novo,
vale passar os `.onnx` para o Git LFS antes.

### `1764e51` · docs: registra a troca da voz para faber no histórico de commits

**Japola** · 01/10/2026

Registra o `e45fc62` neste arquivo. Entrou na `main` pelo merge `5aadeb9`, da
branch `docs/historico-voz-faber`.

### `fe46ad8` · feat: imagem do visor atualizado

**Japola** · 01/10/2026 · `face/assets/`, `docs/`

- `olhos_abertos.png` e `olhos_fechados.png` trocados pelos desenhos novos dos
  olhos do Max.
- Entra o `pensando.png`, para o rosto mostrar quando a IA estiver pensando. Ainda
  não é usado no código.
- Sai o `cncAtiva.png`, que nunca foi usado, e saem as cópias das imagens que
  estavam em `docs/`.

---

## Fase 10: visão com o QuickDraw

Commits enviados direto na `main`, sem PR.

### `eafb490` · mudança nos arquivos da visão

**Iago** · 02/10/2026 · `vision/main.py`, `vision/camera.py`, `face/face.py`

- `vision/main.py` (novo): junta o treino (`train.py`) e a câmera
  (`camera.py`) num programa só. Treina se ainda não existir `model.h5` e depois
  abre a câmera. Opções `--treinar`, `--camera`, `--sem-camera`, `--web` e
  `--cam <n>`. Teclas novas na câmera: `d` (debug), `c` (contornos) e `s` (salva
  um print).
- `vision/camera.py`: desenha os contornos na tela, mostra o FPS e uma janela
  de debug, e escreve o resultado no terminal só quando ele muda e fica estável.
- `face/face.py`: a piscada passa de 150 para 210 ms.

### `3dcadae` · feat: teste visão

**Iago** · 02/10/2026

- Primeiro `model.h5` (cerca de 700 KB) e `classes.json` no repositório, com as
  9 classes do `84ab4c4`. Resolve a pendência de ter que treinar antes de testar.
- `vision/main.py` e `vision/train.py` passam a importar o `keras` direto, em vez
  de `tensorflow.keras`.
- `.gitignore` ganha `.npy`, para não subir os desenhos baixados do QuickDraw.

### `7a5a9c0` · Update .gitignore

**Iago** · 02/10/2026

Corrige o `.npy` do commit anterior para `*.npy`. Sem o `*`, o Git só ignorava
um arquivo chamado exatamente `.npy`, e os desenhos baixados apareciam como
arquivos novos.

### `d20f1f2` · update Model

**Iago** · 02/10/2026 · `vision/main.py`, `model.h5`, `requirements.txt`

- `vision/main.py` passa a treinar até 100 classes do QuickDraw e abre a câmera
  em tela cheia. `+` e `-` passam a mudar a sensibilidade da detecção de tinta,
  em vez do tamanho do quadrado.
- `model.h5` retreinado (mesmo tamanho do anterior).
- `requirements.txt` ganha `tensorflow`, `tensorflowjs` e `scikit-learn`, ainda
  sem versão fixa.

### `58004c2` · feat: import Whisper

**Iago** · 02/10/2026

- `voice/listener_Whisper.py` (novo): o mesmo push-to-talk do
  `voice/listener.py`, mas transcreve com o modelo `whisper-large-v3-turbo` da
  Groq em vez do Vosk. A seleção de microfone e o teste de 16 kHz do `f373537`
  foram mantidos. Precisa da `GROQ_API_KEY` e de internet.
- Apaga o `voice/demo_tts.py` (teste da voz do `1b44888`).
- Apaga o `vision/bibliotecas.txt`. As versões que ele pedia (`numpy 1.26.4`,
  `tensorflow 2.15.0`, `opencv-python 4.9.0.80`) foram depois para o
  `requirements.txt` no `631d058`.
- README: Thales Silva Garcia vai para o Hardware e Gustavo Porto Pereira para
  o Design.

O `main.py` continua usando o `voice/listener.py` (Vosk). O Whisper fica como
alternativa, ainda sem forma de escolher entre os dois.

### `4b54f30` · o

**Iago** · 02/10/2026 · `vision/classes_quickdraw.py`, `vision/main.py`

- `vision/classes_quickdraw.py` (novo): as 342 categorias do QuickDraw com o
  nome em português (`"apple": "maçã"`), mais as listas menores usadas no
  treino.
- `vision/main.py` passa a ler as classes desse arquivo.
- Apaga o `classes.json` do `3dcadae` (volta no `631d058`).

### `88eac6c` · Specify models in requirements section of README

**Iago** · 03/10/2026 · `README.md`

Preenche a tabela de hardware do README: câmera USB C72, caixa de som
Bluetooth, display HDMI de 5 polegadas, Arduino Nano, CNC Shield, 3 motores de
passo de 12 V e fonte de 12 V. Saem as linhas "Computador" e "Caneta e
suporte".

### `8722ab4` · Update face.py

**Iago** · 03/10/2026 · `face/face.py`

- O rosto abre **direto no segundo monitor** (`display_index=1`), sem borda e
  no tamanho da tela. Se só houver um monitor, usa o principal.
- Desliga a escala de DPI do Windows, que deixava a imagem borrada e fora do
  lugar.
- Saem o F11 e o redimensionamento da janela; ESC fecha.
- Dá para testar o rosto sozinho com `python face/face.py`.

---

## Fase 11: visão integrada e modos de jogo

### `631d058` · feat(core): integra modelo QuickDraw e conecta com a LLM

**Iago** · 03/10/2026

O maior commit até aqui (23 arquivos). A visão deixa de ser um programa
separado e passa a rodar dentro do `main.py`.

**Visão** (`vision/`):

- `treinar.py` substitui o `train.py`. Escolhe o tamanho do treino com
  `--classes basico` (9), `medio` (cerca de 71) ou todas (342), ou
  `--escolher "cat,dog"`. Gera `model.h5` e `classes.json` juntos.
- `detector.py` substitui o `camera.py`: classe `Detector`, que recebe o recorte
  da câmera e devolve nome, confiança, as 5 melhores apostas e os contornos.
- `config_camera.py`: abre a câmera com as opções do `camera_config.json`
  (índice, resolução, espelhar, tamanho do quadrado). `--listar` mostra as
  câmeras e `--testar` abre um preview para ajustar e salvar.
- `watcher.py`: classe `DrawingWatcher`, que roda a câmera e o detector em
  segundo plano e mostra uma janela com o que está sendo reconhecido. **Não**
  avisa o Max sozinho: só manda o desenho quando alguém chama `confirmar()`.
- `svg_export.py`: salva os contornos do desenho em `desenho.svg`, para a CNC.
- Apaga o `vision/main.py`.
- `model.h5` retreinado (cerca de 8,9 MB) e `classes.json` de volta, com as 9
  classes básicas.

**Modos de jogo** (`ui/manager.py`, `server/state.py`, `ai/prompts.py`):

- **Modo Livre**: o visitante desenha no tempo dele. Quando ele diz que
  terminou, a IA escreve `[[CONFIRMAR_DESENHO]]` e o `main.py` pede o desenho ao
  `DrawingWatcher`. O Max comenta o desenho e oferece a CNC.
- **Modo Desafio**: é sorteada uma palavra de `PALAVRAS_DESAFIO` e o visitante
  tem 30 segundos para desenhar, com cronômetro na tela e bipe no fim. Depois
  ele diz "pronto" e o Max diz se acertou. A CNC não é oferecida.
- Marcadores novos: `[[CONFIRMAR_DESENHO]]`, `[[DESAFIO_SIM]]` e
  `[[DESAFIO_NAO]]`. Avisos novos: início do desafio e resultado do desafio.
- `State` ganha `modo`, `palavra_sorteada`, `desafio_em_andamento`,
  `tempo_restante` e `aguardando_posicionamento`.
- Comandos novos no console: `/modo livre` e `/desafio`. Por voz: "modo
  desafio", "modo livre", "pronto" etc.

**Interface** (`ui/`):

- `face/` vira `ui/`. O `ui/face.py` recebe o `State` e desenha por cima dos
  olhos o cronômetro e a palavra do desafio.
- `ui/dialogs.py`: antes de ligar a CNC aparece uma janela de **confirmação do
  operador**. Se ele cancelar, o Max avisa o visitante.

**Outros:**

- `requirements.txt` com versões fixas e Python 3.10. Trazia
  `tensorflow==2.15.0` e `piper-tts==1.2.0` (os dois mudam no `334c64b`).
- O prompt foi encurtado: saíram as dicas de como desenhar e várias regras de
  cuidado ficaram mais curtas.
- Cache com respostas novas para `gato`, `cachorro`, `sol` e `carro`, e a de
  `casa` reescrita.
- `.gitignore` ganha `*desenho.svg`.

#### Atenção

- O `responder()` do `main.py` agora procura os marcadores no texto **e** no
  `comando`. Ao criar um marcador novo, ele tem que entrar nas duas listas (a
  que detecta e a que limpa), senão o Max lê o marcador em voz alta.
- O `ui/manager.py` usa `winsound`, que só existe no Windows.
- O `watcher.py` procura `model.h5` e `classes.json` na pasta de onde o
  programa é rodado. Rode sempre da raiz do projeto.

### `d1de809` · Update roadmap with completed modules

**Iago** · 03/10/2026

Marca no roadmap do README os Módulos 1 (visão) e 3 (LLM e voz) como
concluídos.

### `d72c029` · Update README.md

**Iago** · 03/10/2026

O selo "Último update" do README apontava para o repositório
`Desenha_AI_IA`, que não existe. Passa a apontar para `Desenha_AI`.

### `e552817` · Update main.py

**Iago** · 04/10/2026 · `main.py`

Em `FRASES_DESAFIO`, "vamos jogar" vira "desafio". Assim, qualquer fala com a
palavra "desafio" inicia o Modo Desafio.

#### Efeito colateral (ainda em aberto)

O `comando_voz()` testa `FRASES_DESAFIO` **antes** de `FRASES_LIVRE`. Como
"cancelar desafio" contém "desafio", dizer isso **começa um desafio novo** em
vez de voltar ao Modo Livre. O mesmo vale para "não quero outro desafio": a fala
nem chega à LLM. Correção sugerida: testar `FRASES_LIVRE` primeiro.

---

## Fase 12: dependências

### `334c64b` · fix: requirements com TensorFlow 2.20, Keras 3.12 e sem o piper-tts

**Japola** · 06/10/2026 · `requirements.txt`

#### Sintoma

O `requirements.txt` não montava o ambiente que o projeto usa de verdade no
Windows: o `.venv` que roda o projeto tinha outro TensorFlow e não tinha o
`piper-tts`.

#### Causa

Duas linhas do `631d058`:

1. **`piper-tts==1.2.0`**: depende do `piper-phonemize`, que não tem instalador
   para Windows, e por isso o `pip` falha. E o pacote nem é usado: desde o
   `1b44888` a voz chama o **executável** `voice/piper/piper.exe`, que já vem no
   repositório com as DLLs e o `espeak-ng-data` (ver `voice/tts.py` e
   `config.PIPER_EXE`).
2. **`tensorflow==2.15.0`**: traz o Keras 2, mas o código importa o `keras`
   direto (desde o `3dcadae`), e o `model.h5` foi salvo com o Keras 3.12.4
   (está gravado no próprio arquivo).

#### Correção

- `piper-tts` removido. **A voz continua sendo o Piper**: só o pacote do pip
  saiu, o `piper.exe` e o modelo `voice/models/br.onnx` continuam iguais.
- `tensorflow==2.20.0` e `keras==3.12.4`, na seção da visão (estavam na seção
  "Voz e LLM").
- O cabeçalho passa a dizer a versão do Python do projeto e por quê.
- O comentário quebrado da seção OPCIONAL foi reescrito: o `tensorflowjs` só
  serve para o `vision/treinar.py --web`.

#### Versão do Python

O projeto usa **Python 3.10** (o `.venv` foi criado com o **3.10.11**).

| Pacote | Python aceito |
|--------|---------------|
| `keras 3.12.4` e `groq` | 3.10 ou mais novo |
| `tensorflow 2.20.0` | 3.9 a 3.13 |
| `numpy 1.26.4` | até 3.12 |

Ou seja, funciona do 3.10 ao 3.12. O 3.10 é o padrão para todo mundo ter o
mesmo ambiente. Para montar:

```bash
py -3.10 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip check
```

Conferido no `.venv`: TensorFlow 2.20.0, Keras 3.12.4 e numpy 1.26.4 instalados,
`pip check` sem erros e o `model.h5` abre com saída de 9 classes, igual ao
`classes.json`.

O commit seguinte, só de documentação, registra tudo isto neste arquivo e põe a
versão do Python e o passo do `.venv` no "Como executar" do README. A URL do
`git clone` no README também foi corrigida (era `desenha-ai`, o repositório se
chama `Desenha_AI`).

#### Atenção

Não volte a pôr o `piper-tts` no `requirements.txt` achando que falta a voz. Se
a voz não sair, confira se `voice/piper/piper.exe` e `voice/models/br.onnx`
existem.

---

## Pendências conhecidas

Problemas rastreados até um commit e ainda não corrigidos:

| Problema | Onde | Origem |
|----------|------|--------|
| README com pastas que não existem (`hardware/`, `face3d/`) e sem `ui/` | `README.md` | `a9086e3`, `631d058` |
| Normalização pelo pico, primeira sílaba cortada, barra de espaço global | `voice/listener.py` | ver `f373537` |
| `speaker.wait()` sem timeout | `main.py`, `voice/speaker.py` | ver `455d41a` |
| Rosto não reage à fala (só mostra o cronômetro do desafio) e `pensando.png` sem uso | `ui/face.py` | `6b82a33`, `fe46ad8` |
| Modelo de voz com mais de 50 MB fora do Git LFS | `voice/models/` | `1b44888`, `e45fc62` |
| "cancelar desafio" inicia um desafio novo | `main.py` | ver `e552817` |
| 4 das 9 palavras do desafio (`árvore`, `estrela`, `coração`, `flor`) não estão no `classes.json`: a visão nunca as reconhece e o visitante sempre "erra" | `ui/manager.py` | `631d058` |
| `listener_Whisper.py` sem uso: o `main.py` só usa o Vosk | `voice/` | `58004c2` |

Resolvidas desde a última versão desta tabela:

| Problema | Resolvido em |
|----------|--------------|
| `requirements.txt` com pacotes sem uso e sem o `tensorflow` da visão | `d20f1f2`, `631d058` e `334c64b` |
| Modelo da visão fora do repositório e visão fora do `main.py` | `3dcadae` e `631d058` |
