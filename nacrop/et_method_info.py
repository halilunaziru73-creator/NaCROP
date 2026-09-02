"""
et_method_info.py
--------------------
A knowledge base of each ET method's governing equation, input variables, and a
short description -- used by the ET Methods tab's per-method detail view. Every
equation below is the standard, published form of that method (FAO-56 Irrigation
and Drainage Paper 56; Priestley & Taylor 1972; Makkink 1957; Turc 1961;
Hargreaves & Samani 1985; Thornthwaite 1948; Blaney & Criddle 1950; Dalton 1802
mass-transfer form) -- the same equations implemented in nacrop/equations.py.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class MethodInfo:
    key: str
    display_name: str
    equation: str
    variables: List[str] = field(default_factory=list)
    description: str = ""


METHOD_INFO = {
    "FAO-56 Penman-Monteith": MethodInfo(
        key="fao56_penman_monteith", display_name="FAO-56 Penman-Monteith",
        equation="ETo = [0.408\u0394(Rn\u2212G) + \u03b3(900/(T+273))u\u2082(es\u2212ea)] / [\u0394 + \u03b3(1+0.34u\u2082)]",
        variables=["Rn: net radiation (MJ/m\u00b2/day)", "G: soil heat flux (MJ/m\u00b2/day)",
                   "T: mean air temperature (\u00b0C)", "u\u2082: wind speed at 2m (m/s)",
                   "es\u2212ea: vapour pressure deficit (kPa)", "\u0394: slope of vapour pressure curve",
                   "\u03b3: psychrometric constant"],
        description="The internationally standardized reference-crop method (FAO Irrigation and "
                    "Drainage Paper 56) -- combines an energy-balance term with an aerodynamic "
                    "(vapour-transport) term over a hypothetical well-watered grass reference."),
    "ASCE Standardized Penman-Monteith": MethodInfo(
        key="asce_penman_monteith", display_name="ASCE Standardized Penman-Monteith",
        equation="ETo = [0.408\u0394(Rn\u2212G) + \u03b3(Cn/(T+273))u\u2082(es\u2212ea)] / [\u0394 + \u03b3(1+Cd\u00b7u\u2082)]",
        variables=["Rn: net radiation (MJ/m\u00b2/day)", "G: soil heat flux (MJ/m\u00b2/day)",
                   "Cn, Cd: reference-type constants (grass, daily timestep)",
                   "u\u2082: wind speed at 2m (m/s)", "es\u2212ea: vapour pressure deficit (kPa)"],
        description="The ASCE-EWRI standardized form of Penman-Monteith -- numerically very close to "
                    "FAO-56 for the daily grass reference, with slightly different reference-specific "
                    "constants (Cn, Cd)."),
    "Original/Modified Penman": MethodInfo(
        key="field_ref_penman", display_name="Original/Modified Penman",
        equation="ET = [\u0394\u00b7Rn + \u03b3\u00b7Ea] / (\u0394+\u03b3),   Ea = 0.26(1+0.54u\u2082)(es\u2212ea)",
        variables=["Rn: net radiation (mm/day equivalent)", "u\u2082: wind speed (m/s)",
                   "es\u2212ea: vapour pressure deficit (kPa)", "\u0394, \u03b3: as above"],
        description="Penman's original 1948 combination equation with an empirical wind function -- "
                    "the historical precursor to FAO-56 Penman-Monteith, before the canopy/aerodynamic "
                    "resistance terms were standardized."),
    "Priestley-Taylor": MethodInfo(
        key="priestley_taylor", display_name="Priestley-Taylor",
        equation="ET = \u03b1 \u00b7 [\u0394/(\u0394+\u03b3)] \u00b7 (Rn\u2212G) / \u03bb,   \u03b1 \u2248 1.26",
        variables=["Rn: net radiation (MJ/m\u00b2/day)", "G: soil heat flux (MJ/m\u00b2/day)",
                   "\u03b1: empirical Priestley-Taylor coefficient (\u22481.26 for well-watered surfaces)",
                   "\u03bb: latent heat of vaporisation"],
        description="A simplified radiation-driven method that drops Penman's aerodynamic term "
                    "entirely, scaling the equilibrium (radiation-only) evapotranspiration by the "
                    "empirical coefficient \u03b1 -- needs no wind or humidity data."),
    "Makkink": MethodInfo(
        key="makkink", display_name="Makkink",
        equation="ET = C \u00b7 [\u0394/(\u0394+\u03b3)] \u00b7 Rs / \u03bb,   C \u2248 0.61",
        variables=["Rs: incoming solar radiation (MJ/m\u00b2/day)",
                   "C: empirical Makkink coefficient (\u22480.61)", "\u0394, \u03b3, \u03bb: as above"],
        description="A radiation-only method (needs just temperature and solar radiation) developed "
                    "for humid, well-watered conditions -- widely used where wind/humidity data are "
                    "unavailable."),
    "Turc": MethodInfo(
        key="turc", display_name="Turc",
        equation="ET = 0.013 \u00b7 [T/(T+15)] \u00b7 (Rs+50) \u00b7 [1 + (50\u2212RH)/70]  (RH<50% correction)",
        variables=["T: mean air temperature (\u00b0C)", "Rs: solar radiation (MJ/m\u00b2/day)",
                   "RH: mean relative humidity (%)"],
        description="An empirical radiation-and-temperature method from Turc (1961), with an "
                    "additional humidity correction term applied when relative humidity drops "
                    "below 50%."),
    "Hargreaves-Samani": MethodInfo(
        key="hargreaves_samani", display_name="Hargreaves-Samani",
        equation="ETo = 0.0023 \u00b7 Ra \u00b7 (T+17.8) \u00b7 (Tmax\u2212Tmin)^0.5",
        variables=["Ra: extraterrestrial radiation (mm/day equivalent)",
                   "T: mean air temperature (\u00b0C)", "Tmax, Tmin: daily max/min temperature (\u00b0C)"],
        description="A temperature-only method (Hargreaves & Samani, 1985) needing just daily "
                    "max/min temperature and latitude/day-of-year (for Ra) -- the standard fallback "
                    "when radiation, wind, and humidity data are all missing."),
    "Thornthwaite": MethodInfo(
        key="thornthwaite_monthly", display_name="Thornthwaite",
        equation="PET = 16 \u00b7 (10T/I)^a \u00b7 (L/12) \u00b7 (N/30),   I = \u03a3(T\u2098/5)^1.514",
        variables=["T: mean monthly temperature (\u00b0C)",
                   "I: annual heat index (from all 12 monthly mean temperatures)",
                   "L: day-length correction factor", "a: empirical exponent (function of I)"],
        description="A purely temperature-driven monthly method (Thornthwaite, 1948), calibrated on "
                    "temperate-climate water budgets -- included here as a lower-data-requirement "
                    "cross-check, though it was not developed for tropical/semi-arid climates like "
                    "Nigeria's."),
    "Blaney-Criddle": MethodInfo(
        key="blaney_criddle", display_name="Blaney-Criddle",
        equation="ETo = p \u00b7 (0.46\u00b7T + 8.13)",
        variables=["T: mean air temperature (\u00b0C)",
                   "p: mean daily percentage of annual daytime hours (latitude- and month-dependent)"],
        description="One of the oldest and simplest temperature-based methods (Blaney & Criddle, "
                    "1950), needing only temperature and a tabulated daylight-hours percentage -- "
                    "low data requirements, correspondingly lower accuracy."),
    "Dalton-Type Mass Transfer": MethodInfo(
        key="dalton_mass_transfer", display_name="Dalton-Type Mass Transfer",
        equation="E = (a + b\u00b7u) \u00b7 (es\u2212ea)",
        variables=["u: wind speed (km/day)", "es\u2212ea: vapour pressure deficit (kPa)",
                   "a, b: empirical mass-transfer coefficients"],
        description="A classical aerodynamic-only mass-transfer formulation (after Dalton, 1802) -- "
                    "estimates evaporation purely from wind speed and the vapour pressure deficit, "
                    "with no energy-balance term at all."),
}


def get_info(display_name: str) -> MethodInfo:
    return METHOD_INFO.get(display_name)
