"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề: Du lịch Việt Nam — lịch trình, địa điểm, ẩm thực, quy định địa phương.
URL trải đều các nhóm nội dung trên (dư so với mức tối thiểu 5), để RAG
sau này trả lời được nhiều loại câu hỏi khác nhau.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # Ẩm thực
    "https://www.ivivu.com/blog/2023/03/top-18-quan-an-ngon-o-hoi-an-mang-den-trai-nghiem-am-thuc-nhu-nguoi-dia-phuong/",
    "https://www.willflyforfood.net/hoi-an-food-guide/",
    # Lễ hội / văn hóa
    "https://vinwonders.com/vi/wonderpedia/news/ve-dep-dem-trung-thu-o-hoi-an/",
    # Quy định địa phương
    "https://hoianheritage.danang.gov.vn/en/news/news-events/announcement-of-the-visiting-in-hoi-an-ancient-town-125.html",
    "https://en.baobacninhtv.vn/hoi-an-launches-tour-group-entry-fees.bbg",
    "https://tuoitrenews.vn/news/ttnewsstyle/20250107/hoi-an-wants-to-offer-free-entry-into-ancient-town-to-more-visitor-groups/83776.html",
]


async def crawl_article(crawler: AsyncWebCrawler, url: str) -> dict:
    # Bỏ menu/header/footer để chunk không lẫn rác điều hướng.
    config = CrawlerRunConfig(excluded_tags=["nav", "header", "footer", "aside", "form"])
    result = await crawler.arun(url=url, config=config)
    if not result.success:
        raise RuntimeError(result.error_message)
    title = (result.metadata or {}).get("title") or ""
    content = str(result.markdown or "").strip()
    # Chặn trang 404 / Cloudflare challenge / trang rỗng bị lưu như bài thật.
    if "404" in title or "Just a moment" in title or len(content) < 500:
        raise RuntimeError(f"trang lỗi hoặc bị chặn (title={title!r}, {len(content)} ký tự)")
    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Xoá kết quả cũ, nếu không URL crawl lỗi sẽ để lại file của lần chạy trước.
    for old in DATA_DIR.glob("article_*.json"):
        old.unlink()

    # Mở 1 trình duyệt dùng chung cho cả batch thay vì mở/đóng mỗi URL —
    # nhanh hơn nhiều lần và là cách dùng đúng của AsyncWebCrawler.
    async with AsyncWebCrawler() as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            try:
                article = await crawl_article(crawler, url)
                output = DATA_DIR / f"article_{index:02d}.json"
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"Saved: {output}")
            except Exception as error:
                print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())