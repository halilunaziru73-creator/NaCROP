"""
concept_figures.py
--------------------
Original, natively-drawn NaCROP conceptual figures -- NOT scans or screenshots of
any third-party document. These replace the earlier "reference figure" section
(which embedded external document pages) with NaCROP's own diagrams of the same
underlying ideas (a calculation-scheme diagram, a water-stress-response curve, an
annotated canopy-cover curve), each one drawn fresh, in NaCROP's own compact
palette, and populated with THIS farm's own computed numbers -- so every user sees
figures specific to their own run, not a fixed, generic set.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

SOIL = "#8a5a34"
CANOPY = "#2e7d4f"
CANOPY_LIGHT = "#a9d8b8"
WATER = "#1f6f8b"
GRAIN = "#c9a227"
INK = "#16241c"
GRID = "#dfe6e2"
CARD = "#f6f8f5"


def _save(fig, name, dpi=200):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_calculation_scheme(result, fname=None):
    """A native NaCROP box-and-arrow diagram of the 4-step calculation scheme,
    each box annotated with THIS run's own computed value -- the NaCROP-drawn
    equivalent of a textbook calculation-scheme figure, specific to this farm."""
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(f"NaCROP Calculation Scheme \u2014 {result.crop_name}",
                 fontsize=15, fontweight="bold", color=INK, pad=10)

    boxes = [
        ("1. Canopy Cover (CC)", f"CC0={result.params['CC0_pct']}%  \u2192  CCx={result.params['CCx_pct']}%",
         CANOPY_LIGHT, CANOPY),
        ("2. Transpiration (Tr)", f"KcTr,x={result.params['KcTr_x']}  \u00d7  CC  \u00d7  ETo",
         "#cfe8ef", WATER),
        ("3. Biomass (B)", f"WP*={result.params['WP_star_g_m2']} g/m\u00b2  \u00d7  \u03a3(Tr/ETo)  \u2192  "
                            f"{result.final_biomass_kg_ha:,.0f} kg/ha", "#ecd9c2", SOIL),
        ("4. Yield (Y)", f"HI={result.actual_hi_pct}%  \u00d7  B  \u2192  {result.yield_kg_ha:,.0f} kg/ha "
                          f"({result.yield_t_ha:.2f} t/ha)", "#f3e3ad", GRAIN),
    ]
    box_w, box_h = 8.4, 1.05
    x0 = (10 - box_w) / 2
    ys = [4.6, 3.15, 1.7, 0.25]
    for (title, detail, fc, ec), y in zip(boxes, ys):
        ax.add_patch(mpatches.FancyBboxPatch((x0, y), box_w, box_h,
                                              boxstyle="round,pad=0.05,rounding_size=0.12",
                                              facecolor=fc, edgecolor=ec, lw=2.4, zorder=2))
        ax.text(x0 + 0.25, y + box_h - 0.28, title, fontsize=13, fontweight="bold", color=INK, va="top")
        ax.text(x0 + 0.25, y + 0.22, detail, fontsize=10.5, color=INK, va="bottom")

    for y_top, y_bot in zip(ys[:-1], ys[1:]):
        arrow = FancyArrowPatch((5, y_top), (5, y_bot + box_h), arrowstyle="-|>",
                                 mutation_scale=22, color=INK, lw=2.2, zorder=3)
        ax.add_artist(arrow)

    fig.text(0.5, 0.01, f"Season length: {result.season_length_days} days   |   "
                        f"Base temperature: {result.params['base_temperature_c']}\u00b0C   |   "
                        f"Farm total yield \u2248 {result.farm_total_yield_kg:,.0f} kg over "
                        f"{result.farm_area_ha:g} ha",
             fontsize=8.5, color="#556", ha="center")

    fname = fname or f"nacrop_calc_scheme_{result.crop_key}.png"
    return _save(fig, fname)


def plot_water_stress_curve(result, p_upper=0.14, fname=None):
    """A native NaCROP water-stress-response curve: Ks (0-1) vs. relative root-zone
    depletion, with this farm's own day-by-day trajectory plotted on top of the
    threshold curve -- shows exactly where this run's own water status sat,
    relative to the stress thresholds, rather than a generic textbook curve alone."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(8.5, 5.2))

    dr = np.linspace(0, 1, 200)
    ks = np.where(dr <= p_upper, 1.0, np.clip(1.0 - (dr - p_upper) / max(1.0 - p_upper, 1e-6), 0, 1))
    ax.plot(dr, ks, color=WATER, lw=2.6, label="Water-stress response curve (Ks)", zorder=3)
    ax.fill_between(dr, 0, ks, color=WATER, alpha=0.08, zorder=1)
    ax.axvline(p_upper, color=SOIL, ls="--", lw=1.8, label=f"Stress threshold (p-upper = {p_upper})")

    # this farm's own trajectory: approximate relative depletion for each day from Ks
    # (Ks==1 -> no stress i.e. depletion<=p_upper; else invert the linear relation)
    days_dr, days_ks = [], []
    for d in result.days:
        k = d.ks_water
        days_ks.append(k)
        days_dr.append(p_upper if k >= 0.999 else min(1.0, p_upper + (1 - k) * (1 - p_upper)))
    ax.scatter(days_dr, days_ks, s=14, color=GRAIN, alpha=0.75, zorder=4,
               label="This farm's own daily water status")

    ax.set_xlabel("Relative root-zone depletion (fraction of Total Available Water)", fontsize=10.5)
    ax.set_ylabel("Water-stress coefficient (Ks)", fontsize=10.5)
    ax.set_title(f"Water-Stress Response \u2014 {result.crop_name}, this farm's own season",
                 fontsize=13, fontweight="bold", color=INK)
    ax.set_xlim(0, 1); ax.set_ylim(-0.02, 1.05)
    ax.legend(fontsize=9, loc="lower left")
    ax.grid(alpha=.3, color=GRID)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    min_ks = min((d.ks_water for d in result.days), default=1.0)
    note = ("No meaningful water stress occurred this season (Ks stayed at 1.0)." if min_ks >= 0.98
            else f"Water stress reached Ks={min_ks:.2f} at its most severe point this season.")
    fig.text(0.5, -0.02, note, fontsize=9, ha="center", color="#556", style="italic")

    fname = fname or f"nacrop_water_stress_{result.crop_key}.png"
    return _save(fig, fname)


def plot_canopy_phases(result, fname=None):
    """A native, annotated canopy-cover curve for this farm's own season: growth,
    maximum cover, and senescence phases clearly labelled with this run's own CC0/
    CCx/CGC/CDC values, rather than a generic unlabelled curve."""
    fig, ax = plt.subplots(figsize=(9, 5.4))
    days = [d.day for d in result.days]
    cc = [d.cc_pct for d in result.days]
    ax.plot(days, cc, color=CANOPY, lw=2.6, zorder=3)
    ax.fill_between(days, 0, cc, color=CANOPY_LIGHT, alpha=0.55, zorder=1)

    max_cc = max(cc) if cc else 1.0
    ax.set_ylim(0, max_cc * 1.28)

    sen = result.stage_boundaries.get("senescence_start_day")
    dev_end = result.stage_boundaries.get("development_end_day")
    if dev_end is not None:
        ax.axvline(dev_end, color=WATER, ls=":", lw=1.6)
        ax.annotate("Canopy expansion\n(CGC = {:.3f}/day)".format(result.params["CGC_per_day"]),
                    xy=(dev_end * 0.5, max_cc * 0.35), fontsize=9, color=INK, ha="center")
    if sen is not None:
        ax.axvline(sen, color=SOIL, ls="--", lw=1.8)
        ax.annotate(f"Maximum cover\nCCx={result.params['CCx_pct']}%",
                    xy=(sen, max_cc * 1.08), fontsize=9, color=INK, ha="center", va="bottom")
        ax.annotate("Senescence\n(CDC = {:.3f}/day)".format(result.params["CDC_per_day"]),
                    xy=((sen + max(days)) / 2 if days else sen, max_cc * 0.3),
                    fontsize=9, color=INK, ha="center")

    ax.set_xlabel("Day of season", fontsize=10.5)
    ax.set_ylabel("Green Canopy Cover (%)", fontsize=10.5)
    ax.set_title(f"Canopy Cover Development \u2014 {result.crop_name} (CC0={result.params['CC0_pct']}%)",
                 fontsize=13, fontweight="bold", color=INK, pad=14)
    ax.grid(alpha=.3, color=GRID)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fname = fname or f"nacrop_canopy_phases_{result.crop_key}.png"
    return _save(fig, fname)
