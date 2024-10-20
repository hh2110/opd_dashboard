from streamlit.delta_generator import DeltaGenerator

from opd_dashboard.model import Filter
from opd_dashboard.schedule import RoomTableColumns, ScheduleSheet


def schedule_page(scheduler_tab: DeltaGenerator, filter: Filter):
    # Create columns
    col1, col2 = scheduler_tab.columns(2)
    # Fetch the schedule data
    schedule = ScheduleSheet()
    rooms = schedule.rooms
    # refresh data if needed
    if filter.refresh_data:
        schedule.refresh_data()
        filter.refresh_data = False
    # Write the same DataFrame into both columns
    for room in rooms[0 : len(rooms) // 2]:
        build_row(col1, schedule, room, filter)
    for room in rooms[len(rooms) // 2 :]:
        build_row(col2, schedule, room, filter)


def build_row(
    col: DeltaGenerator, schedule: ScheduleSheet, room: str, filter: Filter
) -> None:
    df_ = schedule.build_room_df_for_week(room, filter)
    unique_departments = [
        dept for dept in df_[RoomTableColumns.DEPARTMENT].unique() if dept is not None
    ]
    utilisation = schedule.calculate_utilisation(df_)
    col.subheader(f"{room} {', '.join(unique_departments)}")
    col.write(f"Utilisation: {utilisation:.1f}%")
    col.dataframe(df_, hide_index=True, width=500)
