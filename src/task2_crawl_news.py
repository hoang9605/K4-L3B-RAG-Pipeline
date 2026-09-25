"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề: Du lịch Việt Nam — lịch trình, địa điểm, ẩm thực, quy định địa phương.
7 URL (đủ dư so với mức tối thiểu 5) trải đều 4 nhóm nội dung trên, để RAG
sau này trả lời được nhiều loại câu hỏi khác nhau.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # Lịch trình / địa điểm
    "https://www.vietnamairlines.com/bh/en/plan-book/travel/travel-guide/places-to-visit-in-hoi-an",
    # Ẩm thực
    "https://www.authenticfoodquest.com/guide-best-food-in-hoi-an-restaurants/",
    "https://www.willflyforfood.net/hoi-an-food-guide/",
    # Lễ hội / văn hóa
    "https://hanoitimes.vn/google-celebrates-hoi-an-lantern-full-moon-festival-45382.html",
    # Quy định địa phương
    "https://hoianheritage.danang.gov.vn/en/news/news-events/announcement-of-the-visiting-in-hoi-an-ancient-town-125.html",
    "https://en.baobacninhtv.vn/hoi-an-launches-tour-group-entry-fees.bbg",
    "https://tuoitrenews.vn/news/ttnewsstyle/20250107/hoi-an-wants-to-offer-free-entry-into-ancient-town-to-more-visitor-groups/83776.html",
    "https://www.google.com/aclk?sa=L&pf=1&ai=DChsSEwj3zfWh6YiXAxXxxDwCHXBTJU4YACICCAEQAxoCc2Y&co=1&ase=2&gclid=Cj0KCQjwlNPVBhCMARIsAPZ5RqjDpYCVbCEFHAG8HtIMHSAB_8_gdTV_eIFYlEp8aVsFirquFiq-tA4aAgbZEALw_wcB&cid=CAAS3gHkaNMkjj8oikgjVzOqiN6IqQOl5tOdiHuSyQB6I3IAnBOYMNRD9dSlGZmd741tKXMzJV-NUXjhMozPp-THwrJiQMO8JP3o_o4h6JZ9_xhJO7kX18C91Q2riOqYj53RKjde4qa31VjBaUHs4ee9Rd4v9UZOBUyQ2agnom96q3Szy1UMwbVy_dgHjnnB7Up1BU6E7RFoVjd5nbElJvQgJE_N_uRQH73W1OF3Ud_rC6uUOvaSDhBrS5XzopEL5cyzmHUmfc7cCgYHOq9DkPFS4bVMMnXMgK1lZDK1uQCLBaM&cce=2&category=acrcp_v1_32&sig=AOD64_25LJSmDkCE52MBeutjSvnDsn_phw&q&nis=4&adurl=https://www.traveloka.com/vi-vn/flight/route/Da-Nang-Hanoi.DAD.HAN?id%3D679491042369133595%26adloc%3Dvi-vn%26kw%3D679491042369133595_%26gmt%3D%26gn%3Dg%26gd%3Dc%26gdm%3D%26gcid%3D723258518310%26gdp%3D%26gdt%3D%26gap%3D%26pc%3D1%26aid%3D169132735817%26wid%3Ddsa-2380471162240%26fid%3D186248776198%26gid%3D9225885%26%26utm_id%3DXlMcZeIC%26ad_id%3D723258518310%26target_id%3Ddsa-2380471162240%26click_id%3DCj0KCQjwlNPVBhCMARIsAPZ5RqjDpYCVbCEFHAG8HtIMHSAB_8_gdTV_eIFYlEp8aVsFirquFiq-tA4aAgbZEALw_wcB%26group_id%3D169132735817%26gad_source%3D1%26gad_campaignid%3D21952212954%26gbraid%3D0AAAAADi60Un3EH4ApdY_rjZhdbKdjQOt6%26gclid%3DCj0KCQjwlNPVBhCMARIsAPZ5RqjDpYCVbCEFHAG8HtIMHSAB_8_gdTV_eIFYlEp8aVsFirquFiq-tA4aAgbZEALw_wcB&ved=2ahUKEwic6-2h6YiXAxXBkuEIHe8rNhMQ0Qx6BAhSEAE",
    "https://www.google.com/aclk?sa=L&ai=DChsSEwj3zfWh6YiXAxXxxDwCHXBTJU4YACICCAEQARoCc2Y&co=1&ase=2&gclid=Cj0KCQjwlNPVBhCMARIsAPZ5Rqg3MlADp5lrkB6frrGYhldeVR-T4yRUS8yM7MtGocwZQPrKKkjfrUAaAov-EALw_wcB&cid=CAAS3gHkaNMkjgfiTH1ht_T0q_KJnnygiZsukkeDjqWPKuq72jD2oq-U9dSlGZmd741tKXMzJV-NUXjhMozPp-THwrJiQMO8JP3o_o4h6JZ9_xhJO7kX18C91Q2riOqYj53RKjde4qa31VjBaUHs4ee9Rd4v9UZOBUyQ2agnom96q3Szy1UMwbVy_dgHjnnB7Up1BU6E7RFoVjd5nbElJvQgJE_N_uRQH73W1OF3Ud_rC6uUOvaSDhBrS5XzopEL5cyzmHUmfc7cCgYHOq9DkPFS4bVMMnXMgK1lZDK1uQCLBaM&cce=2&category=acrcp_v1_32&sig=AOD64_2w01UEyRZJOIP2ENNZy7Di5eXATg&q&nis=4&adurl&ved=2ahUKEwic6-2h6YiXAxXBkuEIHe8rNhMQ0Qx6BAhVEAE",
    "https://vn.trip.com/flights/da-nang-to-hanoi/airfares-dad-han/?locale=vi_vn&curr=vnd&14894&4140937&allianceid=14894&sid=4140960&ppcid=ckid-57159653651_adid-762569813257_akid-kwd-459222965471_adgid-187321771132&utm_source=google&utm_medium=cpc&utm_campaign=22766115578&gad_source=1&gad_campaignid=22766115578&gbraid=0AAAAABn2eFI6pHEp53iN-uqjBRp-n0HHd&gclid=Cj0KCQjwlNPVBhCMARIsAPZ5Rqg3MlADp5lrkB6frrGYhldeVR-T4yRUS8yM7MtGocwZQPrKKkjfrUAaAov-EALw_wcB",


]


async def crawl_article(crawler: AsyncWebCrawler, url: str) -> dict:
    result = await crawler.arun(url=url)
    return {
        "url": url,
        "title": result.metadata.get("title", "Unknown"),
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": result.markdown,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

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