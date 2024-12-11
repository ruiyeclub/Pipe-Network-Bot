from typing import Literal, TypedDict


ModuleType = Literal["register", "bind_twitter", "farm", "stats"]


class OperationResult(TypedDict):
    identifier: str
    data: str | dict
    status: bool


class StatisticData(TypedDict):
    identifier: str
    points: int
    referral_url: str
    status: bool
