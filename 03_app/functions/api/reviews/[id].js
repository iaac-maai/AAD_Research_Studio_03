// POST /api/reviews/<check id>: a person confirms or rejects faults, and can sign the check off.
// JSON body: {reviewer, decisions: [{fault_index, decision: "confirm"|"reject", note}], sign_off: true|false}
// Nothing is decided by the model alone: the check stays "pending" until every fault has a decision.

export async function onRequestPost({ params, request, env }) {
  const row = await env.DB.prepare("SELECT id, check_json FROM checks WHERE id = ?").bind(params.id).first();
  if (!row) return Response.json({ error: "No check with that id." }, { status: 404 });

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Send the decisions as JSON." }, { status: 400 });
  }
  const reviewer = String(body.reviewer || "").trim().slice(0, 80);
  if (!reviewer) return Response.json({ error: "Write your name before you confirm or reject." }, { status: 400 });

  const checks = JSON.parse(row.check_json).checks || [];
  const failed = new Set(checks.map((c, i) => (c.status === "fail" ? i : -1)).filter((i) => i >= 0));
  const now = new Date().toISOString();
  const statements = [];
  for (const d of body.decisions || []) {
    const i = Number(d.fault_index);
    if (!failed.has(i) || !["confirm", "reject"].includes(d.decision)) {
      return Response.json({ error: `Fault ${i} isn't a fault of this check, or the decision isn't confirm / reject.` },
        { status: 400 });
    }
    statements.push(env.DB.prepare(
      "INSERT INTO reviews (id, check_id, fault_index, decision, note, reviewer, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
    ).bind(crypto.randomUUID(), row.id, i, d.decision, String(d.note || "").slice(0, 500) || null, reviewer, now));
  }
  if (statements.length) await env.DB.batch(statements);

  // The latest decision per fault counts. Reviewed once every fault has one.
  const { results } = await env.DB.prepare(
    "SELECT fault_index, decision FROM reviews WHERE check_id = ? ORDER BY created_at",
  ).bind(row.id).all();
  const decided = new Map(results.map((r) => [r.fault_index, r.decision]));
  const allDecided = [...failed].every((i) => decided.has(i));
  const status = allDecided ? "reviewed" : "pending";

  if (body.sign_off) {
    if (!allDecided) return Response.json({ error: "Decide every fault before you sign off." }, { status: 400 });
    await env.DB.prepare("UPDATE checks SET review_status = 'signed_off', signed_off_by = ?, signed_off_at = ? WHERE id = ?")
      .bind(reviewer, now, row.id).run();
    return Response.json({ review_status: "signed_off", signed_off_by: reviewer, signed_off_at: now });
  }
  await env.DB.prepare("UPDATE checks SET review_status = ? WHERE id = ?").bind(status, row.id).run();
  return Response.json({ review_status: status, decided: decided.size, faults: failed.size });
}
