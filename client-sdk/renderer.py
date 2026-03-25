"""Optional SLM-based narrative renderer — runs entirely client-side."""
import json
from typing import Optional

import httpx


class NarrativeRenderer:
    """
    Converts structured game events into readable narrative text using
    a local or remote small language model. Purely cosmetic — the server
    never depends on this output.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "http://localhost:11434/v1",  # default: Ollama local
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def render(self, event: dict) -> str:
        prompt = self._build_render_prompt(event)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key or 'none'}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150,
                        "temperature": 0.8,
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return self._fallback_render(event)

    def _build_render_prompt(self, event: dict) -> str:
        return (
            "Convert this game event into a short, immersive narrative sentence (max 2 sentences). "
            "Write in second person. No game mechanics terminology.\n\n"
            f"Event: {json.dumps(event, ensure_ascii=False)}"
        )

    def _fallback_render(self, event: dict) -> str:
        """Simple template fallback when LLM is unavailable."""
        et = event.get("event_type", "")
        data = event.get("data", event)
        if et == "combat_round":
            return f"{data.get('actor_id', '?')} 攻擊了 {data.get('target_id', '?')}，造成 {data.get('damage', 0)} 點傷害。"
        if et == "player_moved":
            return f"{data.get('player_name', '?')} 向 {data.get('direction', '?')} 方向移動。"
        if et == "player_said":
            return f"{data.get('player_name', '?')} 說：「{data.get('message', '')}」"
        return json.dumps(event, ensure_ascii=False)
