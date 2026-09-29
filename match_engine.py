"""
match_engine.py
----------------
A simple RULE-BASED possible-match engine (no ML needed for this project level).

For a given "lost" report, it scans all "found" reports and produces a
match score out of 100 based on:
  - Category match          (35 points)
  - Location similarity     (25 points)
  - Date proximity          (20 points)
  - Description keyword overlap (20 points)

This is intentionally simple and explainable -- exactly what a college
project should show: clear logic, not a black box.
"""

from datetime import datetime
import database as db


def _date_proximity_score(date1_str, date2_str, max_days=30):
    """Closer dates score higher. Returns 0-20."""
    try:
        d1 = datetime.strptime(date1_str, "%Y-%m-%d")
        d2 = datetime.strptime(date2_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0

    diff_days = abs((d1 - d2).days)
    if diff_days > max_days:
        return 0
    # Linear decay: 0 days apart = 20 points, max_days apart = 0 points
    return round(20 * (1 - diff_days / max_days), 1)


def _location_score(loc1, loc2):
    """Simple text similarity for location. Returns 0-25."""
    if not loc1 or not loc2:
        return 0
    loc1, loc2 = loc1.lower().strip(), loc2.lower().strip()
    if loc1 == loc2:
        return 25
    # partial match (e.g. "Library" vs "Library 2nd Floor")
    if loc1 in loc2 or loc2 in loc1:
        return 15
    return 0


def _keyword_overlap_score(desc1, desc2):
    """Overlap of significant words between two descriptions. Returns 0-20."""
    if not desc1 or not desc2:
        return 0

    stopwords = {"the", "a", "an", "in", "on", "at", "with", "and", "is",
                 "was", "of", "to", "it", "my", "has", "have", "near"}

    words1 = {w.strip(".,").lower() for w in desc1.split() if w.lower() not in stopwords and len(w) > 2}
    words2 = {w.strip(".,").lower() for w in desc2.split() if w.lower() not in stopwords and len(w) > 2}

    if not words1 or not words2:
        return 0

    overlap = words1 & words2
    union = words1 | words2
    jaccard = len(overlap) / len(union) if union else 0
    return round(20 * jaccard, 1)


def score_pair(lost_item, found_item):
    """Return (score, breakdown_dict) comparing one lost item to one found item."""
    category_score = 35 if lost_item["category"] == found_item["category"] else 0
    location_score = _location_score(lost_item["location"], found_item["location"])
    date_score = _date_proximity_score(lost_item["date_lost_found"], found_item["date_lost_found"])
    keyword_score = _keyword_overlap_score(lost_item["description"], found_item["description"])

    total = category_score + location_score + date_score + keyword_score

    breakdown = {
        "category_score": category_score,
        "location_score": location_score,
        "date_score": date_score,
        "keyword_score": keyword_score,
        "total_score": round(total, 1),
    }
    return round(total, 1), breakdown


def find_matches_for_lost_item(lost_item_id, min_score=25, top_n=5):
    """
    Compare one lost item against all currently unclaimed 'found' items.
    Returns a list of dicts sorted by score (highest first), each containing
    the found item row plus its score breakdown.
    """
    lost_item = db.get_item_by_id(lost_item_id)
    if lost_item is None or lost_item["type"] != "lost":
        return []

    all_items = db.get_all_items()
    found_candidates = [
        i for i in all_items
        if i["type"] == "found" and i["status"] in ("Unclaimed", "Possible Match")
    ]

    results = []
    for found_item in found_candidates:
        score, breakdown = score_pair(lost_item, found_item)
        if score >= min_score:
            results.append({
                "found_item": found_item,
                "score": score,
                "breakdown": breakdown,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_n]


def find_matches_for_found_item(found_item_id, min_score=25, top_n=5):
    """
    The mirror of find_matches_for_lost_item: given a newly reported found
    item, find which open lost reports it might belong to. Used to trigger
    'possible match' notifications for the students who reported those
    lost items.
    """
    found_item = db.get_item_by_id(found_item_id)
    if found_item is None or found_item["type"] != "found":
        return []

    all_items = db.get_all_items()
    lost_candidates = [
        i for i in all_items
        if i["type"] == "lost" and i["status"] in ("Unclaimed", "Possible Match")
    ]

    results = []
    for lost_item in lost_candidates:
        score, breakdown = score_pair(lost_item, found_item)
        if score >= min_score:
            results.append({
                "lost_item": lost_item,
                "score": score,
                "breakdown": breakdown,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_n]


def find_all_possible_matches(min_score=25):
    """
    Scan ALL lost items and return a match list for each, for the
    'Possible Matches' page. Returns a list of:
        {"lost_item": row, "matches": [ {found_item, score, breakdown}, ... ]}
    Only lost items that have at least one match above min_score are included.
    """
    all_items = db.get_all_items()
    lost_items = [i for i in all_items if i["type"] == "lost" and i["status"] != "Claimed"]

    output = []
    for lost_item in lost_items:
        matches = find_matches_for_lost_item(lost_item["item_id"], min_score=min_score)
        if matches:
            output.append({"lost_item": lost_item, "matches": matches})

    return output
