from typing import Any, List, Optional, Union

import os
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from utilitylib.finder import CloudFinder
from newsbot_logics import filter_reports_date, unpack_watchlist
from pslib import get_news

finder = CloudFinder("run-sources-timefolionotify-asia-northeast3")
watchlist = finder.load("watchlist.json", local=True)
last_message = finder.load("last_message.json", local=True)

# d6_codes, d8_codes = unpack_watchlist(watchlist)
# print(filter_reports_date("20251112", d8_codes))


def get_news(stock_code: str, timeout: int = 20):
    # Scrapes Naver Finance news for a single company by stock code.
    # Returns a list of dicts with "title", "url", "date" keys.
    session = requests.Session()
    user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Safari/537.36")
    accept_language = "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    
    base_url = "https://finance.naver.com/item"
    
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": accept_language,
        "Referer": base_url + f"/main.naver?code={stock_code}",
    }
    
    main_url = base_url + f"/main.naver?code={stock_code}"
    try: session.get(main_url, headers = {"User-Agent": user_agent, "Accept-Language": accept_language}, timeout=timeout)
    except Exception: pass

    url = base_url + f"/news.naver?code={stock_code}"
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'euc-kr'
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception: return []

    return copy_html_form(soup, "#news_frame")

def copy_html_form(html_or_soup: Union[str, BeautifulSoup], form_selector: str, extra_selectors: Optional[List[str]] = None) -> List[Any]:
    """
    Replicate the DOM serialization logic from ChromeDriver.copy for a BeautifulSoup tree.
    Returns a list of dictionaries describing all nodes matching the provided selectors.
    """
    soup = html_or_soup if isinstance(html_or_soup, BeautifulSoup) else BeautifulSoup(html_or_soup, "html.parser")

    def serialize(node: Tag) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        obj["tag"] = node.name or ""
        obj["text"] = (node.get_text(strip=True) or "") if node else ""
        attributes: dict[str, Any] = {}
        for attr_name, attr_value in node.attrs.items():
            if isinstance(attr_value, list):
                attributes[attr_name] = " ".join(attr_value)
            else:
                attributes[attr_name] = attr_value
        obj["attributes"] = attributes

        non_html_props = {
            "href": node.attrs.get("href"),
            "src": node.attrs.get("src"),
            "value": node.attrs.get("value"),
            "id": node.attrs.get("id"),
            "className": " ".join(node.attrs.get("class", [])) if node.attrs.get("class") else None,
            "name": node.attrs.get("name"),
            "type": node.attrs.get("type"),
        }
        for key, value in non_html_props.items():
            if value not in (None, "", []):
                obj[key] = value

        children: List[dict[str, Any]] = []
        for child in node.children:
            if isinstance(child, Tag):
                children.append(serialize(child))
        obj["children"] = children
        return obj

    selectors: List[str] = [form_selector]
    if extra_selectors:
        selectors.extend(extra_selectors)

    serialized: List[dict[str, Any]] = []
    seen_nodes: set[int] = set()
    for selector in selectors:
        for element in soup.select(selector):
            if not isinstance(element, Tag):
                continue
            element_id = id(element)
            if element_id in seen_nodes:
                continue
            seen_nodes.add(element_id)
            serialized.append(serialize(element))
    return serialized


if __name__ == "__main__":
    print(get_news("270660"))