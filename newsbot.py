import json
import os
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
from newsbot_logics import unpack_watchlist, filter_reports_date, build_reports_section_html, unpack_last_message, send_news, get_korean_time
from utilitylib.telegram import ChatBot
from utilitylib.finder import CloudFinder
from utilitylib.planner import Planner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    try: from config import BOT_TOKEN
    except ImportError: logger.warning("OS variable not found!")

CHAT_ID = os.getenv("CHAT_ID")
if CHAT_ID is None:
    try: from config import CHAT_ID
    except ImportError: logger.warning("OS variable not found!")

API_KEY = os.getenv("API_KEY")
if API_KEY is None:
    try: from config import API_KEY
    except ImportError: logger.warning("OS variable not found!")

running_local = os.getenv("RUNNING_LOCAL", "false").lower() == "true"

app = Flask(__name__)

logger.info("Initializing CloudFinder...")
myCloud = CloudFinder("run-sources-timefolionotify-asia-northeast3")

'''
Define work functions.
'''
def work_reset_last_message():
    try:
        reset_data = {"printed_news": {}, "printed_reports": {}}
        myCloud.save(reset_data, "last_message.json", local=running_local)
        return True
    except Exception as e:
        logger.error(f"Error in work_reset_last_message: {str(e)}")
        return False


def work_send_news(last_hour):
    try:
        watchlist = myCloud.load("watchlist.json", local=running_local)
        send_news(myCloud, watchlist, BOT_TOKEN, CHAT_ID, last_hour=last_hour)
        return True
    except Exception as e:
        logger.error(f"Error in work_send_news: {str(e)}")
        return False


def work_check_reports():
    try:
        watchlist = myCloud.load("watchlist.json", local=running_local)
        last_message = myCloud.load("last_message.json", local=running_local)
        _, printed_reports = unpack_last_message(last_message)
        
        logger.info("Unpacking watchlist")
        d6_codes, d8_codes = unpack_watchlist(watchlist)
        
        logger.info("Fetching reports")
        today = get_korean_time().strftime("%Y%m%d")
        reports_by_corp_raw = filter_reports_date(today, d8_codes, dart_api_key=API_KEY)
        reports_by_corp = {name: [report] if report else [] for name, report in reports_by_corp_raw.items()}
        
        logger.info("Checking for new reports")
        has_new = False
        new_reports_by_corp = {}
        for corp_name, reports_list in reports_by_corp.items():
            if not reports_list:
                continue
            last_reports = printed_reports.get(corp_name, [])
            last_urls = {item.get('url') for item in last_reports if item.get('url')}
            new_items = [item for item in reports_list if item.get('url') and item.get('url') not in last_urls]
            if new_items:
                has_new = True
                new_reports_by_corp[corp_name] = new_items
                logger.info(f"New reports found for {corp_name}: {len(new_items)} report(s)")
        
        if has_new:
            logger.info("Building message and sending")
            reports_msg, _ = build_reports_section_html(new_reports_by_corp)
            full_msg = reports_msg
            
            logger.info("Sending Telegram message")
            bot = ChatBot(BOT_TOKEN)
            bot.send_message(CHAT_ID, full_msg)
            
            logger.info("Saving last_message.json")
            all_companies = set(d6_codes.keys())
            complete_reports = {name: reports_by_corp.get(name, []) for name in all_companies}
            save_result = myCloud.save({"printed_news": {}, "printed_reports": complete_reports}, "last_message.json", local=running_local)
            if not save_result:
                logger.error("Failed to save last_message.json")
            else:
                logger.info("last_message.json saved successfully")
            
            logger.info("=== Report check completed successfully ===")
            return "Message sent successfully"
        else:
            logger.info("No new reports found. Skipping update.")
            return "No new reports found. Skipping update."
    except Exception as e:
        error_msg = f"Error in work_check_reports: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return f"Error: {str(e)}"


def make_planner():
    logger.info("Creating planner...")
    planner = Planner(utc_time=9)
    
    # 00:00: Reset last_message.json
    planner.add_plan(hour=0, minute=0, buffer=5, func=work_reset_last_message, kwargs={})
    
    # 08:00: Send morning news (last 15 hours)
    planner.add_plan(hour=8, minute=0, buffer=5, func=work_send_news, kwargs={"last_hour": 15})
    
    # 13:00: Send afternoon news (last 5 hours)
    planner.add_plan(hour=13, minute=0, buffer=5, func=work_send_news, kwargs={"last_hour": 5})
    
    # 17:00: Send evening news (last 4 hours)
    planner.add_plan(hour=17, minute=0, buffer=5, func=work_send_news, kwargs={"last_hour": 4})
    
    logger.info("Planner configured with all plans")
    return planner


def run_newsbot():
    try:
        logger.info("Starting newsbot execution...")

        # Run scheduled tasks
        planner = make_planner()
        scheduled_executed = planner.run_schedule()
        if scheduled_executed: logger.info("Scheduled task executed")
        else: logger.info("No scheduled task matched current time")

        # Run always-running tasks
        work_check_reports()
        return True

    except Exception as e:
        logger.error(f"Error in run_newsbot: {str(e)}")
        return False


@app.route("/", methods=["GET", "POST"])
def main():
    try:
        result = run_newsbot()
        return result
    except Exception as e:
        error_msg = f"Error in main route: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
