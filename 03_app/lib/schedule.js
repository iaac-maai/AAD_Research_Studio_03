// The bar bending schedule's format is live/schedule.schema.json (Akanksha), shared with the form and the PDF reader.
// validateSchedule checks a schedule against it with the few JSON Schema keywords that file uses
// (type, required, properties, items, minItems, maxItems, minimum, maximum, enum), so no library is needed.

import SCHEMA from "../../live/schedule.schema.json";

export { SCHEMA };

// Returns a list of plain-language problems; empty means the schedule is valid.
export function validateSchedule(value) {
  const problems = [];
  check(value, SCHEMA, "the schedule", problems);
  return problems;
}

function typeOk(v, type) {
  if (type === "object") return v !== null && typeof v === "object" && !Array.isArray(v);
  if (type === "array") return Array.isArray(v);
  if (type === "integer") return Number.isInteger(v);
  if (type === "number") return typeof v === "number" && Number.isFinite(v);
  if (type === "string") return typeof v === "string";
  return true;
}

function check(v, s, where, problems) {
  if (s.enum && !s.enum.some((e) => e === v)) {
    problems.push(`${where} must be one of ${s.enum.join(", ")} (got ${JSON.stringify(v)})`);
    return;
  }
  if (s.type && !typeOk(v, s.type)) {
    problems.push(`${where} must be ${s.type === "integer" ? "a whole number" : `a ${s.type}`} (got ${JSON.stringify(v)})`);
    return;
  }
  if (typeof v === "number") {
    if (s.minimum !== undefined && v < s.minimum) problems.push(`${where} must be at least ${s.minimum} (got ${v})`);
    if (s.maximum !== undefined && v > s.maximum) problems.push(`${where} must be at most ${s.maximum} (got ${v})`);
  }
  if (Array.isArray(v)) {
    if (s.minItems !== undefined && v.length < s.minItems) problems.push(`${where} needs at least ${s.minItems} values`);
    if (s.maxItems !== undefined && v.length > s.maxItems) problems.push(`${where} takes at most ${s.maxItems} values`);
    if (s.items) v.forEach((x, i) => check(x, s.items, `${where}[${i}]`, problems));
  }
  if (typeOk(v, "object")) {
    for (const key of s.required || []) {
      if (v[key] === undefined || v[key] === null) problems.push(`${where === "the schedule" ? "" : `${where}.`}${key} is missing`);
    }
    for (const [key, sub] of Object.entries(s.properties || {})) {
      // null means "not given" (the form leaves empty fields as null); required fields are caught above
      if (v[key] !== undefined && v[key] !== null) check(v[key], sub, where === "the schedule" ? key : `${where}.${key}`, problems);
    }
  }
}
