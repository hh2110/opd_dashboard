from streamlit.delta_generator import DeltaGenerator

from opd_dashboard.schedule import SHARE_LINK


def links_page(links_tab: DeltaGenerator) -> None:
    links_tab.write(
        "This is the link to the excel file that contains the schedule and leaves sheets"
        f" that is used to generate the opd dashboard: {SHARE_LINK}"
    )
