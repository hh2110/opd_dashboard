import streamlit as st

from components.links_page import links_page
from components.schedule_page import schedule_page
from components.sidebar import filter_sidebar
from opd_dashboard.model import Filter

st.set_page_config(layout="wide")

if "filter" not in st.session_state:
    st.session_state["filter"] = Filter(start_date=None, end_date=None, week=None)

filter_sidebar(st.session_state.filter)

schedule_tab, links_tab = st.tabs(["Schedule", "Links"])

schedule_page(scheduler_tab=schedule_tab, filter=st.session_state.filter)
links_page(links_tab)
