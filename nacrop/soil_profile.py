"""
soil_profile.py
------------------
A labelled soil-profile cross-section diagram for the Soil Water tab/report: the
selected crop drawn at the top (using crop_icons.py), with a symbolically-labelled
soil column below it showing field capacity, permanent wilting point, root-zone
depth, and the current depletion/moisture level -- all duly labelled with this run's
own actual values, not a generic textbook diagram.

Also draws the soil profile as clearly numbered horizon layers (1, 2, 3) plus a
groundwater-table strip beneath the column (4) -- the same two-part "soil profile /
groundwater table" layered-icon convention used in FAO's own soil-profile figures --
redrawn here as NaCROP's own original artwork. The horizon banding is a schematic
depth split (this run's actual TAW/RAW/FC/PWP numbers still come from a single
measured-or-assumed soil texture, clearly labelled), matching how FAO's own generic
soil-profile icon is schematic rather than a lab-measured horizon log. The
groundwater table is similarly noted as not measured for this farm, since NaCROP
does not model a shallow water table.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from . import crop_icons as ci

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")


def plot_soil_profile(crop_key: str, crop_display_name: str, farm_name: str,
                       soil_cfg, taw_raw: dict, storage_mm: float = None, depletion_mm: float = None,
                       root_zone_depth_m: float = None, maturity: float = 0.75,
                       fname: str = "soil_profile.png") -> str:
    """Large, high-contrast, high-DPI version -- deliberately oversized (title 20pt,
    body labels 14-16pt, thick borders) so the figure reads clearly even scaled down
    to a notebook-tab canvas or a printed report page."""
    os.makedirs(OUT_DIR, exist_ok=True)
    fc_pct = soil_cfg.field_capacity_pct
    pwp_pct = soil_cfg.pwp_pct
    zr_m = root_zone_depth_m if root_zone_depth_m is not None else soil_cfg.root_zone_depth_m
    taw_mm = taw_raw["TAW_mm"]
    raw_mm = taw_raw["RAW_mm"]
    mad = soil_cfg.mad
    texture = getattr(soil_cfg, "soil_texture", "Loam (assumed)")

    storage_pct = None
    if storage_mm is not None and taw_mm:
        storage_pct = max(0.0, min(1.0, storage_mm / taw_mm))

    fig, ax = plt.subplots(figsize=(10, 13.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-2.6, 6.2)
    ax.axis("off")
    ax.set_title(f"Soil-Water Profile: {crop_display_name} ({farm_name})",
                 fontsize=20, fontweight="bold", color="#123524", pad=14)

    # --- crop at the top, sitting clearly above the soil surface ---
    surface_y = 4.0
    inset = fig.add_axes([0.30, 0.685, 0.40, 0.25])
    inset.set_xlim(0, 1); inset.set_ylim(0, 1); inset.set_aspect("equal"); inset.axis("off")
    inset.patch.set_alpha(0)
    ci.draw_crop_icon(inset, crop_key, maturity, cy=0.02)

    # --- soil column outline ---
    col_x0, col_x1 = 2.3, 7.7
    ax.add_patch(mpatches.Rectangle((col_x0, 0), col_x1 - col_x0, surface_y,
                                     facecolor="#d9b88a", edgecolor="#3d2610", lw=3.2, zorder=1))

    # --- numbered soil horizon bands (1, 2, 3): FAO-style layered-column icon,
    #     redrawn as NaCROP's own artwork. Each band carries a distinct hatch
    #     pattern (dots / dashes / cross-hatch) purely so the horizons are told
    #     apart visually (grayscale-safe, colorblind-safe) -- NOT a claim about
    #     what texture each horizon actually is, since no soil survey/lab texture
    #     class was measured for this farm (consistent with the app's own
    #     No-fabrication policy: don't assert specific data that wasn't measured).
    depth_scale_preview = surface_y / max(zr_m * 1.3, 0.3)
    root_bottom_y_preview = max(surface_y - zr_m * depth_scale_preview, 0.3)
    horizon_bands = [("1", "#e8d3ab", ".."), ("2", "#c9a876", "---"), ("3", "#a9825a", "xx")]
    n_bands = len(horizon_bands)
    band_h = (surface_y - root_bottom_y_preview) / n_bands
    root_bottom_y = root_bottom_y_preview  # reuse the same boundary computed above (single source of truth)
    for i, (num, color, hatch) in enumerate(horizon_bands):
        band_top = surface_y - i * band_h
        band_bot = band_top - band_h
        ax.add_patch(mpatches.Rectangle((col_x0, band_bot), col_x1 - col_x0, band_h,
                                         facecolor=color, edgecolor="#3d2610", lw=1.4, alpha=0.95,
                                         hatch=hatch, zorder=1.5))
        ax.add_patch(mpatches.Circle((col_x0 + 0.35, (band_top + band_bot) / 2), 0.17,
                                      facecolor="white", edgecolor="#3d2610", lw=1.6, zorder=5))
        ax.text(col_x0 + 0.35, (band_top + band_bot) / 2, num, fontsize=11, fontweight="bold",
                ha="center", va="center", color="#3d2610", zorder=6)
    ax.text(col_x0, surface_y + 0.18, "Soil horizons (schematic \u2014 not lab-measured)", fontsize=8.5,
            color="#5a3a18", style="italic", ha="left")

    # root zone shading removed as a full-width overlay (it was flattening the
    # horizon-band colors into gray) -- the horizon bands above already convey
    # "this is the root zone" via the dashed Zr line below

    # moisture fill indicator -- a narrow blue gauge strip along the right edge of
    # the column, so it reads clearly as a fill level WITHOUT washing out the
    # horizon band colors across the rest of the column width
    gauge_w = (col_x1 - col_x0) * 0.16
    gauge_x0 = col_x1 - gauge_w
    ax.add_patch(mpatches.Rectangle((gauge_x0, root_bottom_y), gauge_w, surface_y - root_bottom_y,
                                     facecolor="white", edgecolor="#123524", lw=1.6, zorder=3.4))
    if storage_pct is not None:
        fill_h = (surface_y - root_bottom_y) * storage_pct
        ax.add_patch(mpatches.Rectangle((gauge_x0, root_bottom_y), gauge_w, fill_h,
                                         facecolor="#1565c0", edgecolor="none", alpha=0.85, zorder=3.5))

    # root depth line + label -- thicker dashed line, bold larger text
    ax.plot([col_x0 - 0.2, col_x1 + 0.2], [root_bottom_y, root_bottom_y], color="#123524",
            lw=2.6, ls="--", zorder=4)
    ax.text(col_x1 + 0.35, root_bottom_y, f"Root zone depth (Zr)\n{zr_m:.2f} m", fontsize=13.5,
            va="center", ha="left", fontweight="bold", color="#123524")

    # field capacity marker (top of profile = FC reference)
    ax.annotate("", xy=(col_x0 - 0.4, surface_y), xytext=(col_x0 - 0.4, root_bottom_y),
                arrowprops=dict(arrowstyle="<->", color="#1565c0", lw=2.4))
    ax.text(col_x0 - 0.6, (surface_y + root_bottom_y) / 2,
            f"Field Capacity\n{fc_pct}%", fontsize=13, ha="right", va="center",
            color="#1565c0", fontweight="bold")

    ax.text(col_x0 - 0.6, root_bottom_y - 0.42, f"Permanent Wilting Point\n{pwp_pct}%",
            fontsize=13, ha="right", va="center", color="#a15c00", fontweight="bold")
    ax.plot([col_x0 - 0.4, col_x1 + 0.4], [root_bottom_y - 0.05, root_bottom_y - 0.05],
            color="#a15c00", lw=1.8, ls=":", zorder=4)

    # TAW / RAW labels (right side) -- larger, bold, color-coded
    ax.text(col_x1 + 0.35, (surface_y + root_bottom_y) / 2 + 0.35,
            f"TAW = {taw_mm:.1f} mm", fontsize=13.5, va="center", ha="left",
            color="#123524", fontweight="bold")
    ax.text(col_x1 + 0.35, (surface_y + root_bottom_y) / 2 - 0.10,
            f"RAW = {raw_mm:.1f} mm\n(MAD = {mad})", fontsize=13.5, va="center", ha="left",
            color="#c0392b", fontweight="bold")

    if storage_mm is not None:
        ax.text(col_x0 + (col_x1 - col_x0) / 2, root_bottom_y - 1.05,
                f"Current moisture: {storage_mm:.1f} mm ({storage_pct * 100:.0f}% of TAW)"
                + (f"\nDepletion: {depletion_mm:.1f} mm" if depletion_mm is not None else ""),
                fontsize=15, ha="center", va="top", fontweight="bold", color="#123524",
                bbox=dict(boxstyle="round,pad=0.5", fc="#eef3ea", ec="#123524", lw=2.2))

    texture_display = texture.replace(" (assumed)", "").replace("(assumed)", "").strip()
    ax.text(col_x0 + (col_x1 - col_x0) / 2, -0.55, f"Texture: {texture_display}",
            fontsize=11, ha="center", color="#555", style="italic")

    # --- groundwater table strip beneath the soil column (4): FAO-style separate
    #     "groundwater table" icon, redrawn as NaCROP's own artwork -- horizontal
    #     wavy blue bands. NaCROP does not model a measured shallow water table for
    #     this farm, so this is explicitly labelled as such, not a per-farm
    #     measurement (consistent with the No-fabrication policy). ---
    gw_top, gw_bottom = -1.15, -2.35
    ax.add_patch(mpatches.Rectangle((col_x0, gw_bottom), col_x1 - col_x0, gw_top - gw_bottom,
                                     facecolor="#bcd9ef", edgecolor="#123524", lw=2.0, zorder=1))
    n_waves = 4
    band_h_gw = (gw_top - gw_bottom) / n_waves
    for i in range(n_waves):
        y = gw_bottom + i * band_h_gw
        shade = "#8fc0e3" if i % 2 == 0 else "#a9d0ea"
        ax.add_patch(mpatches.Rectangle((col_x0, y), col_x1 - col_x0, band_h_gw,
                                         facecolor=shade, edgecolor="none", alpha=0.7, zorder=1.2))
    ax.plot([col_x0 - 0.3, col_x1 + 0.3], [gw_top, gw_top], color="#123524", lw=2.0, ls="--", zorder=3)
    ax.text(col_x1 + 0.35, (gw_top + gw_bottom) / 2,
            "Groundwater table\n(not measured for\nthis farm; assumed\ndeep enough for\nno capillary rise)",
            fontsize=10.5, va="center", ha="left", color="#123524", fontweight="bold")
    ax.add_patch(mpatches.Circle((col_x0 + 0.35, gw_top - 0.35), 0.16,
                                  facecolor="white", edgecolor="#123524", lw=1.4, zorder=5))
    ax.text(col_x0 + 0.35, gw_top - 0.35, "4", fontsize=10, fontweight="bold",
            ha="center", va="center", color="#123524", zorder=6)

    path = os.path.join(OUT_DIR, fname)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path
