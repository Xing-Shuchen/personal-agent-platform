"""Cross-element PageObservation checks shared by extraction and storage."""
from __future__ import annotations

from typing import Any


def _inside(inner: list[float], outer: list[float]) -> bool:
    return (outer[0] <= inner[0] < inner[2] <= outer[2]
            and outer[1] <= inner[1] < inner[3] <= outer[3])


def validate_observation(observation: dict[str, Any]) -> None:
    """Raise ValueError for links or geometry a single-object Schema cannot prove."""
    regions = {page["id"]: page for page in observation["pages"]}
    if len(regions) != len(observation["pages"]):
        raise ValueError("duplicate page region ID")
    elements = observation["printed_regions"] + observation["marks"] + observation["annotations"] + observation["symbols"]
    by_id = {item["id"]: item for item in elements}
    if len(by_id) != len(elements):
        raise ValueError("duplicate detection ID")
    for page in observation["pages"]:
        box = page["bbox"]
        if not (box[0] < box[2] and box[1] < box[3]):
            raise ValueError("zero-area page region")
    printed = {item["id"]: item for item in observation["printed_regions"]}
    for item in elements:
        box = item["bbox"]
        if item["page_region_id"] not in regions or not (box[0] < box[2] and box[1] < box[3]):
            raise ValueError("detection has invalid page or bbox")
        if not _inside(box, regions[item["page_region_id"]]["bbox"]):
            raise ValueError("detection outside its page region")
        for link in item["linked_text_region_ids"]:
            if link not in printed:
                raise ValueError("text link target missing")
            if printed[link]["page_region_id"] != item["page_region_id"]:
                raise ValueError("direct text link crosses page regions")
    for link in observation["links"]:
        if link["from_id"] not in by_id or link["to_id"] not in by_id:
            raise ValueError("observation link target missing")
