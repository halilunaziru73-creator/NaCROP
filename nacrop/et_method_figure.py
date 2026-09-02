"""
et_method_figure.py
----------------------
Two figures for the ET Methods tab's per-method detail view:

1. plot_method_seasonal_chart -- this specific method's ETo/ETc recomputed across
   the whole season's climatology (not just today), so the user sees its own
   trend shape, not just a single bar.
2. plot_method_soil_column -- a compact soil-column diagram with an
   evapotranspiration arrow sized to THIS method's own predicted mm/day, so the
   physical quantity ("this much water leaving the root zone today, by this
   method") is visible, not just a number in a table.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")

WATER = "#1565c0"
SOIL = "#8a5a34"
CANOPY = "#2e7d4f"
INK = "#16241c"


def plot_method_seasonal_chart(method_name: str, days, eto_series, etc_series, today_idx,
                                fname=None, day_to_month_label=None) -> str:
    """Monthly bar chart (mean ETo/ETc per calendar month for this method), not a
    smooth daily-across-the-season line -- aggregated from the same underlying
    daily values, just grouped by month for a clearer, less noisy read."""
    os.makedirs(OUT_DIR, exist_ok=True)
    from collections import OrderedDict
    monthly_eto, monthly_etc = OrderedDict(), OrderedDict()
    for i, d in enumerate(days):
        label = day_to_month_label(d) if day_to_month_label else f"M{d // 30 + 1}"
        monthly_eto.setdefault(label, []).append(eto_series[i])
        monthly_etc.setdefault(label, []).append(etc_series[i])
    labels = list(monthly_eto.keys())
    eto_means = [sum(v) / len(v) for v in monthly_eto.values()]
    etc_means = [sum(v) / len(v) for v in monthly_etc.values()]
    today_month_label = day_to_month_label(days[today_idx]) if (day_to_month_label and 0 <= today_idx < len(days)) else None

    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = range(len(labels))
    bar_w = 0.38
    bars_eto = ax.bar([i - bar_w / 2 for i in x], eto_means, width=bar_w, color=WATER, label="Mean ETo (mm/day)")
    bars_etc = ax.bar([i + bar_w / 2 for i in x], etc_means, width=bar_w, color=CANOPY, label="Mean ETc (mm/day)")
    if today_month_label in labels:
        idx = labels.index(today_month_label)
        ax.axvspan(idx - 0.5, idx + 0.5, color="#c0392b", alpha=0.08, zorder=0)
        ax.text(idx, max(eto_means + etc_means) * 1.05, "\u2193 this month", ha="center",
                fontsize=8, color="#c0392b", fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0, fontsize=8.5)
    ax.set_ylabel("mm/day", fontsize=9)
    ax.set_title(f"{method_name} \u2014 monthly prediction", fontsize=10, fontweight="bold", color=INK)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    path = os.path.join(OUT_DIR, fname or f"et_method_trend_{method_name.replace(' ', '_').replace('/', '-')}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_method_soil_column(method_name: str, etc_today: float, eto_today: float,
                             root_zone_depth_m: float = 1.0, fname=None) -> str:
    """A compact soil column with an upward ET arrow sized to this specific
    method's own predicted mm/day -- so the number has a visible physical scale."""
    os.makedirs(OUT_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 8)
    ax.axis("off")
    ax.set_title(f"{method_name}\nET leaving the soil column today", fontsize=9.5,
                 fontweight="bold", color=INK)

    col_x0, col_x1 = 2.5, 7.5
    col_top, col_bottom = 4.0, 0.3
    ax.add_patch(mpatches.Rectangle((col_x0, col_bottom), col_x1 - col_x0, col_top - col_bottom,
                                     facecolor="#d9b88a", edgecolor="#3d2610", lw=2.2, zorder=1))
    ax.add_patch(mpatches.Rectangle((col_x0, col_bottom), col_x1 - col_x0,
                                     (col_top - col_bottom) * 0.55,
                                     facecolor=WATER, edgecolor="none", alpha=0.45, zorder=2))
    ax.text((col_x0 + col_x1) / 2, col_bottom - 0.25, f"Root zone ({root_zone_depth_m:.2f} m)",
            fontsize=8, ha="center", color="#555")

    # ET arrow, length scaled to etc_today (clamped to a sensible visual range)
    arrow_len = max(0.6, min(3.2, (etc_today or 0) * 0.5))
    ax.annotate("", xy=((col_x0 + col_x1) / 2, col_top + arrow_len),
                xytext=((col_x0 + col_x1) / 2, col_top + 0.05),
                arrowprops=dict(arrowstyle="-|>", color=WATER, lw=3.2))
    ax.text((col_x0 + col_x1) / 2, col_top + arrow_len + 0.35,
            f"ETc = {etc_today:.2f} mm/day\n(ETo = {eto_today:.2f} mm/day)",
            ha="center", fontsize=9, fontweight="bold", color=INK,
            bbox=dict(boxstyle="round,pad=0.35", fc="#eef3ea", ec=WATER, lw=1.4))

    path = os.path.join(OUT_DIR, fname or f"et_method_soilcol_{method_name.replace(' ', '_').replace('/', '-')}.png")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path
