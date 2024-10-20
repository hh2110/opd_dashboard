from datetime import date

from pydantic import BaseModel


class Filter(BaseModel):
    start_date: date | None
    end_date: date | None
    week: str | None
    refresh_data: bool = False
