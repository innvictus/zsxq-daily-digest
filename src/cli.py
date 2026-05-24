"""Command-line interface."""
import argparse
import sys
import os
import yaml
from datetime import datetime, timedelta

from .crawler.client import ZSXQClient
from .crawler.fetcher import Fetcher
from .storage.database import Database
from .ai.claude import ClaudeProvider
from .ai.openai import OpenAIProvider
from .ai.deepseek import DeepSeekProvider
from .report.generator import ReportGenerator

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")


def load_yaml(filename: str) -> dict:
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_ai_provider(config: dict):
    ai_config = config["ai"]
    provider_name = ai_config["provider"]
    provider_config = ai_config.get(provider_name, {})

    kwargs = {
        "model": provider_config.get("model", ""),
        "api_key": provider_config.get("api_key", ""),
        "base_url": provider_config.get("base_url", ""),
    }

    if provider_name == "claude":
        return ClaudeProvider(**kwargs)
    elif provider_name == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_name == "deepseek":
        return DeepSeekProvider(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}")


def cmd_fetch(args):
    config = load_yaml("config.yaml")
    groups_config = load_yaml("groups.yaml")

    client = ZSXQClient(
        access_token=config["zsxq"]["access_token"],
        user_agent=config["zsxq"].get("user_agent", ""),
        request_interval=config["zsxq"].get("request_interval", 2),
        max_retries=config["zsxq"].get("max_retries", 3),
    )
    db = Database(os.path.join(config["output"]["data_dir"], "zsxq.db"))
    fetcher = Fetcher(client, db)

    # Determine date range
    if args.start and args.end:
        start = datetime.fromisoformat(args.start)
        end = datetime.fromisoformat(args.end)
    else:
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)

    print(f"Fetching posts from {start} to {end}\n")

    total = 0
    all_stats = []
    for group in groups_config.get("groups", []):
        if not group.get("enabled", True):
            continue
        stats = fetcher.fetch_group(
            group["group_id"], group["name"],
            start=start, end=end,
        )
        all_stats.append(stats)
        total += stats["new_posts"]

    # Summary
    print(f"\n{'='*50}")
    print(f"Fetch Summary:")
    for s in all_stats:
        status = "OK" if s["complete"] else "PARTIAL"
        print(f"  {s['group_name']}: {s['new_posts']} new [{status}] "
              f"({s['pages']} pages, {s['errors']} errors, "
              f"oldest: {s['oldest_topic_time'][:19] if s['oldest_topic_time'] else 'N/A'})")
    print(f"  Total: {total} new posts")
    print(f"  API requests: {client.stats['requests']}")
    print(f"  API errors: {client.stats['errors']}")
    print(f"  Rate limited: {client.stats['ratelimited']}")
    print(f"{'='*50}")
    db.close()


def cmd_search(args):
    config = load_yaml("config.yaml")
    db = Database(os.path.join(config["output"]["data_dir"], "zsxq.db"))
    fetcher = Fetcher(None, db)

    results = fetcher.search(args.keyword, group_id=args.group_id)

    print(f"\nFound {len(results)} posts matching '{args.keyword}':\n")
    for i, post in enumerate(results, 1):
        print(f"[{i}] {post['title']}")
        print(f"    作者: {post['author_name']} | "
              f"评论: {post['comments_count']} | "
              f"点赞: {post['likes_count']}")
        print(f"    内容: {post.get('content', '')[:150]}...")
        print()

    db.close()


def cmd_report(args):
    config = load_yaml("config.yaml")
    rules = load_yaml("rules.yaml")

    ai_provider = build_ai_provider(config)
    db = Database(os.path.join(config["output"]["data_dir"], "zsxq.db"))

    generator = ReportGenerator(
        db, ai_provider, rules,
        output_dir=config["output"]["dir"],
    )

    if args.date:
        date = datetime.fromisoformat(args.date)
    else:
        date = datetime.now() - timedelta(days=1)

    filepath = generator.generate(date)
    print(f"\nReport generated: {filepath}")

    # Send email notification
    if config.get("notify", {}).get("enabled", False):
        from .notify.email_sender import send_report_email
        send_report_email(filepath, config)

    db.close()


def cmd_run(args):
    """Full pipeline: fetch + report."""
    # First fetch
    fetch_args = argparse.Namespace(start=args.start, end=args.end)
    cmd_fetch(fetch_args)

    print("\n---\n")

    # Then generate report
    report_args = argparse.Namespace(date=args.date)
    cmd_report(report_args)


def main():
    parser = argparse.ArgumentParser(
        description="ZSXQ Daily Digest - 知识星球AI日报生成器",
        prog="zsxq-daily",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="抓取知识星球内容")
    p_fetch.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    p_fetch.add_argument("--end", help="结束日期 (YYYY-MM-DD)")

    # search
    p_search = subparsers.add_parser("search", help="搜索帖子")
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument("--group-id", help="限定星球ID")

    # report
    p_report = subparsers.add_parser("report", help="生成日报")
    p_report.add_argument("--date", help="日报日期 (YYYY-MM-DD)，默认为昨天")

    # run (fetch + report)
    p_run = subparsers.add_parser("run", help="一键抓取并生成日报")
    p_run.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    p_run.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    p_run.add_argument("--date", help="日报日期 (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
