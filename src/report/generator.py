"""Daily report generator."""
import json
import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from ..storage.database import Database
from ..ai.base import BaseAIProvider


class ReportGenerator:
    def __init__(self, db: Database, ai_provider: BaseAIProvider,
                 rules: dict, output_dir: str = "output"):
        self.db = db
        self.ai = ai_provider
        self.rules = rules
        self.output_dir = output_dir

        template_dir = Path(__file__).parent / "templates"
        self.jinja = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def generate(self, date: datetime) -> str:
        date_str = date.strftime("%Y-%m-%d")
        start = date.strftime("%Y-%m-%dT00:00:00.000+0800")
        end = date.strftime("%Y-%m-%dT23:59:59.000+0800")

        # Check cache
        existing = self.db.get_report(date_str)
        if existing:
            print(f"Report for {date_str} already exists, using cached version.")
            return self._write_report(date_str, existing["html_content"])

        posts = self.db.get_topics_by_date(start, end)
        stats = self._compute_stats(posts)
        print(f"Found {stats['posts']} posts, {stats['files']} files "
              f"({stats['pdfs']} PDFs, {stats['audios']} MP3s, {stats['images']} images) for {date_str}")

        if not posts:
            html = self._empty_report(date_str)
        else:
            print("Sending to AI for analysis...")
            ai_content = self.ai.analyze(posts, self.rules, stats)
            html = self._render(date_str, ai_content, stats)

        self.db.save_report(date_str, html, stats["posts"])
        return self._write_report(date_str, html)

    def _compute_stats(self, posts: list[dict]) -> dict:
        stats = {
            "posts": len(posts),
            "files": 0,
            "images": 0,
            "pdfs": 0,
            "audios": 0,
            "others": 0,
            "file_names": [],
        }

        for p in posts:
            fdata = p.get("files", [])
            if isinstance(fdata, str):
                try:
                    fdata = json.loads(fdata)
                except (json.JSONDecodeError, TypeError):
                    fdata = []
            for f in fdata:
                stats["files"] += 1
                name = f.get("name", "").lower()
                ftype = f.get("type", "").lower()
                if "image" in ftype or name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    stats["images"] += 1
                elif name.endswith('.pdf') or "pdf" in ftype:
                    stats["pdfs"] += 1
                elif name.endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg')) or "audio" in ftype:
                    stats["audios"] += 1
                else:
                    stats["others"] += 1
                stats["file_names"].append(f.get("name", "unknown"))

        return stats

    def _render(self, date_str: str, ai_content: str, stats: dict) -> str:
        template = self.jinja.get_template("daily.html")
        return template.render(
            date=date_str,
            content=ai_content,
            posts_count=stats["posts"],
            stats=stats,
        )

    def _empty_report(self, date_str: str) -> str:
        template = self.jinja.get_template("daily.html")
        return template.render(
            date=date_str,
            content='<section class="report-section"><p>今日无新内容。</p></section>',
            posts_count=0,
            stats={"posts": 0, "files": 0, "images": 0, "pdfs": 0, "audios": 0, "others": 0},
        )

    def _write_report(self, date_str: str, html: str) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, f"{date_str}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML saved: {filepath}")

        # Generate PDF via Chrome headless
        self._html_to_pdf(filepath, date_str)

        return filepath

    def _html_to_pdf(self, html_path: str, date_str: str):
        """Convert HTML to PDF. Tries Chrome, then weasyprint."""
        pdf_path = os.path.join(self.output_dir, f"{date_str}.pdf")

        # Try Chrome headless first (macOS)
        if self._pdf_via_chrome(html_path, pdf_path):
            print(f"PDF saved: {pdf_path}")
            return

        # Try weasyprint (Docker/Linux)
        if self._pdf_via_weasyprint(html_path, pdf_path):
            print(f"PDF saved: {pdf_path}")
            return

        print("PDF skipped: no PDF engine available")

    def _pdf_via_chrome(self, html_path: str, pdf_path: str) -> bool:
        import subprocess
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                try:
                    subprocess.run(
                        [path, "--headless", "--disable-gpu",
                         f"--print-to-pdf={pdf_path}",
                         f"file://{os.path.abspath(html_path)}"],
                        check=True, capture_output=True, timeout=60,
                    )
                    return True
                except Exception:
                    pass
        return False

    def _pdf_via_weasyprint(self, html_path: str, pdf_path: str) -> bool:
        try:
            from weasyprint import HTML as WHTML
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            WHTML(string=html).write_pdf(pdf_path)
            return True
        except Exception:
            return False
