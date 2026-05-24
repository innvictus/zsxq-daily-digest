"""AI provider abstract base class."""
from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    def __init__(self, model: str, api_key: str, base_url: str = ""):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def analyze(self, posts: list[dict], rules: dict, stats: dict = None) -> str:
        """分析帖子列表，返回日报HTML内容."""
        ...
