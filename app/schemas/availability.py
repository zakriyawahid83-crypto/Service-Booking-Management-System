from datetime import date, time

from pydantic import BaseModel, Field, model_validator


class BlockedDateCreate(BaseModel):
    blocked_date: date
    reason: str | None = Field(default=None, max_length=255)


class BlockedDateResponse(BaseModel):
    id: int
    provider_id: int
    blocked_date: date
    reason: str | None

    model_config = {
        "from_attributes": True
    }


class BlockedTimeCreate(BaseModel):
    blocked_date: date
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return self


class BlockedTimeResponse(BaseModel):
    id: int
    provider_id: int
    blocked_date: date
    start_time: time
    end_time: time
    reason: str | None

    model_config = {"from_attributes": True}


class AvailabilityCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    slot_duration: int = Field(default=30, ge=1, le=480)

    @model_validator(mode="after")
    def validate_times(self):

        if self.end_time <= self.start_time:
            raise ValueError(
                "End time must be after start time"
            )

        if (self.break_start is None) != (
            self.break_end is None
        ):
            raise ValueError(
                "Both break_start and break_end are required"
            )

        if self.break_start and self.break_end:

            if self.break_end <= self.break_start:
                raise ValueError(
                    "Break end time must be after break start"
                )

            if self.break_start < self.start_time:
                raise ValueError(
                    "Break must be inside working hours"
                )

            if self.break_end > self.end_time:
                raise ValueError(
                    "Break must be inside working hours"
                )

        return self


class AvailabilityUpdate(BaseModel):
    start_time: time | None = None
    end_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    slot_duration: int | None = Field(default=None, ge=1, le=480)
    is_available: bool | None = None


class AvailabilityResponse(BaseModel):
    id: int
    provider_id: int
    day_of_week: int
    start_time: time
    end_time: time
    break_start: time | None
    break_end: time | None
    slot_duration: int
    is_available: bool

    model_config = {
        "from_attributes": True
    }