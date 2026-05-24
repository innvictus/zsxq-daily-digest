"""ZSXQ content fetcher with deduplication and search."""
import re
from datetime import datetime, timedelta
from .client import ZSXQClient
from ..storage.database import Database


class Fetcher:
    MAX_PAGES_PER_GROUP = 50     # Safety cap: max pages per fetch
    MAX_TOPICS_PER_FETCH = 500   # Safety cap: max topics per group per run

    def __init__(self, client: ZSXQClient, db: Database):
        self.client = client
        self.db = db

    def fetch_group(self, group_id: str, group_name: str,
                    start: datetime, end: datetime) -> dict:
        """抓取单个星球指定时间范围内全部帖子. 返回统计信息."""
        self.db.ensure_group(group_id, group_name)

        end_time_str = end.strftime("%Y-%m-%dT%H:%M:%S.000+0800")
        start_time_str = start.strftime("%Y-%m-%dT%H:%M:%S.000+0800")

        stats = {
            "group_name": group_name,
            "group_id": group_id,
            "pages": 0,
            "topics_seen": 0,
            "new_posts": 0,
            "errors": 0,
            "oldest_topic_time": "",
            "complete": False,
        }

        # Use end_time as cursor for proper pagination
        cursor = end_time_str

        print(f"  [{group_name}] Fetching {start.strftime('%m-%d %H:%M')} -> "
              f"{end.strftime('%m-%d %H:%M')}...")

        for page in range(1, self.MAX_PAGES_PER_GROUP + 1):
            try:
                data = self.client.get_topics(
                    group_id,
                    scope="all",
                    count=20,
                    end_time=cursor,
                )
            except Exception as e:
                stats["errors"] += 1
                print(f"  [{group_name}] Error on page {page}: {e}")
                if page == 1:
                    # First page failed entirely - nothing we can do
                    break
                # Later page failed - we have some data, just stop pagination
                print(f"  [{group_name}] Partial fetch: got {stats['new_posts']} posts "
                      f"before error on page {page}")
                break

            resp_data = data.get("resp_data", data)
            topics = resp_data.get("topics", [])

            if not topics:
                stats["complete"] = True
                break

            stats["pages"] = page
            stats["topics_seen"] += len(topics)

            # Update cursor to the oldest topic's create_time for next page
            cursor = topics[-1].get("create_time", cursor)

            # Filter topics within time range and insert new ones
            batch = []
            for t in topics:
                parsed = self._parse_topic(t, group_id)
                ct = parsed["create_time"]

                # Track oldest
                if not stats["oldest_topic_time"] or ct < stats["oldest_topic_time"]:
                    stats["oldest_topic_time"] = ct

                # If we've gone past our start time, still include this post
                # but stop pagination after this batch
                if ct < start_time_str:
                    if not self.db.topic_exists(parsed["topic_id"]):
                        batch.append(parsed)
                    n = self.db.insert_topics_batch(batch)
                    stats["new_posts"] += n
                    stats["complete"] = True
                    break

                if not self.db.topic_exists(parsed["topic_id"]):
                    batch.append(parsed)

            else:
                # Didn't break - insert batch and continue pagination
                n = self.db.insert_topics_batch(batch)
                stats["new_posts"] += n

                if stats["new_posts"] >= self.MAX_TOPICS_PER_FETCH:
                    print(f"  [{group_name}] Reached safety cap of "
                          f"{self.MAX_TOPICS_PER_FETCH} posts")
                    break

                if page % 3 == 0:
                    print(f"  [{group_name}] Page {page}: {stats['new_posts']} new, "
                          f"{stats['topics_seen']} seen, cursor at {cursor[:19]}")

                continue

            # If we get here, we broke out of the inner loop (past start time)
            break

        # Summary
        status = "complete" if stats["complete"] else "partial"
        time_range = ""
        if stats["oldest_topic_time"]:
            time_range = f", oldest: {stats['oldest_topic_time'][:19]}"

        print(f"  [{group_name}] Done ({status}): {stats['new_posts']} new posts, "
              f"{stats['pages']} pages, {stats['errors']} errors{time_range}")

        self.db.update_group_fetch_time(group_id)
        return stats

    def _parse_topic(self, raw: dict, group_id: str) -> dict:
        topic_type = raw.get("type", "talk")
        title = raw.get("title", "")

        content = ""
        if topic_type == "talk" and "talk" in raw:
            text = raw["talk"].get("text", "")
            content = self._strip_html(text)
        elif topic_type == "q&a" and "question" in raw:
            q_text = self._strip_html(raw["question"].get("text", ""))
            answer = raw.get("answer", {})
            a_text = self._strip_html(answer.get("text", "")) if answer else ""
            title = raw["question"].get("title", title) or q_text[:80]
            content = f"Q: {q_text}\n\nA: {a_text}"
        elif topic_type == "task" and "task" in raw:
            content = self._strip_html(raw["task"].get("description", ""))
        else:
            for key in ("text", "description", "content"):
                if key in raw:
                    content = self._strip_html(raw[key])
                    break

        if not content:
            content = title

        content = content[:10000]

        return {
            "topic_id": str(raw.get("topic_id", "")),
            "group_id": group_id,
            "title": title or "(无标题)",
            "content": content,
            "author_name": raw.get("owner", {}).get("name", "匿名"),
            "author_id": str(raw.get("owner", {}).get("user_id", "")),
            "create_time": raw.get("create_time", ""),
            "comments_count": raw.get("interaction", {}).get("comments_count", 0),
            "likes_count": raw.get("interaction", {}).get("likes_count", 0),
            "readings_count": raw.get("interaction", {}).get("readings_count", 0),
            "topic_type": topic_type,
            "files": self._extract_files(raw),
            "_raw": raw,
        }

    def _extract_files(self, raw: dict) -> list[dict]:
        files = []

        talk = raw.get("talk", {})
        if talk:
            for f in talk.get("files", []):
                files.append({
                    "name": f.get("name", ""),
                    "url": f.get("url", ""),
                    "size": f.get("size", 0),
                    "type": f.get("type", ""),
                    "text_content": "",
                })
            for img in talk.get("images", []):
                files.append({
                    "name": img.get("name", "image"),
                    "url": img.get("large_url", img.get("url", "")),
                    "size": img.get("size", 0),
                    "type": "image",
                    "text_content": "",
                })

        for f in raw.get("files", []):
            files.append({
                "name": f.get("name", ""),
                "url": f.get("url", ""),
                "size": f.get("size", 0),
                "type": f.get("type", ""),
                "text_content": "",
            })

        question = raw.get("question", {})
        answer = raw.get("answer", {})
        for obj in (question, answer):
            if obj:
                for f in obj.get("files", []):
                    files.append({
                        "name": f.get("name", ""),
                        "url": f.get("url", ""),
                        "size": f.get("size", 0),
                        "type": f.get("type", ""),
                        "text_content": "",
                    })

        return files

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def search(self, keyword: str, group_id: str = None,
               count: int = 50) -> list[dict]:
        return self.db.search_topics(keyword, group_id, count)

    def search_online(self, group_id: str, keyword: str,
                      count: int = 20) -> list[dict]:
        data = self.client.search_topics(group_id, keyword, count)
        resp_data = data.get("resp_data", data)
        topics = resp_data.get("topics", [])
        return [self._parse_topic(t, group_id) for t in topics]
