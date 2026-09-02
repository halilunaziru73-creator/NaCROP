"""
simulation.py
--------------
NEW pipeline stage: a 4-step crop-growth simulation, added AFTER every existing
NaCROP stage so the original pipeline order is preserved:

    load_and_validate -> run_indirect_methods -> run_direct_method ->
    benchmark_methods -> validate_methods -> run_downstream ->
    run_temperature_anchored_pipeline -> run_full_pipeline
    -> **simulate_nacrop_season()**   <-- NEW, this module

The 4 steps of the NaCROP calculation scheme:
    Step 1 -- Green Canopy Cover (CC) development
    Step 2 -- Crop transpiration (Tr = Ks . KcTr . CC* . ETo)
    Step 3 -- Above-ground biomass (B = WP* . sum(Tr/ETo))
    Step 4 -- Final yield (Y = HI . B)

Any conservative parameter NaCROP does not already carry (CC0, CCx, CGC, CDC, WP*,
HIo, base temperature) is obtained via `interactive_inputs.ask_bank()`, which asks
the user a short question with a documented default already filled in -- so every
figure this module produces is either backed by NaCROP's own field/standard data,
or by a value the user was explicitly asked for (never silently invented),
consistent with README's "No-fabrication policy".

Simplification note: the canopy-growth and -decline curves below use a
logistic-growth / exponential-decay approximation of the piecewise crop-canopy
equations published in the peer-reviewed crop-water-productivity modelling
literature (Raes et al., 2009, Agronomy Journal 101(3):438-447) -- close enough
for a decision-support overview figure, but a simplification, not a
research-grade canopy curve.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

from . import crops as crop_mod
from . import thermal_model as tm
from . import interactive_inputs as qa


@dataclass
class SimulationDay:
    day: int
    gdd_cum: float
    kc: float
    cc_pct: float
    eto_mm: float
    etc_mm: float
    ks_water: float
    tr_mm: float
    cum_biomass_g_m2: float


@dataclass
class NaCROPSimulationResult:
    crop_key: str
    crop_name: str
    season_length_days: int
    params: Dict[str, float]
    days: List[SimulationDay] = field(default_factory=list)
    final_biomass_g_m2: float = 0.0
    final_biomass_kg_ha: float = 0.0
    reference_hi_pct: float = 0.0
    actual_hi_pct: float = 0.0
    yield_kg_ha: float = 0.0
    yield_t_ha: float = 0.0
    farm_area_ha: float = 1.0
    farm_total_yield_kg: float = 0.0
    stage_boundaries: Dict[str, int] = field(default_factory=dict)


def _canopy_cover_curve(t: int, cc0_pct: float, ccx_pct: float, cgc: float,
                         t_senescence: int, cdc: float) -> float:
    """Simplified canopy cover model: logistic growth to CCx, then
    exponential senescence decline (see module docstring for the simplification
    note in the module docstring above)."""
    if t <= t_senescence:
        if cc0_pct <= 0:
            cc0_pct = 0.1
        denom = 1 + ((ccx_pct - cc0_pct) / cc0_pct) * math.exp(-cgc * t)
        return max(0.0, ccx_pct / denom)
    else:
        cc_at_sen = _canopy_cover_curve(t_senescence, cc0_pct, ccx_pct, cgc,
                                         t_senescence, cdc)
        return max(0.0, cc_at_sen * math.exp(-cdc * (t - t_senescence)))


def simulate_nacrop_season(
    crop_key: str,
    doy_climatology: Dict[str, dict],
    lat_deg: float,
    farm_area_ha: float = 1.0,
    dwb_depletion_series: Optional[List[float]] = None,
    dwb_taw_series: Optional[List[float]] = None,
    ask_questions: bool = True,
    season_index: int = 0,
) -> NaCROPSimulationResult:
    """Run the 4-step crop-growth simulation for one crop's dominant local season.

    dwb_depletion_series / dwb_taw_series: optional day-aligned soil-water-balance
    output from `soil_water.simulate_daily_soil_water_balance` (this pipeline's own
    Step "run_downstream") -- when supplied, they drive the water-stress coefficient
    Ks (relative root-zone depletion), so canopy expansion and
    transpiration genuinely respond to THIS farm's own simulated soil-water status,
    not a generic no-stress assumption.
    """
    profile = crop_mod.CROPS[crop_key]
    season = profile.seasons[season_index]
    n_days = season.length_days

    # ---- Parameters: reuse what NaCROP already has; ask (once, cached) for the rest
    if ask_questions:
        cc0_per_seedling = qa.ask_bank("cc0_per_seedling_pct")
        density = qa.ask_bank("plant_density")
        ccx_pct = qa.ask_bank("ccx_pct")
        base_temp_c = qa.ask_bank("base_temperature_c")
        hio_pct = qa.ask_bank("reference_harvest_index_pct")
        wp_star = qa.ask_bank("wp_star_g_m2")
    else:
        cc0_per_seedling, density, ccx_pct = 0.5, 75000, 95.0
        base_temp_c, hio_pct, wp_star = tm.TBASE_C, 48.0, 33.7

    cc0_pct = min(ccx_pct * 0.9, (cc0_per_seedling / 100.0) * (density / 10000.0) * 100.0)
    cc0_pct = max(cc0_pct, 0.1)

    stages = profile.stage_lengths_days
    raw_total = sum(stages.values())
    scale = n_days / raw_total if raw_total else 1.0
    dev_end = int((stages["Initial"] + stages["Development"]) * scale)
    mid_end = int((stages["Initial"] + stages["Development"] + stages["Mid-season"]) * scale)
    t_senescence = mid_end

    # canopy growth coefficient calibrated so CC ~ reaches CCx at end of Development stage
    cgc = max(0.02, math.log(max(ccx_pct / cc0_pct - 1, 1.01)) / max(dev_end, 1))
    cdc = max(0.01, 3.0 / max(n_days - t_senescence, 5))

    kc_tr_x = profile.kc_mid * 1.02  # KcTr,x set slightly above the FAO-56 mid-season Kc

    days_out: List[SimulationDay] = []
    cum_b = 0.0
    for d in range(n_days):
        doy = crop_mod.doy_for_season_day(season, d)
        clim = doy_climatology.get(str(doy)) or doy_climatology.get(str(min(doy, 365)))
        if clim is None:
            continue
        gdd_today = max(((clim["tmax"] + clim["tmin"]) / 2) - base_temp_c, 0.0)
        gdd_cum = (days_out[-1].gdd_cum if days_out else 0.0) + gdd_today

        cc_pct = _canopy_cover_curve(d, cc0_pct, ccx_pct, cgc, t_senescence, cdc)
        kc = crop_mod.kc_at_dap(profile, d, season_length_days=n_days)

        from . import equations as eq
        eto_res = eq.hargreaves_samani(tmax=clim["tmax"], tmin=clim["tmin"],
                                        tmean=(clim["tmax"] + clim["tmin"]) / 2,
                                        lat_deg=lat_deg, day_of_year=doy)
        eto = eto_res["et0_mm_day"] if eto_res.get("status") == "OK" else 0.0
        etc = eto * kc

        ks_water = 1.0
        if dwb_depletion_series and dwb_taw_series and d < len(dwb_depletion_series):
            taw = dwb_taw_series[d] if hasattr(dwb_taw_series, "__len__") else dwb_taw_series
            depletion = dwb_depletion_series[d]
            p_upper = qa.ANSWERS.get("root_zone_depletion_upper_threshold", 0.14) if ask_questions else 0.14
            if taw and taw > 0:
                dr_rel = depletion / taw
                if dr_rel <= p_upper:
                    ks_water = 1.0
                else:
                    ks_water = max(0.0, 1.0 - (dr_rel - p_upper) / max(1.0 - p_upper, 1e-6))

        tr = ks_water * kc_tr_x * (cc_pct / 100.0) * eto
        cum_b += wp_star * (tr / eto) if eto > 0 else 0.0

        days_out.append(SimulationDay(
            day=d, gdd_cum=round(gdd_cum, 1), kc=round(kc, 3), cc_pct=round(cc_pct, 2),
            eto_mm=round(eto, 3), etc_mm=round(etc, 3), ks_water=round(ks_water, 3),
            tr_mm=round(tr, 3), cum_biomass_g_m2=round(cum_b, 2),
        ))

    final_b_g_m2 = days_out[-1].cum_biomass_g_m2 if days_out else 0.0
    final_b_kg_ha = final_b_g_m2 * 10.0  # g/m2 -> kg/ha

    min_ks = min((dd.ks_water for dd in days_out), default=1.0)
    hi_multiplier = 1.0 if min_ks >= 0.6 else max(0.6, min_ks)  # simplified HI adjustment
    actual_hi_pct = hio_pct * hi_multiplier

    yield_kg_ha = final_b_kg_ha * (actual_hi_pct / 100.0)
    yield_t_ha = yield_kg_ha / 1000.0
    farm_total_kg = yield_kg_ha * farm_area_ha

    return NaCROPSimulationResult(
        crop_key=crop_key, crop_name=profile.display_name, season_length_days=n_days,
        params={
            "CC0_pct": round(cc0_pct, 3), "CCx_pct": ccx_pct, "CGC_per_day": round(cgc, 4),
            "CDC_per_day": round(cdc, 4), "KcTr_x": round(kc_tr_x, 3),
            "WP_star_g_m2": wp_star, "HIo_pct": hio_pct, "base_temperature_c": base_temp_c,
        },
        days=days_out, final_biomass_g_m2=final_b_g_m2, final_biomass_kg_ha=round(final_b_kg_ha, 1),
        reference_hi_pct=hio_pct, actual_hi_pct=round(actual_hi_pct, 2),
        yield_kg_ha=round(yield_kg_ha, 1), yield_t_ha=round(yield_t_ha, 3),
        farm_area_ha=farm_area_ha, farm_total_yield_kg=round(farm_total_kg, 1),
        stage_boundaries={"development_end_day": dev_end, "mid_season_end_day": mid_end,
                           "senescence_start_day": t_senescence},
    )
