import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import format_scheduling
from datetime import datetime, timedelta

def debug_formatting():
    # Test with multi-day event input
    inputs = [
        '<2025-04-27 Sun 00:00>--<2025-04-29 Tue 00:00>',  # 2-day
        '<2025-04-27 Sun 00:00>--<2025-04-28 Mon 00:00>'   # 1-day
    ]
    
    for input_str in inputs:
        print("\n" + "="*50)
        output = format_scheduling(input_str)
        
        print(f"Input:  {input_str}")
        print(f"Output: {output}")
        
        if '29' in input_str:
            print(f"Expected for 2-day: <2025-04-27 Sun>--<2025-04-28 Mon>")
        else:
            print(f"Expected for 1-day: <2025-04-27 Sun>")
    
    # Debug date parsing for both examples
    print("\n" + "="*50)
    print("DEBUG DETAILS:")
    
    # 2-day example
    start_date = "2025-04-27"
    start_day = "Sun"
    end_date = "2025-04-29"
    end_day = "Tue"
    
    start_dt = datetime.strptime(f"{start_date}", '%Y-%m-%d')
    end_dt = datetime.strptime(f"{end_date}", '%Y-%m-%d')
    
    print(f"\nTwo-day example: {start_date} to {end_date}")
    print(f"Start date: {start_dt}, weekday: {start_dt.weekday()}")
    print(f"End date: {end_dt}, weekday: {end_dt.weekday()}")
    
    duration = (end_dt - start_dt).days
    print(f"Duration: {duration} days")
    
    adjusted_end_dt = end_dt - timedelta(days=1)
    print(f"Adjusted end date: {adjusted_end_dt}, weekday: {adjusted_end_dt.weekday()}")
    
    # Day of week mapping
    day_map = {
        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'
    }
    
    adjusted_end_day = day_map[adjusted_end_dt.weekday()]
    print(f"Adjusted end day: {adjusted_end_day}")
    
    expected = f"<{start_date} {start_day}>--<{adjusted_end_dt.strftime('%Y-%m-%d')} {adjusted_end_day}>"
    print(f"Constructed output: {expected}")
    
    # 1-day example
    start_date = "2025-04-27"
    start_day = "Sun"
    end_date = "2025-04-28"
    end_day = "Mon"
    
    start_dt = datetime.strptime(f"{start_date}", '%Y-%m-%d')
    end_dt = datetime.strptime(f"{end_date}", '%Y-%m-%d')
    
    print(f"\nOne-day example: {start_date} to {end_date}")
    print(f"Start date: {start_dt}, weekday: {start_dt.weekday()}")
    print(f"End date: {end_dt}, weekday: {end_dt.weekday()}")
    
    duration = (end_dt - start_dt).days
    print(f"Duration: {duration} days")
    
    expected = f"<{start_date} {start_day}>"
    print(f"Constructed output: {expected}")

if __name__ == "__main__":
    debug_formatting()