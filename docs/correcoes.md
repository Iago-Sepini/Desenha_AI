# Registro de correções

Histórico dos bugs encontrados e corrigidos no projeto. Cada entrada explica o
**sintoma**, a **causa** e a **correção**, para que o problema seja reconhecido
rápido se voltar a aparecer.

Entradas mais recentes primeiro.

---

## Marcador da CNC contaminava o histórico da conversa

**23/09/2026** · `ai/llm.py`

### Sintoma

A CNC podia disparar **sozinha**, sem ninguém ter autorizado, depois de algumas
trocas de conversa.

### Causa

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

### Correção

`_enviar()` agora processa a resposta antes de guardar, e devolve
`(texto limpo, comando)`. O histórico nunca vê marcador. O `_save_cache()` também
passou a gravar o texto limpo.

### Atenção

Quem mexer aqui pode "simplificar" de volta para guardar o texto cru, porque
parece mais fiel. Não é: o histórico tem que ficar limpo. O caminho do comando é
o valor de retorno, não o histórico.

Se o sintoma voltar, quem estiver no Arduino vai procurar o erro no código serial
— e a causa está no `ai/llm.py`.

---

## Confirmação da CNC nunca era falada

**23/09/2026** · `main.py` · commit `455d41a`

### Sintoma

A criança dizia "sim, quero" e ouvia **silêncio total**. O assistente só voltava a
falar 1 a 2 segundos depois, já sobre o processo da CNC. A resposta de confirmação
aparecia no terminal com `[IA]` mas nunca chegava à caixa de som.

Parecia que o programa tinha travado no momento mais importante da demonstração.

### Causa

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

### Correção

`speaker.wait()` antes de encadear o evento, para a confirmação terminar de ser
falada.

### Efeito colateral aceito

Durante os segundos da confirmação a thread que chamou fica bloqueada: o `>` do
terminal não volta e o push-to-talk não responde. E se alguém disser "parar" nesse
intervalo, o `wait()` só retorna quando disserem "continuar" — o `Speaker.wait()`
não tem timeout.

---

## Chave de API era da xAI, não da Groq

**23/09/2026** · `.env`

### Sintoma

```
[LLM] erro: Error code: 401 - {'error': {'message': 'Invalid API Key', ...}}
```

O chat não respondia nada.

### Causa

A chave no `.env` começava com `xai-`, que é prefixo da **xAI (Grok)**. O projeto
usa a **Groq**, cujas chaves começam com `gsk_`. São duas empresas diferentes com
nomes quase idênticos:

| | Groq | Grok |
|---|---|---|
| Empresa | Groq Inc. | xAI |
| O que é | Provedor de inferência (LPU) | Modelo de LLM |
| Console | console.groq.com | console.x.ai |
| Prefixo | `gsk_...` | `xai-...` |

O `ai/llm.py` importa `from groq import Groq`, então fala com `api.groq.com`, que
não reconhece uma chave `xai-`.

### Correção

Chave nova gerada em <https://console.groq.com/keys>, começando com `gsk_`.

---

## Faxina: `import` morto e caractere perdido no prompt

**23/09/2026** · `ai/llm.py`, `ai/prompts.py` · commit `aa391c1`

Duas coisas cosméticas, sem efeito funcional:

- `import re` no `ai/llm.py` não era usado por nada.
- Um `z` solto numa linha do `PERSONA`, entre a descrição do rosto e a seção do
  projeto. Estava sendo enviado ao modelo em toda requisição.
