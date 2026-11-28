// GET /api/cities?q=val: up to 8 towns for the site-city field, as {name, country, lat, lon}.
// Same data and order as concrete_evidence/location.find_city: concrete_evidence/reference/cities.csv
// (GeoNames, CC BY 4.0), accents and case ignored, names that start with the query, exact name first,
// then Spain (where the app is used), then the largest. Optional ?country=ES narrows it.

import CSV from "../../lib/cities.gen.js"; // made from the CSV by scripts/cities.mjs (npm run dev / deploy)

const LIMIT = 8;
let CITIES = null; // parsed once per Worker instance

export const plain = (text) => String(text).trim().toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");

function cities() {
  if (CITIES) return CITIES;
  const lines = CSV.split(/\r?\n/).filter((l) => l && !l.startsWith("#"));
  const head = lines.shift().split(",");
  const col = Object.fromEntries(head.map((h, i) => [h, i]));
  CITIES = lines.map((l) => {
    const f = l.split(",");
    return { name: f[col.name], country: f[col.country], lat: Number(f[col.lat]), lon: Number(f[col.lon]),
      population: Number(f[col.population]), key: plain(f[col.name]) };
  });
  return CITIES;
}

export function findCity(query, country = null, limit = LIMIT) {
  const q = plain(query || "");
  if (!q) return [];
  const want = country ? String(country).toUpperCase() : null;
  return cities()
    .filter((c) => c.key.startsWith(q) && (!want || c.country === want))
    .sort((a, b) => (a.key !== q) - (b.key !== q) || (a.country !== "ES") - (b.country !== "ES") || b.population - a.population)
    .slice(0, limit)
    .map(({ name, country: cc, lat, lon }) => ({ name, country: cc, lat, lon }));
}

export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const q = (url.searchParams.get("q") || "").slice(0, 80);
  return Response.json(findCity(q, url.searchParams.get("country")), {
    headers: { "Cache-Control": "private, max-age=3600" },
  });
}
