# Registro de correções

Histórico dos bugs encontrados e corrigidos no projeto. Cada entrada explica o
**sintoma**, a **causa** e a **correção**, para que o problema seja reconhecido
rápido se voltar a aparecer.

Entradas mais recentes primeiro.

---

## Cache guardava o nome antigo do assistente

**23/09/2026** · `data/cache/respostas.json`

### Sintoma

Com a Groq fora do ar, o plano B entrava e o assistente se apresentava como
**Iago** — nome antigo do projeto. Hoje ele se chama Max (`NOME_ASSISTENTE`, em
`ai/prompts.py`).

Só acontece quando a API falha, então passa despercebido em teste normal e
aparece justo na feira, se a internet cair.

### Causa

As respostas foram gravadas quando o assistente ainda se chamava Iago. O cache
guarda o **texto pronto**, então não acompanha mudanças no prompt.

Havia também uma entrada `"bob_esponja"` (com underline) cujo conteúdo era a
resposta de "não entendi seu desenho" — um plano B que já nascia falhando. Repare
que ela convivia com `"bob esponja"` (com espaço): o `_key()` normaliza espaços,
mas underline não é espaço, então as duas são chaves diferentes.

### Correção

Nome atualizado nas três entradas que o citavam, e a entrada `"bob_esponja"`
removida. O conteúdo das demais foi preservado em vez de apagar o arquivo, para
não ficar sem plano B nenhum.

### Atenção

O cache não se atualiza sozinho quando o prompt muda. Ao mexer no
`ai/prompts.py` — principalmente em nome, tom ou regras de apresentação — vale
conferir se as respostas guardadas ainda combinam.

Vale também para o Módulo 1: se a visão devolver rótulos com underline
(`bob_esponja`), eles viram chaves separadas das com espaço e o cache racha em
duas entradas para o mesmo desenho.

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
