import os
from datetime import datetime
from io import BytesIO

import dotenv
import pandas as pd
import requests

from components.sidebar import convert_week_to_dates
from opd_dashboard.model import Filter

dotenv.load_dotenv()

LINK = os.getenv("LINK")
SHARE_LINK = os.getenv("SHARE_LINK")
SCHEDULE_SHEET = "schedule"
LEAVE_SHEET = "leaves"


class SheetColumns:
    DEPARTMENT = "department"
    PERSON_1 = "person-1"
    PERSON_2 = "person-2"
    ROOM = "room"
    DATE = "date"
    DAY = "day"
    START_TIME = "start-time"
    END_TIME = "end-time"
    REPEAT = "repeat"
    EVERY_NUMBER = "every-number"
    EVERY_PERIOD = "every-period (day, week, month"
    OCCURS_UNTIL_DATE = "occurs until date"


class LeaveColumns:
    PERSON_1 = "person-1"
    FROM = "from"
    TO = "to"

    COLUMNS = [PERSON_1, FROM, TO]


class RoomTableColumns:
    DATE = "date"
    DEPARTMENT = "dept"
    PEOPLE = "people"
    START_TIME = "start-time"
    END_TIME = "end-time"

    COLUMNS = [DATE, DEPARTMENT, PEOPLE, START_TIME, END_TIME]


class ScheduleSheet:
    def __init__(self) -> None:
        self._data = None
        self._leave_data = None

    def refresh_data(self) -> None:
        self._data = None
        self._leave_data = None

    @property
    def leave_data(self) -> pd.DataFrame:
        if self._leave_data is None:
            # Fetch the file from OneDrive
            response = requests.get(LINK)
            response.raise_for_status()
            # Read the Excel file into a DataFrame
            excel_data = pd.read_excel(
                BytesIO(response.content), sheet_name=LEAVE_SHEET
            )
            # drop empty rows
            excel_data = excel_data.dropna(how="all")
            for col in [LeaveColumns.FROM, LeaveColumns.TO]:
                excel_data[col] = pd.to_datetime(excel_data[col])
            self._leave_data = excel_data

        return self._leave_data

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            # Fetch the file from OneDrive
            response = requests.get(LINK)
            response.raise_for_status()  # Check if the request was successful
            # Read the Excel file into a DataFrame
            excel_data = pd.read_excel(
                BytesIO(response.content), sheet_name=SCHEDULE_SHEET
            )
            # drop empty rows
            excel_data = excel_data.dropna(how="all")
            # replace person-2 nulls with empty string
            excel_data[SheetColumns.PERSON_2] = excel_data[
                SheetColumns.PERSON_2
            ].fillna("")
            for col in [SheetColumns.DATE, SheetColumns.OCCURS_UNTIL_DATE]:
                excel_data[col] = pd.to_datetime(excel_data[col])
            self._data = excel_data

        return self._data

    @property
    def departments(self) -> pd.Series:
        return self.data[SheetColumns.DEPARTMENT].unique()

    @property
    def people(self) -> pd.Series:
        return pd.concat(
            [
                self.data[SheetColumns.PERSON_1],
                self.data[SheetColumns.PERSON_2],
            ]
        ).unique()

    @property
    def rooms(self) -> list[str]:
        return [f"OPD-{i}" for i in range(1, 16)]

    def build_room_df_for_week(self, room: str, filter: Filter) -> pd.DataFrame:
        """Given a room and a filter which contains the start and end week,
        return the schedule for that room for the given week."""
        week_start, week_end = convert_week_to_dates(filter.week)
        room_data = self.data[self.data[SheetColumns.ROOM] == room]
        room_df = pd.DataFrame(columns=RoomTableColumns.COLUMNS)

        # for each day of the week, identify who is working on that day and add them to the room_df
        for day in pd.date_range(week_start, week_end, freq="D"):
            day_data = self.get_day_data(room_data, day)
            for _, row in day_data.iterrows():
                extra_row = self.build_room_row(row, day)
                room_df = pd.concat([room_df, extra_row])

            if day_data.empty:
                extra_row = self.build_empty_room_row(day)
                room_df = pd.concat([room_df, extra_row])

        return room_df.reset_index(drop=True)

    def build_empty_room_row(self, day: datetime) -> pd.DataFrame:
        """Return an empty row for a day where no one is working."""
        return pd.DataFrame(
            {
                RoomTableColumns.DATE: day.strftime("%a %Y-%m-%d"),
                RoomTableColumns.DEPARTMENT: None,
                RoomTableColumns.PEOPLE: None,
                RoomTableColumns.START_TIME: None,
                RoomTableColumns.END_TIME: None,
            },
            index=[0],  # Specify an index
        )

    def get_day_data(self, room_data: pd.DataFrame, day: datetime) -> pd.DataFrame:
        """Given a DataFrame with room data and a day, return a DataFrame with the data for that day."""
        return room_data.loc[
            (room_data[SheetColumns.DATE] <= day)
            & (room_data[SheetColumns.OCCURS_UNTIL_DATE] >= day)
            & (room_data[SheetColumns.DAY] == day.strftime("%a"))
        ]

    def build_room_row(self, row: pd.Series, day: datetime) -> pd.DataFrame:
        """Given a row from the schedule sheet and a day, return a DataFrame with the room schedule for that day.

        Also consider leaves on that day."""
        df = pd.DataFrame(
            {
                RoomTableColumns.DATE: day.strftime("%a %Y-%m-%d"),
                RoomTableColumns.DEPARTMENT: row[SheetColumns.DEPARTMENT],
                RoomTableColumns.PEOPLE: f"{row[SheetColumns.PERSON_1]}-{row[SheetColumns.PERSON_2]}",
                RoomTableColumns.START_TIME: row[SheetColumns.START_TIME],
                RoomTableColumns.END_TIME: row[SheetColumns.END_TIME],
            },
            index=[0],  # Specify an index
        )

        self.consider_leaves(df, day)

        return df

    def consider_leaves(self, df: pd.DataFrame, day: datetime) -> None:
        """Given a room df and a day, consider the leaves on that day and update the room df."""
        person_1 = df[RoomTableColumns.PEOPLE].str.split("-")[0][0]
        person_1_leaves = self.leave_data.loc[
            self.leave_data[LeaveColumns.PERSON_1] == person_1
        ]
        for _, row in person_1_leaves.iterrows():
            if row[LeaveColumns.FROM] <= day <= row[LeaveColumns.TO]:
                df[RoomTableColumns.PEOPLE] = f"LEAVE {person_1}"
                df[RoomTableColumns.START_TIME] = None
                df[RoomTableColumns.END_TIME] = None

    def calculate_utilisation(self, room_df: pd.DataFrame) -> float:
        """Given a room df, calculate the utilisation percentage.

        Assume a room is available to work in from 0800 till 2000 and
        0800 till 1300 on Friday. So total hours per week is 6*12 + 5 = 77 hours.
        Loop through the room_df and calculate the total time spent in the room.
        """
        total_time = 0
        for _, row in room_df.iterrows():
            start_time = row[RoomTableColumns.START_TIME]
            end_time = row[RoomTableColumns.END_TIME]
            if start_time is not None and end_time is not None:
                # Convert times to datetime objects for subtraction
                start_datetime = datetime.combine(datetime.today(), start_time)
                end_datetime = datetime.combine(datetime.today(), end_time)

                total_time += (end_datetime - start_datetime).seconds

        seconds_available_in_week = 77 * 3600
        return (total_time / (seconds_available_in_week)) * 100
