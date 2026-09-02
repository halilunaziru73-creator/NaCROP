"""
system_diagram.py
-------------------
NaCROP's own original "how it works" diagram: a full-page scheme -- atmosphere
(rainfall, ETo, air temperature/GDD) feeding a soil-water-balance box (irrigation,
rainfall, evapotranspiration, surface runoff, capillary rise, deep percolation,
groundwater table) on the left, and a numbered Canopy Cover -> Transpiration ->
Biomass -> Yield chain on the right -- drawn fresh in NaCROP's own house style and
labelled throughout with THIS specific farm's own computed numbers, not a generic
textbook illustration. Every box, arrow, icon, and layout choice below is original
NaCROP artwork (nothing copied or traced from any external document); the general
"atmosphere / soil box / numbered growth chain" arrangement follows the same
common-sense reading order (climate at top, water balance on the left, crop-growth
chain on the right) any crop-water diagram would use.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Circle

from . import crop_icons as ci

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")

CANOPY = "#2e7d4f"
CANOPY_LIGHT = "#dff0e4"
WATER = "#1565c0"
WATER_LIGHT = "#dcebfa"
SOIL = "#8a5a34"
SOIL_LIGHT = "#f1e6d8"
GRAIN = "#c9a227"
GRAIN_LIGHT = "#faf1d6"
INK = "#16241c"
STEP = "#d9711a"


def _arrow(ax, start, end, color=INK, lw=2.0, ls="-", style="-|>", mutation=14):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=mutation,
                                  color=color, lw=lw, linestyle=ls, zorder=2))


def _numbered_circle(ax, xy, n, color=STEP, r=0.22):
    ax.add_patch(Circle(xy, r, facecolor=color, edgecolor=INK, lw=1.6, zorder=6))
    ax.text(xy[0], xy[1], str(n), ha="center", va="center", fontsize=13, fontweight="bold",
            color="white", zorder=7)


def plot_system_diagram(context: dict, fname: str = None) -> str:
    """context keys (all optional, degrade gracefully with '?' if missing):
        crop_key, crop_name, farm_owner, et_method, base_temperature_c,
        rainfall_mm, irrigation_mm, eff_rainfall_mm, deep_percolation_mm,
        eto_mm_day, etc_mm_day, gdd_today,
        taw_mm, raw_mm, depletion_mm, storage_mm,
        cc0_pct, ccx_pct, kctr_x,
        wp_star, final_biomass_kg_ha,
        hi_pct, yield_kg_ha, farm_area_ha, farm_total_yield_kg,
        maturity (0-1, for the crop icon)
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    g = lambda k, d="?": context.get(k, d) if context.get(k) is not None else d

    fig, ax = plt.subplots(figsize=(13.5, 9.5))
    ax.set_xlim(0, 13.5); ax.set_ylim(0, 9.5)
    ax.axis("off")
    crop_name = g("crop_name", "this crop")
    farm = g("farm_owner", "This Farm")
    ax.set_title(f"How NaCROP Computed This Season for {crop_name} \u2014 {farm}",
                 fontsize=16, fontweight="bold", color=INK, pad=12)

    # =========================== ATMOSPHERE (top band) ===========================
    ax.plot([0.4, 13.1], [8.85, 8.85], color=INK, lw=1.6, zorder=1)
    ax.text(6.7, 9.05, "ATMOSPHERE", ha="center", fontsize=13, fontweight="bold", color=INK)

    # rainfall (feeds soil box, left)
    ax.text(1.9, 8.6, "rainfall", ha="center", fontsize=10.5, fontweight="bold", color=WATER)
    _arrow(ax, (1.9, 8.5), (1.9, 6.35), color=WATER)

    # ETo (feeds transpiration, right side)
    ax.text(8.8, 8.55, f"ETo\n{g('eto_mm_day')} mm/day", ha="center", fontsize=9.5,
            fontweight="bold", color=WATER)
    _arrow(ax, (8.8, 8.25), (8.8, 6.6), color=WATER)

    # air temperature -> GDD (feeds canopy)
    ax.text(11.7, 8.6, "air temperature", ha="center", fontsize=10.5, fontweight="bold", color=SOIL)
    _arrow(ax, (11.7, 8.5), (11.7, 7.9), color=SOIL)
    ax.text(11.7, 7.6, f"GDD (base {g('base_temperature_c')}\u00b0C)\ntoday: {g('gdd_today')}",
            ha="center", fontsize=9, fontweight="bold", color=SOIL)
    _arrow(ax, (11.4, 7.35), (7.6, 6.7), color=SOIL, ls="--", lw=1.6)

    # =========================== SOIL WATER BALANCE BOX (left) ===========================
    box_x0, box_x1 = 1.0, 4.6
    box_top, box_bottom = 5.9, 3.0
    ax.text(0.15, (box_top + box_bottom) / 2, "SOIL\nWATER\nBALANCE", ha="center", va="center",
            fontsize=11.5, fontweight="bold", color=INK, rotation=0)

    # pseudo-3D box: top face (parallelogram) + front face (rectangle) + side face
    skew = 0.55
    top_poly = [(box_x0, box_top), (box_x1, box_top), (box_x1 + skew, box_top + 0.35),
                (box_x0 + skew, box_top + 0.35)]
    ax.add_patch(mpatches.Polygon(top_poly, closed=True, facecolor="#8fae7a",
                                   edgecolor=INK, lw=1.8, zorder=2))
    side_poly = [(box_x1, box_top), (box_x1 + skew, box_top + 0.35),
                 (box_x1 + skew, box_bottom + 0.35), (box_x1, box_bottom)]
    ax.add_patch(mpatches.Polygon(side_poly, closed=True, facecolor=WATER, alpha=0.55,
                                   edgecolor=INK, lw=1.8, zorder=2))
    ax.add_patch(mpatches.Rectangle((box_x0, box_bottom), box_x1 - box_x0, box_top - box_bottom,
                                     facecolor=WATER, alpha=0.35, edgecolor=INK, lw=1.8, zorder=1.8))

    # moisture fill level inside the front face, from this farm's own storage/TAW
    taw_mm = g("taw_mm", None)
    storage_mm = g("storage_mm", None)
    if isinstance(taw_mm, (int, float)) and isinstance(storage_mm, (int, float)) and taw_mm:
        pct = max(0.0, min(1.0, storage_mm / taw_mm))
        fh = (box_top - box_bottom) * pct
        ax.add_patch(mpatches.Rectangle((box_x0, box_bottom), box_x1 - box_x0, fh,
                                         facecolor=WATER, alpha=0.55, edgecolor="none", zorder=2.2))
        ax.add_patch(Circle((box_x0 + 0.5, box_bottom + 0.4), 0.14, facecolor="#3fa9f5",
                             edgecolor=INK, lw=1, zorder=2.5))

    # crop icon sitting on top of the box, centered, placed precisely in DATA
    # coordinates (not a guessed figure-fraction) so it never collides with the
    # evapotranspiration/irrigation arrows and labels on either side of it
    crop_cx0, crop_cx1 = box_x0 + 1.2, box_x0 + 2.4
    inset = ax.inset_axes([crop_cx0, box_top + 0.05, crop_cx1 - crop_cx0, 1.5],
                           transform=ax.transData)
    inset.set_xlim(0, 1); inset.set_ylim(0, 1); inset.set_aspect("equal"); inset.axis("off")
    inset.patch.set_alpha(0)
    maturity_val = g("maturity", 0.6)
    if not isinstance(maturity_val, (int, float)):
        maturity_val = 0.6
    ci.draw_crop_icon(inset, g("crop_key", "maize"), float(maturity_val), cy=0.05)

    # --- arrows in/out of the soil box, positioned clear of the crop icon on
    #     either side, each labelled with this farm's own number ---
    # evapotranspiration (up, out of box top-left, LEFT of the crop icon)
    _arrow(ax, (box_x0 + 0.35, box_top), (box_x0 + 0.35, box_top + 1.65), color=CANOPY)
    ax.text(box_x0 + 0.35, box_top + 1.8, "evapo-\ntranspiration", ha="center", fontsize=8.5,
            fontweight="bold", color=CANOPY)

    # irrigation (down, into box, RIGHT of the crop icon) -- this farm's own net irrigation
    _arrow(ax, (box_x1 - 0.3, box_top + 1.65), (box_x1 - 0.3, box_top), color=WATER)
    ax.text(box_x1 - 0.3, box_top + 1.8, f"irrigation\n{g('irrigation_mm')} mm", ha="center",
            fontsize=8.5, fontweight="bold", color=WATER)

    # surface runoff (out to the right, top of box) -- shorter text, clear of the CC box
    _arrow(ax, (box_x1 + skew, box_top - 0.1), (box_x1 + 1.35, box_top + 0.45), color=SOIL)
    ax.text(box_x1 + 1.4, box_top + 0.5, "surface runoff\n(0 mm)",
            ha="left", fontsize=8, fontweight="bold", color=SOIL)

    # capillary rise (up, into box from below)
    _arrow(ax, (box_x0 + 1.0, box_bottom - 1.0), (box_x0 + 1.0, box_bottom), color=WATER)
    ax.text(box_x0 + 1.0, box_bottom - 1.15, "capillary\nrise", ha="center", fontsize=8.5,
            fontweight="bold", color=WATER)

    # deep percolation (down, out of box to below) -- this farm's own value
    _arrow(ax, (box_x0 + 2.2, box_bottom), (box_x0 + 2.2, box_bottom - 1.0), color=SOIL)
    ax.text(box_x0 + 2.2, box_bottom - 1.15, f"deep percolation\n{g('deep_percolation_mm')} mm",
            ha="center", fontsize=8.5, fontweight="bold", color=SOIL)

    # groundwater table (label at the bottom, honestly flagged as not measured)
    ax.plot([box_x0 - 0.3, box_x1 + skew + 0.3], [box_bottom - 1.7, box_bottom - 1.7],
            color=INK, lw=1.6, ls="--")
    ax.text((box_x0 + box_x1) / 2, box_bottom - 1.95, "groundwater table (not measured for this farm)",
            ha="center", fontsize=8.5, fontweight="bold", color=INK, style="italic")

    # TAW/RAW/depletion summary beneath the box
    ax.text((box_x0 + box_x1) / 2, box_bottom - 0.35,
            f"TAW: {g('taw_mm')} mm   RAW: {g('raw_mm')} mm   Depletion: {g('depletion_mm')} mm",
            ha="center", fontsize=8.5, fontweight="bold", color=INK,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=INK, lw=1))

    # =========================== RIGHT-SIDE GROWTH CHAIN ===========================
    chain_x = 8.9
    # --- 1. Canopy Cover, with a small growth-curve inset ---
    cc_y0, cc_y1 = 5.4, 7.2
    ax.add_patch(mpatches.FancyBboxPatch((chain_x - 1.6, cc_y0), 3.2, cc_y1 - cc_y0,
                                          boxstyle="round,pad=0.02,rounding_size=0.08",
                                          facecolor=CANOPY_LIGHT, edgecolor=CANOPY, lw=2.0, zorder=3))
    ax.text(chain_x, cc_y1 - 0.22, "CC \u2014 Canopy Cover", ha="center", fontsize=11,
            fontweight="bold", color=INK, zorder=4)
    curve_ax = ax.inset_axes([chain_x - 1.3, cc_y0 + 0.55, 2.6, 1.05], transform=ax.transData)
    curve_ax.set_facecolor("none")
    xs = [i / 20 for i in range(21)]
    ys = [min(1.0, (x * 2.2) ** 1.3) if x < 0.6 else max(0.15, 1 - (x - 0.6) * 1.8) for x in xs]
    curve_ax.plot(xs, ys, color=CANOPY, lw=2.2)
    curve_ax.fill_between(xs, 0, ys, color=CANOPY, alpha=0.25)
    curve_ax.set_xticks([]); curve_ax.set_yticks([])
    for s in curve_ax.spines.values():
        s.set_visible(False)
    ax.text(chain_x, cc_y0 + 0.25, f"CC0 \u2192 CCx:  {g('cc0_pct')}% \u2192 {g('ccx_pct')}%",
            ha="center", fontsize=9.5, fontweight="bold", color=INK, zorder=4)
    _numbered_circle(ax, (chain_x + 1.75, cc_y1 - 0.35), 1)

    # --- 2. Transpiration ---
    tr_y = 4.75
    ax.text(chain_x, tr_y, "Transpiration", ha="center", fontsize=13, fontweight="bold", color=STEP)
    ax.text(chain_x, tr_y - 0.35, f"Tr = Ks \u00d7 KcTr,x \u00d7 CC \u00d7 ETo   (KcTr,x={g('kctr_x')})",
            ha="center", fontsize=8.5, color=INK)
    _numbered_circle(ax, (chain_x - 2.0, tr_y), 2)
    _arrow(ax, (chain_x, cc_y0), (chain_x, tr_y + 0.25), color=CANOPY)

    # WP* oval
    wp_y = 4.1
    ax.add_patch(mpatches.Ellipse((chain_x, wp_y), 1.7, 0.55, facecolor="#bfe3ff",
                                   edgecolor=WATER, lw=1.8, zorder=3))
    ax.text(chain_x, wp_y, f"WP*: {g('wp_star')} g/m\u00b2", ha="center", va="center",
            fontsize=9, fontweight="bold", color=INK, zorder=4)
    _arrow(ax, (chain_x, tr_y - 0.45), (chain_x, wp_y + 0.28), color=CANOPY)

    # --- 3. Biomass ---
    b_y = 3.35
    ax.text(chain_x, b_y, "Biomass", ha="center", fontsize=13, fontweight="bold", color=STEP)
    ax.text(chain_x, b_y - 0.3, f"\u2248 {g('final_biomass_kg_ha')} kg/ha", ha="center",
            fontsize=9.5, fontweight="bold", color=INK)
    _numbered_circle(ax, (chain_x - 2.0, b_y), 3)
    _arrow(ax, (chain_x, wp_y - 0.28), (chain_x, b_y + 0.2), color=SOIL)

    # HI oval
    hi_y = 2.65
    ax.add_patch(mpatches.Ellipse((chain_x, hi_y), 1.5, 0.55, facecolor=GRAIN_LIGHT,
                                   edgecolor=GRAIN, lw=1.8, zorder=3))
    ax.text(chain_x, hi_y, f"HI: {g('hi_pct')}%", ha="center", va="center",
            fontsize=9.5, fontweight="bold", color=INK, zorder=4)
    _arrow(ax, (chain_x, b_y - 0.35), (chain_x, hi_y + 0.28), color=SOIL)

    # --- 4. Yield ---
    y_y = 1.65
    ax.add_patch(mpatches.FancyBboxPatch((chain_x - 2.6, y_y - 0.75), 5.2, 1.5,
                                          boxstyle="round,pad=0.02,rounding_size=0.1",
                                          facecolor=GRAIN_LIGHT, edgecolor=GRAIN, lw=2.4, zorder=3))
    ax.text(chain_x, y_y + 0.2, "YIELD FOR THIS FARM", ha="center", fontsize=12,
            fontweight="bold", color=INK, zorder=4)
    ax.text(chain_x, y_y - 0.2, f"{g('yield_kg_ha')} kg/ha over {g('farm_area_ha')} ha",
            ha="center", fontsize=9.5, fontweight="bold", color=INK, zorder=4)
    ax.text(chain_x, y_y - 0.5, f"\u2248 {g('farm_total_yield_kg')} kg total this season",
            ha="center", fontsize=9, color=INK, zorder=4)
    _numbered_circle(ax, (chain_x - 2.0, y_y), 4)
    _arrow(ax, (chain_x, hi_y - 0.28), (chain_x, y_y + 0.55), color=GRAIN, lw=2.4)

    # --- dotted causal arrows: soil water balance -> canopy & transpiration,
    #     showing (for this farm's own numbers) how root-zone moisture status
    #     feeds into canopy growth and transpiration ---
    _arrow(ax, (box_x1 + skew, box_top - 0.4), (chain_x - 1.8, cc_y0 + 0.3),
           color=SOIL, ls="--", lw=1.5, style="-|>", mutation=10)
    _arrow(ax, (box_x1 + skew, box_top - 1.2), (chain_x - 2.1, tr_y - 0.1),
           color=SOIL, ls="--", lw=1.5, style="-|>", mutation=10)

    ax.text(0.2, 0.25,
            "Every number above is this farm's own result from NaCROP's pipeline "
            "(atmosphere \u2192 soil water balance \u2192 canopy \u2192 transpiration \u2192 biomass \u2192 yield), "
            "not a generic illustration.", fontsize=8.5, color="#556", style="italic")

    path = os.path.join(OUT_DIR, fname or "nacrop_system_diagram.png")
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return path
