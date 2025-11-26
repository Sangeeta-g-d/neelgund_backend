from datetime import datetime
import pytz

def format_datetime_ist(dt):
    """
    Convert UTC datetime to IST and return formatted string.
    If input is None, return None.
    """
    if not dt:
        return None

    # Define UTC and IST timezones
    utc = pytz.utc
    ist = pytz.timezone("Asia/Kolkata")

    # Convert datetime to IST
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    dt_ist = dt.astimezone(ist)

    # Format as '03 Nov 2025, 10:15 AM'
    return dt_ist.strftime("%d %b %Y, %I:%M %p")
