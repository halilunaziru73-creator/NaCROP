"""
nigeria_locations.py
----------------------
A small, fully offline lookup of major Nigerian cities/towns (name, state,
approximate lat/lon) used to suggest a human-readable location name whenever the
user changes the farm's Latitude/Longitude -- so the app's location display is no
longer hard-coded to "Zaria, Kaduna State, Nigeria" regardless of what coordinates
are actually entered.

No internet access or geocoding API is available in this environment, so this is
a nearest-neighbour match against ~45 well-known Nigerian population centres
(state capitals plus a few agriculturally significant towns), not a full
reverse-geocoder -- it will name the closest known town, which for most of
Nigeria's ~36 states lands within a reasonable distance of any real farm
location. The user can always type their own custom location name instead if
this approximation isn't close enough.

IMPORTANT LIMITATION (also disclosed in the generated report): only the LOCATION
NAME shown in the app/report follows the entered coordinates. The underlying
crop-water-balance climate model (temperature reconstruction, wind, solar
radiation) was trained specifically on Samaru, Zaria's own 28-year weather
dataset (see thermal_model.py) -- it is not re-calibrated for other locations.
Predictions stay numerically most reliable near Zaria/Kaduna State and become
progressively more approximate the further the entered coordinates are from it.
"""
import math

# (name, state, lat, lon) -- state capitals + a few major agricultural towns
LOCATIONS = [
    ("Samaru, Zaria", "Kaduna State", 11.1500, 7.6500),
    ("Kaduna", "Kaduna State", 10.5222, 7.4383),
    ("Kano", "Kano State", 12.0022, 8.5920),
    ("Katsina", "Katsina State", 12.9908, 7.6018),
    ("Sokoto", "Sokoto State", 13.0059, 5.2476),
    ("Gusau", "Zamfara State", 12.1704, 6.6641),
    ("Birnin Kebbi", "Kebbi State", 12.4539, 4.1975),
    ("Jos", "Plateau State", 9.8965, 8.8583),
    ("Bauchi", "Bauchi State", 10.3158, 9.8442),
    ("Gombe", "Gombe State", 10.2897, 11.1673),
    ("Yola", "Adamawa State", 9.2035, 12.4954),
    ("Damaturu", "Yobe State", 11.7470, 11.9608),
    ("Maiduguri", "Borno State", 11.8333, 13.1500),
    ("Minna", "Niger State", 9.6139, 6.5569),
    ("Abuja", "FCT", 9.0765, 7.3986),
    ("Lokoja", "Kogi State", 7.8023, 6.7333),
    ("Lafia", "Nasarawa State", 8.4939, 8.5169),
    ("Makurdi", "Benue State", 7.7322, 8.5391),
    ("Ilorin", "Kwara State", 8.4966, 4.5426),
    ("Oshogbo", "Osun State", 7.7719, 4.5561),
    ("Ibadan", "Oyo State", 7.3775, 3.9470),
    ("Abeokuta", "Ogun State", 7.1475, 3.3619),
    ("Akure", "Ondo State", 7.2571, 5.2058),
    ("Ado-Ekiti", "Ekiti State", 7.6211, 5.2213),
    ("Lagos", "Lagos State", 6.5244, 3.3792),
    ("Benin City", "Edo State", 6.3350, 5.6037),
    ("Asaba", "Delta State", 6.1987, 6.6980),
    ("Awka", "Anambra State", 6.2120, 7.0740),
    ("Enugu", "Enugu State", 6.4413, 7.4988),
    ("Abakaliki", "Ebonyi State", 6.3249, 8.1137),
    ("Owerri", "Imo State", 5.4840, 7.0351),
    ("Umuahia", "Abia State", 5.5252, 7.4937),
    ("Port Harcourt", "Rivers State", 4.8156, 7.0498),
    ("Yenagoa", "Bayelsa State", 4.9247, 6.2642),
    ("Uyo", "Akwa Ibom State", 5.0378, 7.9128),
    ("Calabar", "Cross River State", 4.9757, 8.3417),
    ("Jalingo", "Taraba State", 8.8833, 11.3667),
    ("Dutse", "Jigawa State", 11.7563, 9.3392),
    ("Funtua", "Katsina State", 11.5222, 7.3178),
    ("Gombi", "Adamawa State", 10.1961, 12.7658),
    ("Kebbi (Argungu)", "Kebbi State", 12.7500, 4.5167),
    ("Zamfara (Talata Mafara)", "Zamfara State", 12.5731, 6.0656),
]

ZARIA_LAT, ZARIA_LON = 11.1500, 7.6500


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_location_name(lat: float, lon: float) -> str:
    """Returns 'Nearest Town, State, Nigeria' for the given coordinates -- an
    offline nearest-neighbour approximation, not a real reverse-geocode."""
    best = min(LOCATIONS, key=lambda loc: _haversine_km(lat, lon, loc[2], loc[3]))
    name, state, _, _ = best
    return f"{name}, {state}, Nigeria"


def distance_from_zaria_km(lat: float, lon: float) -> float:
    """How far the entered coordinates are from Samaru, Zaria -- the site the
    underlying climate/ET model was actually trained on. Used to give the user
    an honest sense of how approximate the predictions are likely to be the
    further they roam from the calibration site."""
    return _haversine_km(lat, lon, ZARIA_LAT, ZARIA_LON)
