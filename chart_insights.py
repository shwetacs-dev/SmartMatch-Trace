"""
chart_insights.py
------------------
Generates a short, plain-language insight sentence for each chart, purely
from the same pandas data the chart itself was built from. These strings
are shown as a real hover tooltip on the chart image (via
ui_helpers.render_chart_with_insight) and repeated as a caption underneath.

Kept separate from charts.py so "what the chart draws" and "what the
chart means" are two clearly distinct responsibilities.
"""


def category_insight(series):
    if series.empty:
        return "No category data yet."
    top_cat = series.idxmax()
    top_count = int(series.max())
    total = int(series.sum())
    pct = round(100 * top_count / total, 1) if total else 0
    return f"'{top_cat}' is the most reported category ({top_count} of {total} items, {pct}%)."


def status_insight(series):
    if series.empty:
        return "No status data yet."
    total = int(series.sum())
    claimed = int(series.get("Claimed", 0))
    pct = round(100 * claimed / total, 1) if total else 0
    return f"{claimed} of {total} items ({pct}%) have been successfully claimed so far."


def monthly_trend_insight(series):
    if series.empty or len(series) < 2:
        return "Not enough months of data yet to show a trend."
    first, last = series.iloc[0], series.iloc[-1]
    direction = "risen" if last > first else ("fallen" if last < first else "stayed flat")
    busiest_month = series.idxmax()
    return f"Reports have {direction} since {series.index[0]}; the busiest month was {busiest_month} ({int(series.max())} reports)."


def location_insight(series):
    if series.empty:
        return "No location data yet."
    top_loc = series.idxmax()
    return f"'{top_loc}' has the most reports overall ({int(series.max())})."


def recovery_rate_insight(series):
    if series.empty:
        return "No recovery-rate data yet."
    best = series.idxmax()
    worst = series.idxmin()
    return (f"'{best}' items are recovered most often ({series.max()}%), "
            f"while '{worst}' items are recovered least often ({series.min()}%).")


def hotspot_insight(series):
    if series.empty:
        return "No lost-item location data yet."
    top_loc = series.idxmax()
    return f"'{top_loc}' is the biggest hotspot for lost items ({int(series.max())} reports) -- worth extra signage or a collection point there."


def heatmap_insight(pivot_df):
    if pivot_df.empty:
        return "No data yet for the location/category breakdown."
    max_val = pivot_df.values.max()
    if max_val == 0:
        return "No overlapping location/category data yet."
    loc_idx, cat_idx = divmod(pivot_df.values.argmax(), pivot_df.shape[1])
    loc = pivot_df.index[loc_idx]
    cat = pivot_df.columns[cat_idx]
    return f"'{cat}' items are most concentrated at '{loc}' ({int(max_val)} reports)."


def location_prediction_insight(category: str, series) -> str:
    """
    Returns a plain-language sentence describing the predicted location
    distribution for the given category.

    If the series is empty (not enough historical data), returns a message
    explaining that instead of a misleading prediction.
    """
    if series is None or series.empty:
        return (
            f"Not enough historical data yet to predict locations for "
            f"'{category}' items — fewer than 3 records match this category and type."
        )
    total_records = int(round(series.sum() / 100 * len(series)))  # approximate original count
    top_loc = series.index[0]
    top_pct = series.iloc[0]
    if len(series) >= 2:
        second_loc = series.index[1]
        second_pct = series.iloc[1]
        return (
            f"Based on historical reports, '{category}' items are most often "
            f"associated with '{top_loc}' ({top_pct:.1f}% of the time), "
            f"followed by '{second_loc}' ({second_pct:.1f}%). "
            f"This is a frequency-based prediction from past records, not a trained model."
        )
    return (
        f"Based on historical reports, '{category}' items are most often "
        f"associated with '{top_loc}' ({top_pct:.1f}% of the time). "
        f"This is a frequency-based prediction from past records, not a trained model."
    )


def day_of_week_insight(series) -> str:
    if series is None or series.empty or series.sum() == 0:
        return "No day-of-week data yet."
    busiest_day = series.idxmax()
    busiest_count = int(series.max())
    quietest_day = series.idxmin()
    return (
        f"Most items are reported on **{busiest_day}s** ({busiest_count} reports). "
        f"{quietest_day}s are the quietest day — useful for scheduling desk staffing."
    )


def hour_of_day_insight(series) -> str:
    if series is None or series.empty or series.sum() == 0:
        return "No time-of-day data yet."
    peak_hour = int(series.idxmax())
    peak_count = int(series.max())
    # Group into rough shift bands
    morning   = int(series[6:12].sum())
    afternoon = int(series[12:18].sum())
    evening   = int(series[18:24].sum())
    busiest_band = max(
        ("morning (6am–12pm)", morning),
        ("afternoon (12pm–6pm)", afternoon),
        ("evening (6pm–midnight)", evening),
        key=lambda x: x[1]
    )[0]
    return (
        f"The peak hour for reports is **{peak_hour:02d}:00–{peak_hour+1:02d}:00** "
        f"({peak_count} items). The busiest part of the day overall is the {busiest_band}."
    )
