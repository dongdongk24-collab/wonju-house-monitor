import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "public" / "listings.json"

START_URL = "https://new.land.naver.com/complexes?ms=2ACykt,3zVYsY,14&a=APT:ABYG:JGC:PRE&e=RETAIL"
API_URL = "https://new.land.naver.com/api/articles"
API_PATH = "/api/articles"
AUTH_URL = "https://new.land.naver.com/api/auth"
CORTAR_NO = "5113000000"
REAL_ESTATE_TYPES = "APT:OPST"
TRADE_TYPES = "B1:B2"
MAX_DEPOSIT_MANWON = 12000
MAX_MONTHLY_RENT_MANWON = 20


@dataclass(frozen=True)
class Listing:
    article_no: str
    name: str
    trade_type: str
    price_text: str
    deposit_manwon: int | None
    monthly_rent_manwon: int | None
    area: str
    floor: str
    direction: str
    realtor: str
    confirmed_at: str
    link: str


def parse_korean_money_to_manwon(value: str) -> int | None:
    text = value.replace(",", "").replace(" ", "")
    if not text:
        return None

    total = 0
    match = re.search(r"(\d+)억", text)
    if match:
        total += int(match.group(1)) * 10000
        text = text[match.end() :]

    tail = re.search(r"(\d+)", text)
    if tail:
        total += int(tail.group(1))

    return total if total else None


def split_price(price_text: str) -> tuple[int | None, int | None]:
    if "/" in price_text:
        deposit, rent = price_text.split("/", 1)
        return parse_korean_money_to_manwon(deposit), parse_korean_money_to_manwon(rent)
    return parse_korean_money_to_manwon(price_text), None


def matches_budget(listing: Listing) -> bool:
    if listing.deposit_manwon is None:
        return False
    if listing.trade_type == "전세":
        return listing.deposit_manwon <= MAX_DEPOSIT_MANWON
    return (
        listing.deposit_manwon <= MAX_DEPOSIT_MANWON
        and listing.monthly_rent_manwon is not None
        and listing.monthly_rent_manwon <= MAX_MONTHLY_RENT_MANWON
    )


def build_params(page: int) -> dict[str, Any]:
    return {
        "cortarNo": CORTAR_NO,
        "order": "rank",
        "realEstateType": REAL_ESTATE_TYPES,
        "tradeType": TRADE_TYPES,
        "tag": "::::::::",
        "rentPriceMin": 0,
        "rentPriceMax": MAX_MONTHLY_RENT_MANWON,
        "priceMin": 0,
        "priceMax": MAX_DEPOSIT_MANWON,
        "areaMin": 0,
        "areaMax": 900000000,
        "showArticle": "false",
        "sameAddressGroup": "false",
        "priceType": "RETAIL",
        "page": page,
    }


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": START_URL,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        }
    )
    session.get(START_URL, timeout=20)
    auth_response = session.get(AUTH_URL, timeout=20)
    if auth_response.ok:
        token = auth_response.text.strip().strip('"')
        if token:
            session.headers.update({"authorization": f"Bearer {token}"})
    return session


def fetch_page_direct(session: requests.Session, page: int) -> dict[str, Any]:
    response = session.get(API_URL, params=build_params(page), timeout=20)
    if response.status_code == 429:
        raise RuntimeError("HTTP 429")
    response.raise_for_status()
    return response.json()


def fetch_page_in_browser(page_obj: Any, page_no: int) -> dict[str, Any]:
    api_path = f"{API_PATH}?{urlencode(build_params(page_no))}"
    result = page_obj.evaluate(
        """
        async (apiPath) => {
          const response = await fetch(apiPath, {
            headers: { accept: "application/json, text/plain, */*" },
            credentials: "include"
          });
          return { status: response.status, text: await response.text() };
        }
        """,
        api_path,
    )
    if result["status"] == 429:
        raise RuntimeError("네이버가 GitHub Actions 브라우저 조회도 제한했습니다. HTTP 429")
    if result["status"] >= 400:
        raise RuntimeError(f"네이버 응답 오류: HTTP {result['status']} {result['text'][:200]}")
    return json.loads(result["text"])


def listing_from_article(article: dict[str, Any]) -> Listing:
    article_no = str(article.get("articleNo", ""))
    price_text = str(article.get("dealOrWarrantPrc", ""))
    deposit, monthly_rent = split_price(price_text)
    return Listing(
        article_no=article_no,
        name=str(article.get("articleName") or article.get("complexName") or ""),
        trade_type=str(article.get("tradeTypeName", "")),
        price_text=price_text,
        deposit_manwon=deposit,
        monthly_rent_manwon=monthly_rent,
        area=str(article.get("areaName") or article.get("exclusiveAreaName") or ""),
        floor=str(article.get("floorInfo", "")),
        direction=str(article.get("direction", "")),
        realtor=str(article.get("realtorName", "")),
        confirmed_at=str(article.get("articleConfirmYmd", "")),
        link=f"https://new.land.naver.com/articles/{article_no}",
    )


def listings_from_pages(fetcher: Any) -> list[Listing]:
    listings: list[Listing] = []
    page_no = 1
    while True:
        payload = fetcher(page_no)
        articles = payload.get("articleList") or []
        if not articles:
            break

        for article in articles:
            listing = listing_from_article(article)
            if listing.article_no and matches_budget(listing):
                listings.append(listing)

        if not payload.get("isMoreData"):
            break
        page_no += 1
        time.sleep(0.8)
    return listings


def fetch_matching_listings_direct() -> list[Listing]:
    session = make_session()
    return listings_from_pages(lambda page_no: fetch_page_direct(session, page_no))


def fetch_matching_listings_browser() -> list[Listing]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page_obj = context.new_page()
        page_obj.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        page_obj.wait_for_timeout(5000)
        listings = listings_from_pages(lambda page_no: fetch_page_in_browser(page_obj, page_no))
        browser.close()
        return listings


def fetch_matching_listings() -> list[Listing]:
    try:
        return fetch_matching_listings_direct()
    except Exception as direct_error:
        print(f"Direct fetch failed, trying browser fetch: {direct_error}", file=sys.stderr)
        return fetch_matching_listings_browser()


def write_payload(payload: dict[str, Any]) -> None:
    OUTPUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    try:
        listings = fetch_matching_listings()
        payload = {
            "ok": True,
            "checkedAt": checked_at,
            "count": len(listings),
            "filters": {
                "location": "원주시",
                "types": "아파트, 오피스텔",
                "jeonseMax": "1억 2천만 원",
                "banJeonse": "보증금 1억 2천만 원 이하, 월세 20만 원 이하",
            },
            "listings": [asdict(listing) for listing in listings],
        }
        write_payload(payload)
        print(f"Wrote {len(listings)} listings to {OUTPUT_FILE}")
        return 0
    except Exception as exc:
        fail_on_error = os.environ.get("FAIL_ON_FETCH_ERROR") == "1"
        payload = {
            "ok": False,
            "checkedAt": checked_at,
            "count": 0,
            "error": str(exc),
            "listings": [],
        }
        write_payload(payload)
        print(str(exc), file=sys.stderr)
        return 1 if fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
