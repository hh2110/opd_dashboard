from datetime import date, datetime, timedelta

import streamlit as st

from opd_dashboard.model import Filter

DATE_FORMAT = "%Y-%m-%d"


def filter_sidebar(filter: Filter) -> None:
    with st.sidebar:
        st.title("Filters")
        filter.start_date = st.date_input("Start date")
        filter.end_date = st.date_input("End date", value=datetime(2024, 12, 31).date())
        filter.week = st.selectbox(
            "Week", create_week_list(filter.start_date, filter.end_date)
        )
        filter.refresh_data = st.button("Refresh excel data")


def create_week_list(start_date: date, end_date: date) -> list[str]:
    """
    Returns a list of strings with format `%b-%d till %b-%d`.

    The weeks must start on a Saturday and end on a Friday.
    Therefore, we need to find the Saturday before the start date
    and the Friday after the end date.
    """
    while start_date.weekday() != 5:
        start_date = start_date - timedelta(days=1)
    while end_date.weekday() != 4:
        end_date = end_date + timedelta(days=1)
    week_list = []
    while start_date < end_date:
        week_end = start_date + timedelta(days=6)
        week_list.append(
            f"{start_date.strftime(DATE_FORMAT)} till {week_end.strftime(DATE_FORMAT)}"
        )
        start_date = start_date + timedelta(days=7)

    return week_list


def convert_week_to_dates(week: str) -> tuple[date, date]:
    """
    Converts a week string to a tuple of start and end dates.
    """
    week_start, week_end = week.split(" till ")
    week_start = datetime.strptime(week_start, DATE_FORMAT).date()
    week_end = datetime.strptime(week_end, DATE_FORMAT).date()

    return week_start, week_end
