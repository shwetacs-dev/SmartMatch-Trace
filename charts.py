"""
charts.py
----------
All visualizations, built with matplotlib ONLY (no seaborn).

Colours are chosen to match the app's purple/blue/coral theme, and every
figure uses a soft off-white card background (instead of pure white or
transparent) so charts stay readable and look intentional against the
app's animated backgrounds, rather than clashing with them.

Every function returns a matplotlib Figure object. app.py renders it via
ui_helpers.render_chart_with_insight(), which also adds a real hover
tooltip with a plain-language insight (see chart_insights.py).
"""

import matplotlib.pyplot as plt
import numpy as np

# Palette tuned to match the app's purple/blue/coral CSS theme
COLORS = ["#6a11cb", "#2575fc", "#ff6a88", "#43cea2",
          "#f7971e", "#ff9a8b", "#8e54e9", "#38ada9"]

CARD_BG = "#FBF9FF"  # soft lavender-white "card" background for every chart


def _new_fig(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    return fig, ax


def _style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#555")
    ax.spines["bottom"].set_color("#555")
    ax.grid(axis="y", linestyle="--", alpha=0.35, color="#888")
    ax.set_axisbelow(True)
    ax.tick_params(colors="#333")
    ax.title.set_color("#3a1c71")
    ax.xaxis.label.set_color("#3a1c71")
    ax.yaxis.label.set_color("#3a1c71")


def bar_items_by_category(series):
    fig, ax = _new_fig((7, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    ax.bar(series.index, series.values, color=COLORS[0])
    ax.set_title("Items by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Number of Items")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def pie_claimed_vs_unclaimed(series):
    fig, ax = _new_fig((5.5, 5.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    ax.pie(
        series.values, labels=series.index, autopct="%1.1f%%",
        colors=COLORS[:len(series)], startangle=90,
        wedgeprops={"width": 0.4},
        textprops={"color": "#333"}
    )
    ax.set_title("Item Status Breakdown", color="#3a1c71")
    fig.tight_layout()
    return fig


def line_monthly_trend(series):
    fig, ax = _new_fig((7.5, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    ax.plot(series.index, series.values, marker="o", color=COLORS[3], linewidth=2.2)
    ax.fill_between(range(len(series)), series.values, color=COLORS[3], alpha=0.12)
    ax.set_title("Reports Per Month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of Reports")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def bar_by_location(series):
    fig, ax = _new_fig((7, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    series = series.sort_values()
    ax.barh(series.index, series.values, color=COLORS[1])
    ax.set_title("Reports by Location")
    ax.set_xlabel("Number of Reports")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def heatmap_location_category(pivot_df):
    fig, ax = _new_fig((8, 5.5))
    if pivot_df.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    data = pivot_df.values
    im = ax.imshow(data, cmap="RdPu", aspect="auto")

    ax.set_xticks(np.arange(len(pivot_df.columns)))
    ax.set_yticks(np.arange(len(pivot_df.index)))
    ax.set_xticklabels(pivot_df.columns, rotation=45, ha="right")
    ax.set_yticklabels(pivot_df.index)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            if value > 0:
                ax.text(j, i, int(value), ha="center", va="center",
                        color="black" if value < data.max() / 2 else "white", fontsize=8)

    ax.set_title("Location vs Category Concentration", color="#3a1c71")
    cbar = fig.colorbar(im, ax=ax, label="Number of Items")
    cbar.ax.yaxis.label.set_color("#3a1c71")
    fig.tight_layout()
    return fig


def bar_category_recovery_rate(series):
    fig, ax = _new_fig((7, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    ax.bar(series.index, series.values, color=COLORS[4])
    ax.set_title("Recovery Rate by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Recovery Rate (%)")
    ax.set_ylim(0, 100)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def bar_location_hotspots(series):
    fig, ax = _new_fig((7, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    ax.bar(series.index, series.values, color=COLORS[6])
    ax.set_title("Lost-Item Hotspot Locations")
    ax.set_xlabel("Location")
    ax.set_ylabel("Number of Lost Reports")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def bar_location_prediction(series, category):
    """
    Horizontal bar chart showing the probability (%) breakdown of locations
    for the given category. X-axis is Probability (%), bars are sorted so
    the most likely location sits at the top.
    """
    fig, ax = _new_fig((7, 4.5))
    if series.empty:
        ax.text(0.5, 0.5, "Not enough historical data yet", ha="center", va="center",
                color="#888", fontsize=11)
        ax.set_title(f"Predicted Locations — {category}", color="#3a1c71")
        _style_axes(ax)
        fig.tight_layout()
        return fig

    # Sort ascending so the highest bar is at the top of a horizontal chart
    sorted_series = series.sort_values(ascending=True)

    bars = ax.barh(sorted_series.index, sorted_series.values, color=COLORS[2])

    # Value labels at the end of each bar
    for bar, val in zip(bars, sorted_series.values):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%", va="center", ha="left", fontsize=8, color="#333"
        )

    ax.set_title(f"Predicted Locations — {category}")
    ax.set_xlabel("Historical Probability (%)")
    ax.set_xlim(0, min(sorted_series.max() + 12, 105))

    # Override the y-grid (horizontal chart) to go on x-axis instead
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#555")
    ax.spines["bottom"].set_color("#555")
    ax.grid(axis="x", linestyle="--", alpha=0.35, color="#888")
    ax.set_axisbelow(True)
    ax.tick_params(colors="#333")
    ax.title.set_color("#3a1c71")
    ax.xaxis.label.set_color("#3a1c71")
    ax.yaxis.label.set_color("#3a1c71")

    fig.tight_layout()
    return fig


def bar_day_of_week(series):
    """Bar chart: number of items reported per day of week (Mon–Sun)."""
    fig, ax = _new_fig((7, 4.5))
    if series.empty or series.sum() == 0:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
        return fig

    # Highlight the busiest day
    colors = [COLORS[2] if v == series.max() else COLORS[1] for v in series.values]
    ax.bar(series.index, series.values, color=colors)
    ax.set_title("Reports by Day of Week")
    ax.set_xlabel("Day")
    ax.set_ylabel("Number of Items")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _style_axes(ax)
    fig.tight_layout()
    return fig


def bar_hour_of_day(series):
    """Bar chart: number of items reported per hour of day (0–23)."""
    fig, ax = _new_fig((9, 4.5))
    if series.empty or series.sum() == 0:
        ax.text(0.5, 0.5, "No time data yet", ha="center", va="center")
        return fig

    # Highlight peak hour
    colors = [COLORS[2] if v == series.max() else COLORS[0] for v in series.values]
    ax.bar(series.index, series.values, color=colors, width=0.8)

    # Label only every other hour on x-axis to avoid crowding
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45, ha="right")
    ax.set_title("Reports by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Number of Items")
    _style_axes(ax)
    fig.tight_layout()
    return fig
