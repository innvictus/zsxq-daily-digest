"""Claude API provider using Anthropic SDK."""
from anthropic import Anthropic
from .base import BaseAIProvider
from .prompts import build_system_prompt, build_user_prompt


class ClaudeProvider(BaseAIProvider):
    def __init__(self, model: str, api_key: str, base_url: str = ""):
        super().__init__(model, api_key, base_url)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = Anthropic(**kwargs)

    def analyze(self, posts: list[dict], rules: dict, stats: dict = None) -> str:
        system_prompt = build_system_prompt(rules)
        user_prompt = build_user_prompt(posts, stats)

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text
