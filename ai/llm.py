import json
from pathlib import Path

from groq import Groq

import config
from ai.prompts import SYSTEM_PROMPT, montar_pedido


class GroqLLM:
    """Conversa com a Groq mantendo o histórico de um visitante."""

    MAX_HISTORICO = 20

    def __init__(self, api_key=None, model=None, cache_file=None):
        self.api_key = api_key or config.GROQ_API_KEY
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY não encontrada. Crie o .env (veja o .env.example).")
        self.model = model or config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key, timeout=config.GROQ_TIMEOUT)
        self.cache_file = Path(cache_file or config.CACHE_FILE)
        self.history = []

    def reset(self):
        self.history = []

    def _processar_resposta(self, texto: str):
        """Identifica comandos de sistema e limpa o texto para a síntese de voz."""
        comando = None
        if "[[CNC_SIM]]" in texto:
            comando = "CNC_SIM"
            texto = texto.replace("[[CNC_SIM]]", "")
        elif "[[CNC_NAO]]" in texto:
            comando = "CNC_NAO"
            texto = texto.replace("[[CNC_NAO]]", "")
        
        return texto.strip(), comando

    def chat(self, mensagem: str, plano_b: str = None) -> tuple[str, str | None]:
        try:
            return self._enviar(mensagem)
        except Exception as e:
            print(f"[LLM] erro: {e}")
            msg_erro = plano_b or "Desculpe, não consegui responder agora. Pode repetir?"
            return msg_erro, None

    def describe(self, objeto: str) -> tuple[str, str | None]:
        pedido = montar_pedido(objeto)
        try:
            texto, comando = self._enviar(pedido)
            self._save_cache(objeto, texto)
            return texto, comando
        except Exception as e:
            print(f"[LLM] erro: {e}")
            guardado = self._load_cache().get(self._key(objeto))
            if guardado:
                print("[LLM] usando resposta guardada")
            else:
                guardado = f"Não consegui pesquisar sobre {objeto} agora. Vamos tentar de novo?"

            # Caches gravados antes desta correção podem conter marcadores, por isso
            # a resposta guardada passa pelo mesmo tratamento antes de ir ao histórico.
            texto, comando = self._processar_resposta(guardado)
            self.history.append({"role": "user", "content": pedido})
            self.history.append({"role": "assistant", "content": texto})
            self._trim()
            return texto, comando

    def _enviar(self, mensagem: str) -> tuple[str, str | None]:
        """Envia a mensagem ao modelo e devolve (texto limpo, comando).

        O histórico guarda o texto já SEM os marcadores [[CNC_*]]. Guardar o texto
        cru contaminaria o contexto: nas rodadas seguintes o modelo veria que ele
        mesmo escreveu [[CNC_SIM]] e isso funciona como exemplo, levando-o a repetir
        o marcador fora de hora. Como o main.py trata esse marcador como autorização
        do visitante, a CNC ligaria sozinha no meio da conversa.
        """
        self.history.append({"role": "user", "content": mensagem})
        try:
            bruto = self._ask()
        except Exception:
            self.history.pop()
            raise
        texto, comando = self._processar_resposta(bruto)
        self.history.append({"role": "assistant", "content": texto})
        self._trim()
        return texto, comando

    def _ask(self) -> str:
        extra = {}
        if "gpt-oss" in self.model:
            extra["reasoning_effort"] = "low"

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
            temperature=0.6,
            max_tokens=1000,
            extra_body=extra,
        )
        texto = (resp.choices[0].message.content or "").strip()
        if not texto:
            raise RuntimeError("resposta vazia")
        return texto

    def _trim(self):
        if len(self.history) > self.MAX_HISTORICO:
            self.history = self.history[-self.MAX_HISTORICO:]
        while self.history and self.history[0]["role"] != "user":
            self.history.pop(0)

    @staticmethod
    def _key(objeto: str) -> str:
        return " ".join(objeto.lower().split())

    def _load_cache(self) -> dict:
        try:
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cache(self, objeto: str, texto: str):
        try:
            data = self._load_cache()
            data[self._key(objeto)] = texto
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LLM] não consegui salvar o cache: {e}")