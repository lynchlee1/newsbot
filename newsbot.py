import json
import os
import logging
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
from newsbot_logics import unpack_watchlist, filter_reports_date, build_reports_section_html, unpack_last_message, send_news
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

running_local = True

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
        
        # Print news at 08:00-08:05, 13:00-13:05, or 17:00-17:05
        current_time = datetime.now()
        in_window_8 = current_time.hour == 8 and 0 <= current_time.minute <= 5
        in_window_13 = current_time.hour == 13 and 0 <= current_time.minute <= 5
        in_window_17 = current_time.hour == 17 and 0 <= current_time.minute <= 5

        if in_window_8:
            logger.info(send_news(myCloud, watchlist, BOT_TOKEN, CHAT_ID, last_hour=15))
        elif in_window_13:
            logger.info(send_news(myCloud, watchlist, BOT_TOKEN, CHAT_ID, last_hour=5))
        elif in_window_17:
            logger.info(send_news(myCloud, watchlist, BOT_TOKEN, CHAT_ID, last_hour=4))

        _, printed_reports = unpack_last_message(last_message)

        logger.info("Step 4: Unpacking watchlist")
        d6_codes, d8_codes = unpack_watchlist(watchlist)
        logger.info(f"Unpacked {len(d6_codes)} stock codes")

        logger.info("Step 5: Fetching reports")
        today = datetime.now().strftime("%Y%m%d")
        logger.info(f"Fetching reports for date: {today}")
        reports_by_corp_raw = filter_reports_date(today, d8_codes, dart_api_key=API_KEY)
        reports_by_corp = {name: [report] if report else [] for name, report in reports_by_corp_raw.items()}
        logger.info(f"Fetched reports for {len([r for r in reports_by_corp.values() if r])} companies")

        logger.info("Step 6: Checking for new reports")
        has_new = False
        new_reports_by_corp = {}
        for corp_name, reports_list in reports_by_corp.items():
            if not reports_list: continue
            last_reports = printed_reports.get(corp_name, [])
            last_urls = {item.get('url') for item in last_reports}
            new_items = [item for item in reports_list if item.get('url') not in last_urls]
            if new_items:
                has_new = True
                new_reports_by_corp[corp_name] = new_items
                logger.info(f"New reports found for {corp_name}")

        if has_new:
            logger.info("Step 7: Building message and sending")
            reports_msg, _ = build_reports_section_html(new_reports_by_corp)
            full_msg = reports_msg
            logger.info(f"Report message length: {len(full_msg)} characters")
            
            logger.info("Step 8: Sending Telegram message")
            bot = ChatBot(BOT_TOKEN)
            bot.send_message(CHAT_ID, full_msg)
            logger.info("Telegram message sent successfully")
            
            logger.info("Step 9: Saving last_message.json")
            all_companies = set(d6_codes.keys())
            complete_reports = {name: reports_by_corp.get(name, []) for name in all_companies}
            save_result = myCloud.save({"printed_news": {}, "printed_reports": complete_reports}, "last_message.json", local=running_local)
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
