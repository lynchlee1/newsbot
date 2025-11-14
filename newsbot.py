import sys
import traceback

try:
    # Set up GCP authentication first (before importing GCS)
    import gcp_auth
    gcp_auth.setup_gcp_credentials()
    print("NEWSBOT: GCP authentication set up", flush=True)
    
    from os import name
    from datetime import datetime, timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed
    print("NEWSBOT: Imports started...", flush=True)
    from utilitylib.gcshandler import GCS
    print("NEWSBOT: GCS imported", flush=True)
    from pslib import (
        get_news,
        get_reports,
        build_reports_section_html,
        build_news_section_html,
        send_message,
        get_duplicated_topic_score,
        KOR_TIMEZONE,
        unpack_watchlist,
        unpack_last_message,
        inv_get_corp,
        get_corp,
        read_reports,
        read_news,
    )
    print("NEWSBOT: All imports successful", flush=True)
except Exception as e:
    print(f"ERROR: Failed to import modules: {e}", flush=True)
    print(traceback.format_exc(), flush=True)
    sys.exit(1)


def reset_last_message(gcs_project, is_local=False):
    reset_data = {
        "printed_news": {},
        "printed_reports": {},
    }
    gcs_project.save(reset_data, "last_message.json", local=is_local)
    return reset_data

def thread_news(stockcode, loaded_watchlist, printed_news, news_day_length):
    any_changes = False

    corp_name = inv_get_corp(loaded_watchlist, stockcode)
    if not corp_name: 
        return None, None, any_changes

    new_datas = get_news(stockcode)
    new_datas, new_codes = read_news(new_datas)

    old_datas = get_corp(printed_news, corp_name)
    mixed_datas = old_datas.copy() if old_datas else []
    old_urls = set(item.get("url", "") for item in mixed_datas if item.get("url", ""))
    prev_titles = [item.get("title", "") for item in mixed_datas]

    current_time = datetime.now(KOR_TIMEZONE)
    time_threshold = timedelta(days=news_day_length, hours=3, minutes=0)

    for new_data in new_datas:
        date_str = new_data.get("date", "").strip()
        if date_str:
            try:
                item_dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M").replace(tzinfo=KOR_TIMEZONE)
                if current_time - item_dt > time_threshold: continue
            except Exception: continue
        else: continue

        new_url = new_data.get("url", "")
        if new_url in old_urls: continue
        
        score, total_keywords = get_duplicated_topic_score(new_data.get("title", ""), prev_titles)
        if score > 0.33 or total_keywords < 6:
            continue
        any_changes = True
        mixed_datas.append(new_data)
        old_urls.add(new_url)
        prev_titles.append(new_data.get("title", ""))
    
    return corp_name, mixed_datas, any_changes

def thread_report(stockcode, loaded_watchlist, printed_reports, report_day_length):
    any_changes = False

    corp_name = inv_get_corp(loaded_watchlist, stockcode)
    if not corp_name: return None, None, any_changes

    new_datas = get_reports(stockcode, past_days=report_day_length)
    new_datas, new_codes = read_reports(new_datas)

    old_datas = get_corp(printed_reports, corp_name)     
    if old_datas and len(old_datas) > 0:
        old_datas_list = old_datas.copy()
        old_urls = set(item.get("url", "") for item in old_datas if item.get("url"))

    else:
        old_datas_list = []
        old_urls = set()
    
    all_reports = old_datas_list.copy()    
    for new_report in new_datas:
        new_url = new_report.get("url", "")
        if new_url not in old_urls:
            all_reports.append(new_report)
            old_urls.add(new_url)
            any_changes = True
    
    return corp_name, all_reports, any_changes

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("NEWSBOT: Starting execution", flush=True)
    print("=" * 60, flush=True)
    
    report_day_length = 0
    news_day_length = 0
    any_changes_global = False
    is_local = False

    try:
        current_project = GCS("run-sources-timefolionotify-asia-northeast3")
        current_time = datetime.now(KOR_TIMEZONE)
        print(f"NEWSBOT: Current time: {current_time}", flush=True)
        
        if current_time.hour == 0 and current_time.minute < 10:
            print("NEWSBOT: Resetting last_message (midnight reset)", flush=True)
            reset_last_message(current_project, is_local)

        print("NEWSBOT: Loading watchlist.json", flush=True)
        loaded_watchlist = current_project.load("watchlist.json", local=is_local)
        if not loaded_watchlist:
            print("ERROR: Failed to load watchlist.json", flush=True)
            exit(1)
        print(f"NEWSBOT: Loaded watchlist with {len(loaded_watchlist)} companies", flush=True)
        
        news_watchlist, report_watchlist = unpack_watchlist(loaded_watchlist)
        print(f"NEWSBOT: News watchlist: {len(news_watchlist)} codes, Report watchlist: {len(report_watchlist)} codes", flush=True)

        print("NEWSBOT: Loading last_message.json", flush=True)
        last_message = current_project.load("last_message.json", local=is_local)
        if not last_message:
            print("WARNING: last_message.json not found or empty, using empty dict", flush=True)
            last_message = {"printed_news": {}, "printed_reports": {}}
        else:
            print(f"NEWSBOT: Loaded last_message.json successfully", flush=True)
        
        printed_news, printed_reports = unpack_last_message(last_message)
        print(f"NEWSBOT: Previous news: {len(printed_news)} companies, Previous reports: {len(printed_reports)} companies", flush=True)
    except Exception as e:
        print(f"ERROR: Failed to initialize: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        exit(1)

    print("NEWSBOT: Processing news threads...", flush=True)
    news_message_args = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {
            executor.submit(thread_news, code, loaded_watchlist, printed_news, news_day_length): code 
            for code in news_watchlist
        }
        for future in as_completed(future_to_code):
            try:
                corp_name, mixed_datas, any_changes = future.result()
                if any_changes:
                    any_changes_global = True
                    print(f"NEWSBOT: News changes detected for {corp_name}", flush=True)
                if corp_name and mixed_datas is not None:
                    news_message_args[corp_name] = mixed_datas
            except Exception as e:
                print(f"ERROR: Error processing news thread: {e}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                continue
    
    print(f"NEWSBOT: News processing complete. Found {len(news_message_args)} companies with data", flush=True)
    news_message, total_news = build_news_section_html(news_message_args)
    print(f"NEWSBOT: Total news items: {total_news}", flush=True)

    print("NEWSBOT: Processing report threads...", flush=True)
    report_message_args = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {
            executor.submit(thread_report, code, loaded_watchlist, printed_reports, report_day_length): code 
            for code in report_watchlist
        }
        for future in as_completed(future_to_code):
            try:
                corp_name, all_reports, any_changes = future.result()
                if any_changes:
                    any_changes_global = True
                    print(f"NEWSBOT: Report changes detected for {corp_name}", flush=True)
                if corp_name and all_reports is not None:
                    # Include ALL items (old + new) in the message
                    report_message_args[corp_name] = all_reports
            except Exception as e:
                print(f"ERROR: Error processing report thread: {e}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                continue
    
    print(f"NEWSBOT: Report processing complete. Found {len(report_message_args)} companies with data", flush=True)
    report_message, total_reports = build_reports_section_html(report_message_args)
    print(f"NEWSBOT: Total report items: {total_reports}", flush=True)
    
    print("=" * 60, flush=True)
    print(f"NEWSBOT: any_changes_global = {any_changes_global}", flush=True)
    print("=" * 60, flush=True)
    
    if any_changes_global:
        try:
            print("NEWSBOT: Sending Telegram message...", flush=True)
            final_message = news_message + "\n" + report_message
            send_message(final_message)
            print("NEWSBOT: Telegram message sent successfully", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to send Telegram message: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
        
        try:
            print("NEWSBOT: Saving last_message.json to GCS...", flush=True)
            last_message = {"printed_news": {}, "printed_reports": {}}
            last_message["printed_news"] = news_message_args
            last_message["printed_reports"] = report_message_args
            save_result = current_project.save(last_message, "last_message.json", local=is_local)
            if save_result:
                print("NEWSBOT: Successfully saved last_message.json to GCS", flush=True)
            else:
                print("ERROR: Failed to save last_message.json to GCS", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to save last_message.json: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
    else:
        print("NEWSBOT: No changes detected, skipping message send and save", flush=True)
    
    print("=" * 60, flush=True)
    print("NEWSBOT: Execution completed", flush=True)
    print("=" * 60, flush=True)
