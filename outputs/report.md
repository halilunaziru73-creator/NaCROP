# NaCROP — Nigeria Irrigation DSS, Report

## 1. Project Information

| Parameter | Value |
|---|---|
| Location | Samaru, Zaria, Kaduna State, Nigeria |
| Latitude / Elevation | 11.11 N / 686.0 m |
| Crop | Maize |
| Season | 2012-07-01 to 2012-08-31 |

## 2. ET Results, All Methods, Evaluated at the Entered Temperature

| Method | Mean ET0 (mm/d) | Mean ETc (mm/d) | Seasonal ETc (mm) | RMSE | MAE | R2 |
|---|---|---|---|---|---|---|
| Blaney-Criddle | 5.424 | 6.508 | 403.52 | 4.0758 | 3.9708 | 0.1194 |
| Original/Modified Penman (reference table) | 2.115 | 2.538 | 157.33 | 0.0003 | 0.0002 | 1.0 |
| FAO-56 Penman-Monteith (reference Cropwat table) | 2.772 | 3.326 | 206.22 | 1.4983 | 1.1758 | 0.0 |
| Hargreaves-Samani | 4.687 | 5.624 | 348.7 | 3.2129 | 3.0866 | 0.2264 |
| Priestley-Taylor | 3.434 | 4.121 | 255.52 | 2.4139 | 1.7963 | 0.0014 |
| Makkink | 2.159 | 2.591 | 160.65 | 1.3809 | 1.1477 | 0.0014 |
| Turc | 3.594 | 4.313 | 267.39 | 2.4447 | 1.9059 | 0.0022 |
| Dalton-Type Mass Transfer | 0.272 | 0.326 | 20.24 | 2.3993 | 2.2111 | 0.1478 |
| FAO-56 Penman-Monteith (independent calc) | 2.988 | 3.585 | 222.29 | 1.6223 | 1.3128 | 0.0133 |
| ASCE Standardized Penman-Monteith | 2.988 | 3.585 | 222.29 | 1.6223 | 1.3128 | 0.0133 |
| Thornthwaite | None | None | None | None | None | None |

## 3. Soil Water Parameters

| Parameter | Value | Unit |
|---|---|---|
| field_capacity_pct | 28.0 | % |
| pwp_pct | 14.0 | % |
| root_zone_depth_m | 1.0 | m |
| TAW_mm | 140.0 | mm |
| RAW_mm | 91.0 | mm |
| MAD | 0.65 | - |

## 4. Irrigation Schedule (first 15 events shown)

| Day | Net Irrigation (mm) | Gross Irrigation (mm) |
|---|---|---|

## 5. System Efficiency

| Parameter | Result | Unit |
|---|---|---|
| Conveyance efficiency (Ec) | 85.0 | % |
| Distribution efficiency (Ed) | 55.0 | % |
| Application efficiency (Ea) | 57.0 | % |
| Overall efficiency (Ep) | 26.65 | % |

## 6. Seasonal Water Budget

| Component | Value (mm) |
|---|---|
| rainfall_mm | 592.0 |
| effective_rainfall_mm | 146.2 |
| gross_irrigation_mm | 0.0 |
| net_irrigation_mm | 0 |
| ETc_used_mm | 160.6 |
| runoff_mm | 0.0 |
| deep_percolation_mm | 445.9 |
| application_loss_mm | 0.0 |
| root_zone_growth_gain_mm | 0.0 |
| storage_change_mm | -14.5 |
| total_supplied_mm | 592.0 |
| total_used_mm | 160.6 |
| total_lost_mm | 445.9 |
| balance_residual_mm | 0.0 |

## 7. Data Provenance & Methodology

- Every result on this report is anchored to the single temperature you entered.
  All other same-day inputs (RH, wind, sunshine) are the site's own historical climatological
  normal for this position in the growing season, see `thermal_model.py` for the exact method.
- Weather/ET data: the Samaru field weather dataset, Samaru station.
- ET, irrigation-scheduling and efficiency formulas: standard irrigation-engineering relationships.
- Soil FC/PWP, irrigation-system efficiencies and yield are **not present** in the supplied data;
  demonstration/standard-default values are used and flagged `[DEMO]`/`[STANDARD]` in the code.

## 8. Demo Dry-Spell Irrigation-Scheduling Scenario
The 1 Jul-31 Aug 2012 case study is a wet-season window (592 mm rainfall over 62 days) in which rainfall alone met crop demand, so the real-data schedule has **0** triggered irrigation events. To demonstrate the depletion-triggered scheduler mechanics, a `[DEMO/ASSUMED]` zero-rainfall scenario was also run using the same ETc series: it produced **1** irrigation events, averaging every **None** days, total net irrigation **93.0 mm** (gross **163.1 mm**). See `DEMO_dry_spell_irrigation_schedule.csv` and `DEMO_dry_spell_soil_depletion.png`.


## 9. Direct Method (Water Balance)


## 9. Direct Method (Water Balance) — Verified Against 28-Year Dataset
**Status:** OK

Direct water-balance method verified against 10000 daily records (28 years, 2000-01-01 to 2027-05-18): formula reconstruction matches the source data column on 100.0% of days.

| Component | Mean annual (mm) |
|---|---|
| rainfall | 581.3 |
| irrigation | 570.5 |
| capillary_rise | 19.5 |
| runoff | 91.0 |
| deep_percolation | 152.3 |
| storage_change | 187.1 |
| etc_direct | 1153.4 |

Formula reconstruction matches the source data column on **100.0%** of days.


## 10. Method Availability Benchmark
```
FAO-56 Penman-Monteith (independent calc) .. PASS
ASCE Standardized Penman-Monteith ......... PASS
Original/Modified Penman (reference table) .. PASS
Priestley-Taylor .......................... PASS
Makkink ................................... PASS
Turc ...................................... PASS
Hargreaves-Samani ......................... PASS
Thornthwaite .............................. INSUFFICIENT DATA
Blaney-Criddle ............................ PASS
Dalton-Type Mass Transfer ................. PASS
FAO-56 Penman-Monteith (reference Cropwat table) .. PASS
```


## 11. NaCROP Simulation
See `nacrop_simulation_maize.png` and `tables/nacrop_simulation_result.json`. Default crop-science parameters were used (non-interactive CLI run); the GUI's Simulation tab asks for farm-specific values instead.

- Final biomass: **19,164 kg/ha**
- Reference HIo: **48.0%**  |  Actual (stress-adjusted) HI: **48.0%**
- Simulated yield: **9,199 kg/ha** (9.20 t/ha)
