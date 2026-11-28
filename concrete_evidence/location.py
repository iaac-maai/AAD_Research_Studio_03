"""Which rules apply where: from the site's city to the country, the seismic level and the code.

The user names only the city (or the photo's GPS gives coordinates). From that:
  city    -> country and coordinates     reference/cities.csv (GeoNames, CC BY 4.0)
  Spain   -> ag,R, the reference peak ground acceleration on rock, from the grid in the
             Spanish annex to Eurocode 8 (AN/UNE-EN 1998-1, table AN.5), interpolated as its
             3.2.1(2) says: the point itself, else the 2 or 4 nearest grid points weighted by 1/distance
  ag,R    -> which code (a Spanish place missing from the table is very low too: the table leaves
             out central Spain, under 0.04 g): under 0.04 g is "very low seismicity" in Spain (AN 3.2.1(5)), where
             Eurocode 8 need not be applied, so Eurocode 2 only; otherwise Eurocode 8 (DCM unless
             the engineer chose otherwise) on top of Eurocode 2.

Only Spain has local values so far. Elsewhere the European recommended values apply and the
result says so. Everything here is a starting point for the engineer, never a decision.
"""

from __future__ import annotations

import csv
import math
import unicodedata
from functools import lru_cache
from pathlib import Path

REF = Path(__file__).parent / "reference"
VERY_LOW_ES = 0.04  # g, AN/UNE-EN 1998-1 3.2.1(5): agR below this is very low seismicity
STEP = 0.1  # degrees between grid points in table AN.5


def _rows(name: str):
    with open(REF / name, encoding="utf-8") as f:
        yield from csv.DictReader(line for line in f if not line.startswith("#"))


def _plain(text: str) -> str:
    """Lower case without accents, so 'Málaga', 'malaga' and 'MALAGA' match."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.strip().lower()) if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _cities() -> list[dict]:
    return [{"name": r["name"], "country": r["country"], "lat": float(r["lat"]), "lon": float(r["lon"]),
             "population": int(r["population"]), "key": _plain(r["name"])} for r in _rows("cities.csv")]


@lru_cache(maxsize=1)
def _grid() -> dict[tuple[int, int], tuple[float, float]]:
    """(lon, lat) in tenths of a degree -> (K, agR in g)."""
    return {(round(float(r["lon"]) * 10), round(float(r["lat"]) * 10)): (float(r["K"]), float(r["agR_g"]))
            for r in _rows("es_seismic_grid.csv")}


def find_city(query: str, country: str | None = None, limit: int = 8) -> list[dict]:
    """Cities whose name starts with the query, largest first: for an autocomplete list.
    Each match: name, country, lat, lon. Same names in other countries come back too
    (Valencia, ES and VE), so the person picks; with identical names Spain comes first."""
    q = _plain(query)
    if not q:
        return []
    out = [c for c in _cities() if c["key"].startswith(q) and (not country or c["country"] == country.upper())]
    # exact name first, then Spain (where the app is used), then by size
    out.sort(key=lambda c: (c["key"] != q, c["country"] != "ES", -c["population"]))
    return [{k: c[k] for k in ("name", "country", "lat", "lon")} for c in out[:limit]]


NEAR_KM = 50  # a photo's GPS further than this from any listed town gets no place name


def nearest_city(lat: float, lon: float) -> dict | None:
    """The listed town nearest to a point (the photo's GPS), within NEAR_KM, as name/country/lat/lon.
    Gives the country (so Spanish values apply) and a name to show instead of raw coordinates."""
    k = math.cos(math.radians(lat))
    best = min(_cities(), key=lambda c: (c["lat"] - lat) ** 2 + ((c["lon"] - lon) * k) ** 2)
    km = 111.2 * math.hypot(best["lat"] - lat, (best["lon"] - lon) * k)
    return {key: best[key] for key in ("name", "country", "lat", "lon")} if km <= NEAR_KM else None


def es_seismic(lat: float, lon: float) -> dict | None:
    """ag,R (g) and K at a point in Spain from the annex grid, or None outside the grid."""
    grid = _grid()
    x, y = lon * 10, lat * 10
    corners = {(math.floor(x), math.floor(y)), (math.floor(x), math.ceil(y)),
               (math.ceil(x), math.floor(y)), (math.ceil(x), math.ceil(y))}
    found = [(p, grid[p]) for p in corners if p in grid]
    if not found:
        return None
    for p, (k, a) in found:
        if p == (x, y):  # exactly on a grid point
            return {"agR_g": a, "K": k}
    w = [(1 / math.hypot(p[0] - x, p[1] - y), v) for p, v in found]
    total = sum(wi for wi, _ in w)
    return {"agR_g": round(sum(wi * v[1] for wi, v in w) / total, 3),
            "K": round(sum(wi * v[0] for wi, v in w) / total, 2)}


def rules_for(city: str | None = None, country: str | None = None, lat: float | None = None,
              lon: float | None = None, ductility: str | None = None) -> dict:
    """Where the column is and which rules that means. Give a city (and country if known), or lat/lon.

    Returns place, country, agR_g, K, ductility, national_annex and a one-line note for the result.
    `ductility` the engineer already chose always wins.
    """
    place = None
    if city:
        matches = find_city(city, country, limit=1)
        if not matches:
            return {"place": city, "country": (country or "").upper() or None, "agR_g": None, "K": None,
                    "ductility": ductility or "DCM", "national_annex": None,
                    "note": f"{city} not found: European recommended values, Eurocode 8 (DCM). Pick a nearby town."}
        place = matches[0]
        lat, lon, country = place["lat"], place["lon"], place["country"]
    elif lat is not None and lon is not None:  # the photo's GPS: name the nearest town, never the raw coordinates
        place = nearest_city(lat, lon)
        country = country or (place and place["country"])
    country = (country or "").upper() or None
    name = (f"{place['name']}, {country}" if city else f"near {place['name']}, {country}") if place else "unknown place"
    if country == "ES" and lat is not None:
        hz = es_seismic(lat, lon)
        if hz is None:  # table AN.5 leaves out the very low areas (central Spain: Madrid, Toledo, Valladolid)
            duct = ductility or "none"
            code = "Eurocode 2 only" if duct in ("none", "DCL") else f"Eurocode 8 ({duct})"
            note = (f"{name}: not in the Spanish annex table, so agR under 0.04 g (very low seismicity), "
                    f"{code}, Spanish annex values. Ask the engineer if unsure.")
            return {"place": name, "country": "ES", "agR_g": None, "K": None, "ductility": duct,
                    "national_annex": "ES", "note": note}
        duct = ductility or ("none" if hz["agR_g"] < VERY_LOW_ES else "DCM")
        code = "Eurocode 2 only" if duct in ("none", "DCL") else f"Eurocode 8 ({duct})"
        return {"place": name, "country": "ES", **hz, "ductility": duct, "national_annex": "ES",
                "note": f"{name}: agR {hz['agR_g']:g} g, {code}, Spanish annex values."}
    duct = ductility or "DCM"
    return {"place": name, "country": country, "agR_g": None, "K": None, "ductility": duct, "national_annex": None,
            "note": f"{name}: no local values yet, European recommended values, Eurocode 8 ({duct})."}
