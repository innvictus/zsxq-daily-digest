#!/usr/bin/env python3
"""ZSXQ Daily Digest - 知识星球AI日报生成器.

Usage:
    python main.py run              # 一键抓取+生成日报
    python main.py fetch            # 只抓取内容
    python main.py report           # 基于已有数据生成日报
    python main.py search "关键词"  # 搜索帖子
"""

from src.cli import main

if __name__ == "__main__":
    main()
