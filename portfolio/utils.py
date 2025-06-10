import calendar
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from dateutil.parser import parse


def is_business_period_end(date=None):
    """
    Fast check if a date is the last business day of week/month/quarter/year.
    Uses only built-in modules for maximum speed (~1-2 microseconds).

    Args:
        date (datetime.date, optional): Date to check. Defaults to today.

    Returns:
        dict: {
            'week': bool,
            'month': bool,
            'quarter': bool,
            'year': bool
        }
    """
    if date is None:
        date = datetime.now().date()
    elif isinstance(date, datetime):
        date = date.date()
    elif isinstance(date, np.datetime64):
        date = pd.to_datetime(date)
    else:
        date = parse(date)

    # Skip if not a business day
    if date.weekday() > 4:  # Saturday=5, Sunday=6
        return {"week": False, "month": False, "quarter": False, "year": False}

    results = {}

    # 1. WEEK END - Check if it's Friday or last business day of week
    results["week"] = date.weekday() == 4  # Friday = 4

    # 2. MONTH END
    last_day_of_month = calendar.monthrange(date.year, date.month)[1]
    last_date_of_month = date.replace(day=last_day_of_month)
    while last_date_of_month.weekday() > 4:
        last_date_of_month -= timedelta(days=1)
    results["month"] = date == last_date_of_month

    # 3. QUARTER END
    quarter_end_months = [3, 6, 9, 12]  # March, June, September, December
    if date.month in quarter_end_months:
        # Same logic as month end, but only for quarter months
        results["quarter"] = results["month"]
    else:
        results["quarter"] = False

    # 4. YEAR END
    if date.month == 12:  # December
        results["year"] = results["month"]
    else:
        results["year"] = False

    return results


def get_last_business_days(year=None):
    """
    Get all last business days for a given year (week/month/quarter/year ends).

    Args:
        year (int, optional): Year to calculate. Defaults to current year.

    Returns:
        dict: Lists of dates for each period type
    """
    if year is None:
        year = datetime.now().year

    results = {"week_ends": [], "month_ends": [], "quarter_ends": [], "year_end": None}

    # Week ends (all Fridays)
    current_date = datetime(year, 1, 1).date()
    while current_date.year == year:
        if current_date.weekday() == 4:  # Friday
            results["week_ends"].append(current_date)
        current_date += timedelta(days=1)

    # Month ends
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        last_date = datetime(year, month, last_day).date()
        while last_date.weekday() > 4:
            last_date -= timedelta(days=1)
        results["month_ends"].append(last_date)

    # Quarter ends (March, June, September, December)
    for month in [3, 6, 9, 12]:
        last_day = calendar.monthrange(year, month)[1]
        last_date = datetime(year, month, last_day).date()
        while last_date.weekday() > 4:
            last_date -= timedelta(days=1)
        results["quarter_ends"].append(last_date)

    # Year end (December)
    results["year_end"] = results["month_ends"][-1]  # Last month end is year end

    return results
    return results
