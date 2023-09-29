from datetime import datetime
import simpy
from typing import Dict
from globals import CELL_SIZE
import json


def scales_to_str(scales: Dict[str, float]) -> str:

    scales_str: str = None

    if scales["OVERALL"] is not None:

        print(f"{scales['OVERALL']}, type: {type(scales['OVERALL'])}")

        scales_str = f"(_,_,{scales['OVERALL']:.3f})"

    else:
        scales_str = f"({scales['CLIENT']:.3f},{scales['SERVER']:.3f},_)"

    return scales_str


def record_emission(data: Dict[int, int], time_: int) -> None:

    # add data point
    if time_ in data:
        # TODO only count payload as sent data?
        # print("Interval exists, incrementing!")
        data[time_] += CELL_SIZE
    else:
        data.update({time_: CELL_SIZE})


def write_emissions_to_file(filename: str, data: Dict[int, int]) -> None:

    # write back to file
    with open(filename, "w") as f:
        json.dump(data, f)


class Message():

    content: bytes = None
    created: datetime = None
    sent: datetime = None

    def __init__(self, content: bytes, env: simpy.Environment) -> None:
        self.content = content
        self.created = env.now
