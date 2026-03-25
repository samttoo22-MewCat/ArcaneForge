"""Client-side DM caller: receives signed prompt packet, calls LLM, submits ruling."""
import json
from typing import Any

import httpx


class DMCaller:
    """
    Calls the user's own LLM API with a server-signed prompt packet,
    then submits the ruling back to the server.

    The user provides their own api_key — the server never sees it.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        server_url: str,
        provider: str = "openai",  # "openai" | "anthropic" | "openai_compat"
        base_url: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.server_url = server_url.rstrip("/")
        self.provider = provider
        self.base_url = base_url

    async def handle_do_response(self, server_response: dict) -> dict:
        """
        Full flow:
        1. Extract dm_packet from server response
        2. Call LLM with payload
        3. Parse ruling
        4. Submit to server /api/v1/dm/ruling
        5. Return server's apply result
        """
        dm_packet = server_response.get("dm_packet")
        if not dm_packet:
            raise ValueError("No dm_packet in server response")

        ruling_json = await self._call_llm(dm_packet["payload"])
        submission = self._build_submission(dm_packet, ruling_json)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/api/v1/dm/ruling",
                json=submission,
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_llm(self, payload: dict) -> dict:
        prompt = self._format_prompt(payload)

        if self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            return await self._call_openai_compat(prompt)

    def _format_prompt(self, payload: dict) -> str:
        return (
            "You are a Dungeon Master for a text MUD game. "
            "Evaluate the player's action and return ONLY valid JSON matching the output_schema.\n\n"
            f"Context:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Return JSON only, no prose:"
        )

    async def _call_openai_compat(self, prompt: str) -> dict:
        base = self.base_url or "https://api.openai.com/v1"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)

    async def _call_anthropic(self, prompt: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": self.model,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            return json.loads(content)

    def _build_submission(self, dm_packet: dict, ruling_json: dict) -> dict:
        return {
            "nonce": dm_packet["nonce"],
            "timestamp": dm_packet["timestamp"],
            "session_id": dm_packet["session_id"],
            "signature": dm_packet["signature"],
            "ruling": ruling_json,
        }
