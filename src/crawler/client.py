"""ZSXQ API client."""
import time
import random
import requests


# Anti-crawl error code (from ZsxqCrawler)
ANTI_CRAWL_ERROR_CODE = 1059
ANTI_CRAWL_MAX_RETRIES = 10

# Rotating User-Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


class ZSXQClient:
    """知识星球 API 客户端."""

    BASE_URL = "https://api.zsxq.com/v2"

    def __init__(self, access_token: str, user_agent: str = "",
                 request_interval: int = 2, max_retries: int = 5):
        self.access_token = access_token
        self.user_agent = user_agent
        self.request_interval = request_interval
        self.max_retries = max_retries
        self._session = self._build_session()
        self._last_request_time = 0
        # Stats tracking
        self.stats = {"requests": 0, "errors": 0, "ratelimited": 0}

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        session.headers.update({
            "Cookie": f"zsxq_access_token={self.access_token}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Cache-Control": "no-cache",
            "Origin": "https://wx.zsxq.com",
            "Pragma": "no-cache",
            "Referer": "https://wx.zsxq.com/",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Version": "2.77.0",
        })
        return session

    def _request_headers(self) -> dict:
        """Per-request headers (UA rotates, timestamp updates)."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "X-Request-Id": str(random.randint(100000000000, 999999999999)),
            "X-Timestamp": str(int(time.time())),
        }

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            jitter = random.uniform(0, 1.5)
            time.sleep(self.request_interval - elapsed + jitter)
        self._last_request_time = time.time()

    def _jittered_backoff(self, attempt: int) -> float:
        base = min(2 ** attempt, 120)
        jitter = random.uniform(0, base * 0.5)
        return base + jitter

    def _anti_crawl_backoff(self, attempt: int) -> int:
        """Longer backoff for anti-crawl (code 1059)."""
        if attempt < 3:
            return 2
        if attempt < 6:
            return 5
        return 10

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.BASE_URL}{path}"
        self.stats["requests"] += 1

        max_retries = max(self.max_retries, ANTI_CRAWL_MAX_RETRIES)

        for attempt in range(max_retries):
            self._rate_limit()
            try:
                # Add per-request rotating headers
                headers = self._request_headers()
                if "headers" in kwargs:
                    headers.update(kwargs.pop("headers"))
                resp = self._session.request(
                    method, url, timeout=30, headers=headers, **kwargs
                )

                # Rate limit
                if resp.status_code == 429:
                    self.stats["ratelimited"] += 1
                    wait = self._jittered_backoff(attempt)
                    print(f"    [429 Rate limited, waiting {wait:.0f}s, attempt {attempt+1}/{max_retries}]")
                    time.sleep(wait)
                    continue

                # Server error
                if resp.status_code >= 500:
                    self.stats["errors"] += 1
                    wait = self._jittered_backoff(attempt + 1)
                    print(f"    [{resp.status_code} Server error, waiting {wait:.0f}s, attempt {attempt+1}/{max_retries}]")
                    time.sleep(wait)
                    continue

                # Client error (not 429)
                if resp.status_code >= 400:
                    self.stats["errors"] += 1
                    raise ZSXQError(f"Client error {resp.status_code}: {resp.text[:200]}")

                # Check JSON response
                data = resp.json()
                if data.get("succeeded"):
                    return data

                error_msg = data.get("error", "unknown")
                error_code = data.get("code", 0)
                self.stats["errors"] += 1

                # Anti-crawl error code 1059 - longer retry
                if error_code == ANTI_CRAWL_ERROR_CODE:
                    wait = self._anti_crawl_backoff(attempt)
                    print(f"    [Code 1059 anti-crawl, waiting {wait}s, attempt {attempt+1}/{max_retries}]")
                    time.sleep(wait)
                    continue

                # Transient server errors - retry
                if "内部错误" in str(error_msg) or "服务异常" in str(error_msg):
                    wait = self._jittered_backoff(attempt + 1)
                    print(f"    [{error_msg}, retrying in {wait:.0f}s, attempt {attempt+1}/{max_retries}]")
                    time.sleep(wait)
                    continue

                raise ZSXQError(f"API error: {error_msg} (code={error_code})")

            except requests.Timeout:
                self.stats["errors"] += 1
                if attempt < max_retries - 1:
                    wait = self._jittered_backoff(attempt)
                    print(f"    [Timeout, retrying in {wait:.0f}s, attempt {attempt+1}/{max_retries}]")
                    time.sleep(wait)
                    continue
                raise ZSXQError("Request timed out")

            except requests.RequestException as e:
                self.stats["errors"] += 1
                if attempt < max_retries - 1:
                    wait = self._jittered_backoff(attempt)
                    print(f"    [Network: {e}, retrying in {wait:.0f}s]")
                    time.sleep(wait)
                    continue
                raise ZSXQError(f"Request failed: {e}")

        raise ZSXQError("Max retries exceeded")

    def get_topics(self, group_id: str, scope: str = "all",
                   count: int = 20, end_time: str = None) -> dict:
        """获取星球话题列表."""
        params = {"scope": scope, "count": count}
        if end_time:
            params["end_time"] = end_time
        return self._request("GET", f"/groups/{group_id}/topics", params=params)

    def get_topic(self, topic_id: str) -> dict:
        return self._request("GET", f"/topics/{topic_id}")

    def search_topics(self, group_id: str, keyword: str,
                      count: int = 20) -> dict:
        params = {"scope": "all", "count": count, "search": keyword}
        return self._request("GET", f"/groups/{group_id}/topics", params=params)

    def get_groups(self) -> dict:
        return self._request("GET", "/groups")


class ZSXQError(Exception):
    pass
