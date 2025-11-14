import json
import os
import logging
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
from newsbot_logics import get_news, unpack_watchlist, filter_news_by_time, filter_reports_date, build_news_section_html, build_reports_section_html, unpack_last_message, get_duplicated_topic_score
from utilitylib.telegram import ChatBot
from utilitylib.finder import CloudFinder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")
running_local = os.getenv("RUNNING_LOCAL", "false").lower() == "true"

if BOT_TOKEN is None:
    try: from config import BOT_TOKEN
    except ImportError: logger.warning("OS variable not found!")
if CHAT_ID is None:
    try: from config import CHAT_ID
    except ImportError: logger.warning("OS variable not found!")
if API_KEY is None:
    try: from config import API_KEY
    except ImportError: logger.warning("OS variable not found!")

app = Flask(__name__)
logger.info(f"Initialized with running_local={running_local}")
logger.info(f"BOT_TOKEN present: {bool(BOT_TOKEN)}")
logger.info(f"CHAT_ID present: {bool(CHAT_ID)}")
logger.info(f"API_KEY present: {bool(API_KEY)}")

# def compare(old_dict, old_key, new_dict, new_key, old_dict_is = "ignored"):
#     old_values_list = []
#     for _, corp_prints in old_dict.items():
#         for single_print in corp_prints:
#             old_values_list.append(single_print.get(old_key))
    
#     if old_dict_is == "ignored": 
#         concat_dict = new_dict
#         new_values_list = []
#     elif old_dict_is == "used":
#         concat_dict = {**old_dict, **new_dict}
#         new_values_list = old_values_list.copy()
    
#     for _, corp_prints in concat_dict.items():
#         for single_print in corp_prints:
#             new_values_list.append(single_print.get(new_key))
    
#     is_new_item = False
#     for new_value in new_values_list:
#         if new_value not in old_values_list:
#             is_new_item = True
#             break
    
#     return 

def send_news():
    pass # will be implemented later

def run_newsbot():
    try:
        logger.info("=== Starting newsbot execution ===")
        
        logger.info("Step 1: Initializing CloudFinder")
        myCloud = CloudFinder("run-sources-timefolionotify-asia-northeast3")
        
        # 00:00 - 00:05 : Reset last_message.json
        current_time = datetime.now()
        if current_time.hour == 0 and current_time.minute <= 5:
            reset_data = {"printed_news": {}, "printed_reports": {}}
            myCloud.save(reset_data, "last_message.json", local=running_local)
            logger.info("last_message.json reset successfully")
        
        watchlist = myCloud.load("watchlist.json", local=running_local)
        if not watchlist: return False
        logger.info(f"Watchlist loaded successfully")
        
        last_message = myCloud.load("last_message.json", local=running_local)
        logger.info("Last message loaded successfully")
        
        # 6:30 - 6:35 : Print news
        current_time = datetime.now()
        if current_time.hour == 6 and current_time.minute >=30 and current_time.minute <= 35:
            send_news()


        printed_news, printed_reports = unpack_last_message(last_message)

        logger.info("Step 4: Unpacking watchlist")
        d6_codes, d8_codes = unpack_watchlist(watchlist)
        stock_code_to_name = {code: name for name, code in d6_codes.items()}
        stock_codes = list(d6_codes.values())
        logger.info(f"Unpacked {len(stock_codes)} stock codes")

        logger.info("Step 5: Fetching news for all companies")
        with ThreadPoolExecutor() as executor:
            news_results = list(executor.map(get_news, stock_codes))
        logger.info(f"Fetched news for {len(news_results)} companies")

        logger.info("Step 6: Filtering and deduplicating news")
        news_by_corp = {}
        for i, news_list in enumerate(news_results):
            corp_name = stock_code_to_name[stock_codes[i]]
            filtered = filter_news_by_time(news_list, hours=2)
            if filtered:
                deduplicated = []
                # Get previously printed news titles for this company
                prev_printed_titles = [item.get('title', '') for item in printed_news.get(corp_name, [])]
                for news in filtered:
                    # Check against both newly deduplicated items and previously printed news
                    prev_titles = [item['title'] for item in deduplicated] + prev_printed_titles
                    score, _ = get_duplicated_topic_score(news['title'], prev_titles)
                    if score < 0.3:
                        deduplicated.append(news)
                if deduplicated:
                    news_by_corp[corp_name] = deduplicated
        logger.info(f"Filtered news for {len(news_by_corp)} companies")

        logger.info("Step 7: Fetching reports")
        today = datetime.now().strftime("%Y%m%d")
        logger.info(f"Fetching reports for date: {today}")
        reports_by_corp_raw = filter_reports_date(today, d8_codes, dart_api_key=API_KEY)
        reports_by_corp = {name: [report] if report else [] for name, report in reports_by_corp_raw.items()}
        logger.info(f"Fetched reports for {len([r for r in reports_by_corp.values() if r])} companies")

        logger.info("Step 8: Using previously unpacked last message data")
        # printed_news and printed_reports were already unpacked in Step 3

        logger.info("Step 9: Checking for new content")
        has_new = False
        for corp_name, news_list in news_by_corp.items():
            if not news_list: continue
            last_news = printed_news.get(corp_name, [])
            last_urls = {item.get('url') for item in last_news}
            if any(item.get('url') not in last_urls for item in news_list):
                has_new = True
                logger.info(f"New news found for {corp_name}")
                break

        if not has_new:
            for corp_name, reports_list in reports_by_corp.items():
                if not reports_list: continue
                last_reports = printed_reports.get(corp_name, [])
                last_urls = {item.get('url') for item in last_reports}
                if any(item.get('url') not in last_urls for item in reports_list):
                    has_new = True
                    logger.info(f"New reports found for {corp_name}")
                    break

        if has_new:
            logger.info("Step 10: Building message and sending")
            news_msg, _ = build_news_section_html(news_by_corp)
            reports_msg, _ = build_reports_section_html(reports_by_corp)
            full_msg = news_msg + "\n" + reports_msg
            logger.info(f"Message length: {len(full_msg)} characters")
            
            logger.info("Step 11: Sending Telegram message")
            bot = ChatBot(BOT_TOKEN)
            bot.send_message(CHAT_ID, full_msg)
            logger.info("Telegram message sent successfully")
            
            logger.info("Step 12: Saving last_message.json")
            all_companies = set(d6_codes.keys())
            complete_news = {name: news_by_corp.get(name, []) for name in all_companies}
            complete_reports = {name: reports_by_corp.get(name, []) for name in all_companies}
            save_result = myCloud.save({"printed_news": complete_news, "printed_reports": complete_reports}, "last_message.json", local=running_local)
            if not save_result:
                logger.error("Failed to save last_message.json")
            else:
                logger.info("last_message.json saved successfully")
            
            logger.info("=== Newsbot execution completed successfully ===")
            return "Message sent successfully"
        else:
            logger.info("No new information found. Skipping update.")
            return "No new information found. Skipping update."
            
    except Exception as e:
        error_msg = f"Error in run_newsbot: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return f"Error: {str(e)}"

@app.route("/", methods=["GET", "POST"])
def main():
    try:
        logger.info("=== Received request at / endpoint ===")
        result = run_newsbot()
        logger.info(f"Request completed with result: {result[:100]}...")
        return result
    except Exception as e:
        error_msg = f"Error in main route: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
