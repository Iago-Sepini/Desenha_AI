import json
from pathlib import Path

from groq import Groq

import config
from ai.prompts import SYSTEM_PROMPT, montar_pedido


class GroqLLM:
    """Conversa com a Groq mantendo o histórico de um visitante.

    - chat(mensagem): fala do visitante ou aviso [SISTEMA] -> resposta
    - describe(objeto): desenho identificado pela visão -> resposta
    - reset(): novo visitante, zera a conversa
    """

    MAX_HISTORICO = 20  # mensagens guardadas (as mais antigas saem)

    def __init__(self, api_key=None, model=None, cache_file=None):
        self.api_key = api_key or config.GROQ_API_KEY
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY não encontrada. Crie o .env (veja o .env.example).")
        self.model = model or config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key, timeout=config.GROQ_TIMEOUT)
        self.cache_file = Path(cache_file or config.CACHE_FILE)
        self.history = []

    # ---------- API pública ----------
    def reset(self):
        self.history = []

    def chat(self, mensagem: str, plano_b: str = None) -> str:
        try:
            return self._enviar(mensagem)
        except Exception as e:
            print(f"[LLM] erro: {e}")
            return plano_b or "Desculpe, não consegui responder agora. Pode repetir?"

    def describe(self, objeto: str) -> str:
        pedido = montar_pedido(objeto)
        try:
            texto = self._enviar(pedido)
            self._save_cache(objeto, texto)
            return texto
        except Exception as e:
            print(f"[LLM] erro: {e}")
            texto = self._load_cache().get(self._key(objeto))
            if texto:
                print("[LLM] usando resposta guardada")
            else:
                texto = f"Não consegui pesquisar sobre {objeto} agora. Vamos tentar de novo?"
            # registra no histórico para a conversa continuar fazendo sentido
            self.history.append({"role": "user", "content": pedido})
            self.history.append({"role": "assistant", "content": texto})
            self._trim()
            return texto

    # ---------- internos ----------
    def _enviar(self, mensagem: str) -> str:
        self.history.append({"role": "user", "content": mensagem})
        try:
            texto = self._ask()
        except Exception:
            self.history.pop()  # não deixa mensagem sem resposta no histórico
            raise
        self.history.append({"role": "assistant", "content": texto})
        self._trim()
        return texto

    def _ask(self) -> str:
        extra = {}
        if "gpt-oss" in self.model:
            extra["reasoning_effort"] = "low"  # pensa menos = responde mais rápido

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