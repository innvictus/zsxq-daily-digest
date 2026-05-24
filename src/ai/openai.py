"""OpenAI-compatible provider."""
from openai import OpenAI
from .base import BaseAIProvider
from .prompts import build_system_prompt, build_user_prompt


class OpenAIProvider(BaseAIProvider):
    def __init__(self, model: str, api_key: str, base_url: str = ""):
        super().__init__(model, api_key, base_url)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def analyze(self, posts: list[dict], rules: dict, stats: dict = None) -> str:
        system_prompt = build_system_prompt(rules)
        user_prompt = build_user_prompt(posts, stats)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8192,
        )
        return resp.choices[0].message.content
