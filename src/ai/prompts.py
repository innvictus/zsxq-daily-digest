"""Shared prompt building utilities for AI providers."""


def build_system_prompt(rules: dict) -> str:
    report_rules = rules.get("report_rules", {})
    role = report_rules.get("role", "你是一个专业的内容编辑。")
    data_scope = report_rules.get("data_scope", "")

    sections = report_rules.get("output_format", {}).get("sections", [])
    section_text = ""
    for i, s in enumerate(sections):
        section_text += f"\n### {i+1}. {s['name']}\n{s['description']}"

    style = report_rules.get("style", "")
    constraints = report_rules.get("constraints", [])
    constraint_text = "\n".join(f"- {c}" for c in constraints)

    return f"""{role}

{data_scope}

请严格按照以下结构输出日报HTML正文（不要包含<html>、<head>、<body>标签，只输出body内部HTML）：
{section_text}

写作风格：{style}

限制条件：
{constraint_text}

HTML格式要求：
- 直接输出纯HTML，绝对不要用```html或任何markdown代码块包裹
- 每个section用 <section class="report-section"> 包裹，内部标题用 <h2>
- 数据表格使用 <table class="data-table">，表头用 <thead><tr><th>，内容用 <tbody><tr><td>
- 财报/估值类表格对齐工整，数字右对齐
- 每篇精选文章结尾必须有一个醒目的原文链接，使用帖子的group_id和topic_id拼出真实URL：
  <a href="https://wx.zsxq.com/group/帖子对应的group_id/topic/帖子对应的topic_id" class="source-link" target="_blank">阅读原文 →</a>
  严禁使用 # 或假链接。每个帖子都有group_id和topic_id，就在上方数据中标明了。
- 文章卡片嵌套在 <div class="article-card"> 里
- 金句引用用 <blockquote>，注明出处和作者
- 板块热度排名使用表格（排名 | 板块 | 提及次数 | 核心逻辑 | 水晶标的）
  水晶标的列要列出该板块券商推荐的个股，附上推荐券商名称
  如果券商原文说"首推""重点推荐""强烈推荐"，必须在标的后面标注【XX券商首推】
  首推标的必须排在该板块标的列表的最前面
- 不要在报告中输出格式说明文字，直接输出内容
- MP3录音文件一律忽略，不要在日报中提及
"""


def build_user_prompt(posts: list[dict], stats: dict = None) -> str:
    if stats is None:
        stats = {"posts": len(posts), "files": 0, "images": 0, "pdfs": 0, "audios": 0}

    # Exclude MP3s from stats display
    display_stats = dict(stats)
    display_stats["files"] = stats["pdfs"] + stats["images"] + stats["others"]

    lines = [
        "以下是今天（0:00到24:00）知识星球上所有帖子的完整内容，请据此生成日报：",
        f"共计 {len(posts)} 篇帖子",
        "",
        f"【数据统计】总帖子 {stats['posts']} 篇，有意义附件 {display_stats['files']} 个",
        f"  - PDF研报文件: {stats['pdfs']} 个",
        f"  - 图片: {stats['images']} 个",
        f"  - 其他文件: {stats['others']} 个",
        f"  - (MP3录音 {stats['audios']} 个已忽略，不在日报中展示)",
        "",
    ]

    for i, post in enumerate(posts, 1):
        group_name = post.get("group_name", "")

        # Files - skip MP3 files
        files_info = ""
        files_data = post.get("files", [])
        non_mp3_files = [f for f in files_data
                         if not f.get("name", "").lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg'))]
        if non_mp3_files:
            files_info = "\n    【附件文件】:\n"
            for f in non_mp3_files:
                files_info += f"      - 文件名: {f.get('name', 'unknown')}\n"
                if f.get("text_content"):
                    files_info += f"        文件内容摘要: {f['text_content'][:2000]}\n"

        lines.append(
            f"---\n"
            f"[{i}] 标题: {post['title']}\n"
            f"    作者: {post['author_name']}\n"
            f"    时间: {post['create_time']}\n"
            f"    星球: {group_name} ({post.get('group_id', '')})\n"
            f"    topic_id: {post['topic_id']}\n"
            f"    评论: {post.get('comments_count', 0)}, "
            f"点赞: {post.get('likes_count', 0)}, "
            f"阅读: {post.get('readings_count', 0)}\n"
            f"    内容:\n{post.get('content', '')[:5000]}\n"
            f"{files_info}"
        )

    lines.append("\n特别重要：")
    lines.append("1. 板块热度表格必须包含'首推标的'列，列出每个板块券商推荐的个股")
    lines.append("2. 券商说'首推''重点推荐''强烈推荐'的标的要标注【XX券商首推】并排在最前面")
    lines.append("3. 每篇文章必须用真实的group_id和topic_id拼出原文链接")
    lines.append("4. 估值指引用表格，数字右对齐")
    lines.append("5. 最后的「综合推荐买入」栏目只推荐3个标的，按确定性从高到低排列")
    lines.append("   第一个必须是你认为最确定、最可能上涨的，推荐理由要结合今日研报的具体逻辑")

    return "\n".join(lines)
