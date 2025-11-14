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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

# Try to import from config.py if env vars are not set (for local development)
if BOT_TOKEN is None:
    try:
        from config import BOT_TOKEN
    except ImportError:
        logger.warning("BOT_TOKEN not set in environment and config.py not found")
if CHAT_ID is None:
    try:
        from config import CHAT_ID
    except ImportError:
        logger.warning("CHAT_ID not set in environment and config.py not found")
if API_KEY is None:
    try:
        from config import API_KEY
    except ImportError:
        logger.warning("API_KEY not set in environment and config.py not found")

# Validate environment variables - check if they got concatenated (common PowerShell issue)
if BOT_TOKEN and ("CHAT_ID=" in BOT_TOKEN or "API_KEY=" in BOT_TOKEN or "RUNNING_LOCAL=" in BOT_TOKEN):
    logger.error("ERROR: Environment variables appear to be concatenated!")
    logger.error(f"BOT_TOKEN value looks malformed: {BOT_TOKEN[:50]}...")
    logger.error("This usually happens when PowerShell doesn't parse --set-env-vars correctly.")
    logger.error("Try using quotes or update-env-vars instead of set-env-vars")

running_local = os.getenv("RUNNING_LOCAL", "false").lower() == "true"

logger.info(f"Initialized with running_local={running_local}")
logger.info(f"BOT_TOKEN present: {bool(BOT_TOKEN)}")
logger.info(f"CHAT_ID present: {bool(CHAT_ID)}")
logger.info(f"API_KEY present: {bool(API_KEY)}")

# Final validation
if not BOT_TOKEN or not CHAT_ID or not API_KEY:
    logger.error("CRITICAL: Missing required environment variables!")
    logger.error(f"BOT_TOKEN: {'SET' if BOT_TOKEN else 'MISSING'}")
    logger.error(f"CHAT_ID: {'SET' if CHAT_ID else 'MISSING'}")
    logger.error(f"API_KEY: {'SET' if API_KEY else 'MISSING'}")

def run_newsbot():
    try:
        logger.info("=== Starting newsbot execution ===")
        
        logger.info("Step 1: Initializing CloudFinder")
        myCloud = CloudFinder("run-sources-timefolionotify-asia-northeast3")
        
        # Check if we need to reset last_message.json (between 00:00 and 00:05)
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        should_reset = (current_hour == 0 and current_minute <= 5)
        
        if should_reset:
            logger.info("Step 1.5: Resetting last_message.json (time is between 00:00 and 00:05)")
            all_companies = set()
            try:
                watchlist_temp = myCloud.load("watchlist.json", local=running_local)
                if watchlist_temp:
                    d6_codes_temp, _ = unpack_watchlist(watchlist_temp)
                    all_companies = set(d6_codes_temp.keys())
            except:
                pass
            reset_data = {
                "printed_news": {name: [] for name in all_companies} if all_companies else {},
                "printed_reports": {name: [] for name in all_companies} if all_companies else {}
            }
            myCloud.save(reset_data, "last_message.json", local=running_local)
            logger.info("last_message.json reset successfully")
        
        logger.info("Step 2: Loading watchlist.json")
        watchlist = myCloud.load("watchlist.json", local=running_local)
        if not watchlist:
            logger.error("Failed to load watchlist.json")
            return "Error: Failed to load watchlist.json"
        logger.info(f"Watchlist loaded successfully. Companies: {list(watchlist.keys()) if isinstance(watchlist, dict) else 'N/A'}")
        
        logger.info("Step 3: Loading last_message.json")
        last_message = myCloud.load("last_message.json", local=running_local)
        if last_message is False:
            logger.warning("Failed to load last_message.json, using empty dict")
            last_message = {}
        logger.info("Last message loaded successfully")
        
        # Unpack last_message early to use printed_news for deduplication
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
