import re
import os
import requests
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from utilitylib.telegram import ChatBot
from utilitylib.planner import Planner

# Korean timezone (UTC+9)
KST = timezone(timedelta(hours=9))
def get_korean_time():
    return datetime.now(KST)

'''
뉴스 제목 중복 방지, 뉴스 시간 필터링
'''
def get_duplicated_topic_score_list(curr_topic: str, prev_topics: list[str]):
    # Check if the current topic is duplicated with the previous topics.
    def _split_keywords(text): return [t for t in re.split(r"[',\"\s]+", text) if t]
    curr_keywords = set(_split_keywords(curr_topic))
    results = []
    for prev in prev_topics:
        prev_keywords = set(_split_keywords(prev))
        intersection = curr_keywords & prev_keywords
        results.append(len(intersection))
    return results, len(curr_keywords)


def get_duplicated_topic_score(curr_topic: str, prev_topics: list[str]):
    # Check if the current topic is duplicated with the previous topics.
    duplicates, total_keywords = get_duplicated_topic_score_list(curr_topic, prev_topics)
    if len(duplicates) == 0: return 0, total_keywords
    return max(duplicates) / total_keywords, total_keywords


def filter_news_by_time(news_list: list, days: int = 0, hours: int = 0, minutes: int = 0):
    # Get Korean time and convert to naive for comparison (scraped dates are already in Korean time)
    threshold = get_korean_time().replace(tzinfo=None) - timedelta(days=days, hours=hours, minutes=minutes)
    filtered = []
    for news in news_list:
        try:
            news_date = datetime.strptime(news['date'], "%Y.%m.%d %H:%M")
            if news_date >= threshold: filtered.append(news)
        except: pass
    return filtered

'''
데이터 -> 텔레그램 텍스트 변환
'''
def build_reports_section_html(reports_today_by_corp: dict):
    message = f"<b>오늘의 신규 공시입니다.</b>\n"
    total_reports = sum((len(v) for v in reports_today_by_corp.values()), 0)
    if total_reports > 0:
        for corp_name, results in reports_today_by_corp.items():
            if not results: continue
            message += f"[{corp_name}]\n"
            for result in results:
                title = result['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                url_href = result['url'].replace('&', '&amp;').replace('"', '&quot;')
                title = title.rstrip()
                url_href = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + url_href
                message += f"- <a href=\"{url_href}\">{title}</a>\n"
            message += "\n"
    else:
        message += "없음\n\n"
    return message, total_reports


def build_news_section_html(news_today_by_corp: dict):
    message = f"<b>오늘의 신규 뉴스입니다.</b>\n"
    total_news = sum((len(v) for v in news_today_by_corp.values()), 0)
    if total_news > 0:
        for corp_name, results in news_today_by_corp.items():
            if not results:
                continue
            message += f"[{corp_name}]\n"
            for result in results:
                title = result['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                url_href = (result.get('url') or '').replace('&', '&amp;').replace('"', '&quot;')
                if url_href:
                    message += f"- <a href=\"{url_href}\">{title}</a>\n"
                else:
                    message += f"- {title}\n"
            message += "\n"
    else:
        message += "없음\n"
    return message, total_news

'''
공시 데이터 가져오기
'''
def get_reports_date(date, dart_api_key):
    base_url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={dart_api_key}&bgn_de={date}&end_de={date}&page_count=100"
    
    results = []
    page_no = 1
    while True:
        requesting_url = base_url + f"&page_no={page_no}"
        response = requests.get(requesting_url)
        response = response.json()
        if response["status"] != "000": return []

        for report in response["list"]:
            results.append({
                "d8_code": report["corp_code"],
                "title": report["report_nm"],
                "url": report["rcept_no"]
            })
        if page_no == response["total_page"]: break
        else: page_no += 1
    return results

def filter_reports_date(date, watchlist, dart_api_key):
    full_reports = get_reports_date(date, dart_api_key=dart_api_key)

    results = {}
    for report in full_reports:
        for corp_name, d8_code in watchlist.items():
            if report["d8_code"] == d8_code:
                results[corp_name] = report
                break
    return results

'''
뉴스 데이터 가져오기
'''
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

    iframe = soup.select_one("iframe#news_frame")
    if iframe:
        iframe_src = iframe.get("src", "")
        if iframe_src:
            iframe_src = "https://finance.naver.com" + iframe_src
            try:
                resp = session.get(iframe_src, headers=headers, timeout=timeout)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'euc-kr'
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception: pass

    table = soup.select_one("body > div > table.type5")
    if not table: table = soup.select_one("table.type5")
    if not table:
        all_tables = soup.find_all("table", class_="type5")
        if all_tables: table = all_tables[0]
    if not table: return []

    tbody = table.find("tbody")
    if not tbody:
        tbody = table
    if not tbody:
        return []

    items = []
    seen_urls: set[str] = set()

    def normalize_url(href: str):
        href = href.strip()
        if not href or href == "#": return ""
        if href.startswith("http://") or href.startswith("https://"): return href
        if href.startswith("/"): return "https://finance.naver.com" + href
        return "https://finance.naver.com/" + href.lstrip("/")

    def normalize_date(raw: str):
        if not raw: return ""
        cleaned = re.sub(r"\s+", " ", raw).strip()
        try:
            parsed = datetime.strptime(cleaned, "%Y.%m.%d %H:%M")
            return parsed.strftime("%Y.%m.%d %H:%M")
        except ValueError: return cleaned

    for row in tbody.find_all("tr"):
        link_tags = row.select("a.tit")
        if not link_tags: continue

        date_cell = row.find("td", class_="date")
        date_text = normalize_date(date_cell.get_text() if date_cell else "")

        for link in link_tags:
            title_text = link.get_text(strip=True)
            if not title_text: continue

            normalized_href = normalize_url(link.get("href", ""))
            if not normalized_href or normalized_href in seen_urls: continue

            items.append({"title": title_text, "url": normalized_href, "date": date_text})
            seen_urls.add(normalized_href)
    return items

'''
저장된 데이터 구조에 맞게 변환
'''
def unpack_watchlist(watchlist):
    d6_codes = {}
    d8_codes = {}
    for name, code_list in watchlist.items():
        if code_list[0]: d6_codes[name] = code_list[0]
        if code_list[1]: d8_codes[name] = code_list[1]
    return d6_codes, d8_codes

def unpack_last_message(loaded_data):
    printed_news = loaded_data.get("printed_news", {})
    printed_reports = loaded_data.get("printed_reports", {})
    return printed_news, printed_reports


def send_news(myCloud, watchlist, bot_token, chat_id, last_hour):
    d6_codes, _ = unpack_watchlist(watchlist)
    stock_codes = list(d6_codes.values())
    stock_code_to_name = {code: name for name, code in d6_codes.items()}
    with ThreadPoolExecutor() as executor:
        news_results = list(executor.map(get_news, stock_codes))

    now = get_korean_time()
    # Convert to naive for comparison (scraped dates are already in Korean time)
    cutoff = now.replace(tzinfo=None) - timedelta(hours=last_hour)
    news_by_corp = {}
    for idx, news_list in enumerate(news_results):
        corp_name = stock_code_to_name[stock_codes[idx]]
        if not news_list:
            continue
        deduplicated = []
        for news in news_list:
            news_dt = datetime.strptime(news['date'], "%Y.%m.%d %H:%M")
            if news_dt < cutoff:
                continue
            titles = [item['title'] for item in deduplicated]
            score, _ = get_duplicated_topic_score(news['title'], titles)
            if score < 0.3:
                deduplicated.append(news)
        if deduplicated:
            news_by_corp[corp_name] = deduplicated

    if not news_by_corp: return None

    planner = Planner(utc_time=9)
    hour_str = planner.time_str(now)
    header = now.strftime("%Y.%m.%d")
    lines = [f"<b>{header} {hour_str} 뉴스입니다.</b>"]
    for corp_name, news_list in news_by_corp.items():
        lines.append(f"[{corp_name}]")
        for news in news_list:
            title = news['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            url_href = (news.get('url') or '').replace('&', '&amp;').replace('"', '&quot;')
            if url_href:
                lines.append(f"- <a href=\"{url_href}\">{title}</a>")
            else:
                lines.append(f"- {title}")
        lines.append("")

    ChatBot(bot_token).send_message(chat_id, "\n".join(lines).strip())
    return None
