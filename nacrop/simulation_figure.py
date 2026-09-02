"""
simulation_figure.py
---------------------
Renders the NaCROP "Simulation" figure: a compact 4-panel scheme --

    Step 1  Green Canopy Cover (CC)
    Step 2  Crop transpiration (Tr)
    Step 3  Above-ground biomass (B, cumulative)
    Step 4  Final yield (Y) -- single summary bar + Harvest Index

drawn natively in NaCROP's own compact palette (soil-brown / canopy-green /
water-blue / grain-gold), all 4 steps tightly stacked in one figure (one PNG) so
the whole scheme reads at a glance, computed specifically for this farm's own crop
and results.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# NaCROP compact palette
SOIL = "#8a5a34"
CANOPY = "#2e7d4f"
CANOPY_LIGHT = "#a9d8b8"
WATER = "#1f6f8b"
GRAIN = "#c9a227"
INK = "#17252a"
GRID = "#dfe6e2"


def plot_nacrop_simulation(result, fname=None):
    """result: nacrop.simulation.NaCROPSimulationResult"""
    days = [d.day for d in result.days]
    cc = [d.cc_pct for d in result.days]
    tr = [d.tr_mm for d in result.days]
    cum_b = [d.cum_biomass_g_m2 for d in result.days]

    fig, axes = plt.subplots(4, 1, figsize=(9, 10.5), sharex=False,
                              gridspec_kw={"height_ratios": [1.1, 1, 1, 0.8]})
    fig.suptitle(f"NaCROP Simulation \u2014 {result.crop_name}\n"
                 f"4-step crop-growth scheme (Canopy Cover \u2192 Transpiration \u2192 Biomass \u2192 Yield)",
                 fontsize=11, color=INK, fontweight="bold")

    sen = result.stage_boundaries.get("senescence_start_day")

    ax = axes[0]
    ax.plot(days, cc, color=CANOPY, lw=2)
    ax.fill_between(days, 0, cc, color=CANOPY_LIGHT, alpha=.6)
    if sen is not None:
        ax.axvline(sen, color=SOIL, ls="--", lw=1, alpha=.7)
        ax.text(sen, max(cc) * 1.02 if cc else 1, "senescence starts", fontsize=7,
                color=SOIL, ha="left", va="bottom")
    ax.set_ylabel("CC (%)", fontsize=9)
    ax.set_title("Step 1 \u2014 Green Canopy Cover development", fontsize=9, loc="left", color=INK)
    ax.grid(alpha=.3, color=GRID)

    ax = axes[1]
    ax.plot(days, tr, color=WATER, lw=1.6)
    ax.fill_between(days, 0, tr, color=WATER, alpha=.15)
    ax.set_ylabel("Tr (mm/day)", fontsize=9)
    ax.set_title("Step 2 \u2014 Crop transpiration  (Tr = Ks \u00d7 KcTr,x \u00d7 CC* \u00d7 ETo)",
                 fontsize=9, loc="left", color=INK)
    ax.grid(alpha=.3, color=GRID)

    ax = axes[2]
    ax.plot(days, cum_b, color=SOIL, lw=2)
    ax.fill_between(days, 0, cum_b, color=SOIL, alpha=.12)
    ax.set_ylabel("B (g/m\u00b2, cum.)", fontsize=9)
    ax.set_xlabel("Day of season", fontsize=9)
    ax.set_title("Step 3 \u2014 Above-ground biomass  (B = WP* \u00d7 \u03a3(Tr/ETo))",
                 fontsize=9, loc="left", color=INK)
    ax.grid(alpha=.3, color=GRID)

    ax = axes[3]
    ax.barh(["Biomass \u2192 Yield"], [result.final_biomass_kg_ha], color=SOIL, alpha=.35,
            label=f"Biomass: {result.final_biomass_kg_ha:,.0f} kg/ha")
    ax.barh(["Biomass \u2192 Yield"], [result.yield_kg_ha], color=GRAIN,
            label=f"Yield: {result.yield_kg_ha:,.0f} kg/ha (HI={result.actual_hi_pct:.0f}%)")
    ax.set_title("Step 4 \u2014 Final yield  (Y = HI \u00d7 B)", fontsize=9, loc="left", color=INK)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlabel("kg / ha", fontsize=9)

    for a in axes:
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)

    fig.text(0.01, 0.005,
              f"Farm area: {result.farm_area_ha:g} ha \u2192 total yield \u2248 "
              f"{result.farm_total_yield_kg:,.0f} kg  |  "
              f"CC0={result.params['CC0_pct']}%  CCx={result.params['CCx_pct']}%  "
              f"WP*={result.params['WP_star_g_m2']} g/m\u00b2  HIo={result.params['HIo_pct']}%  "
              f"Tbase={result.params['base_temperature_c']}\u00b0C",
              fontsize=7, color="#556", ha="left")

    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fname = fname or f"nacrop_simulation_{result.crop_key}.png"
    path = os.path.join(FIG_DIR, fname)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
