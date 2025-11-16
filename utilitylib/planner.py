from datetime import datetime, timedelta, timezone


'''
Planner class to execute functions at specified time.
Example:
    def greet(name, message): print(f"Hi {name}, {message}")
    
    planner = Planner(utc_time=9)
    planner.add_plan(hour=9, minute=0, buffer=5, func=greet, kwargs={"name": "Alex", "message": "Good morning!"})
    planner.run_schedule()
    -> "Hi Alex, Good morning!" Will be printed if system time is within 09:00-09:05AM
'''
class Planner:
    def __init__(self, utc_time: int = 0):
        '''
        Initialize Planner class with UTC time. 9 for KST.
        '''
        self.timezone = timezone(timedelta(hours=utc_time))
        self.plans = []
    
    def add_plan(self, hour: int, minute: int, buffer: int, func: callable, kwargs: dict = {}):
        '''
        Add plan to execute func if system time is within [hour:minute, hour:minute + buffer] interval.
        '''
        self.plans.append((hour, minute, buffer, func, kwargs))
    
    def run_schedule(self):
        '''
        Run all works in self.plans.
        '''
        current = datetime.now(self.timezone)
        for plan in self.plans:
            hour, minute, buffer, func, kwargs = plan
            start = current.replace(hour=hour, minute=minute)
            end = start + timedelta(minutes=buffer)
            if start <= current <= end:
                func(**kwargs)
                return True
        return False

    def time_str(self, time: datetime, disp_minutes: bool = False):
        '''
        Return time string in format of Korean string.
        Note that 00:00 is "오후 12시" and 12:00 is "오전 12시".
        '''
        hour = time.hour
        minute = time.minute

        hour_text = ""
        if hour == 0: hour_text = "오후 12시"
        elif hour < 12: hour_text = f"오전 {hour}시"
        elif hour == 12: return "오전 12시"
        else: hour_text = f"오후 {hour - 12}시"

        if disp_minutes: return f"{hour_text} {minute}분"
        else: return hour_text
