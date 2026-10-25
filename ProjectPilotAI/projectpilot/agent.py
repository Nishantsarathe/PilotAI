"""AI project-manager agent: plan -> schedule -> assign -> predict -> recommend.

Every recommendation needs explicit human approval (apply_recommendation).
"""
import pandas as pd

from . import model, optimizer, planner, scheduler

DAILY_RATE = 400


def build(desc: str, team: list[dict], deadline: int, budget: float, today: int = 0):
    tasks, source = planner.generate_plan(desc)
    optimizer.assign(tasks, team)
    for t in tasks:
        t.setdefault("progress", 0)
    return {"tasks": tasks, "team": team, "deadline": deadline, "budget": budget,
            "today": today, "source": source, "log": []}


def from_tasks(tasks: list[dict], deadline: int, budget: float, today: int = 0, source: str = "asana"):
    """Build a project from existing tasks (e.g. imported from Asana). Imported owners are kept."""
    members = {}
    for t in tasks:
        if t.get("owner"):
            m = members.setdefault(t["owner"], {"name": t["owner"], "skills": set(), "load": 30.0, "email": t.get("email")})
            m["skills"].add(t["skill"])
    team = [{**m, "skills": sorted(m["skills"])} for m in members.values()]
    if not team:
        team = [{"name": "Team", "skills": list(planner.SKILLS), "load": 30.0, "email": None}]
    for t in tasks:
        t["locked"] = bool(t.get("owner"))
    optimizer.assign(tasks, team)
    return {"tasks": tasks, "team": team, "deadline": deadline, "budget": budget,
            "today": today, "source": source, "log": []}


def analyse(p: dict) -> dict:
    tasks, team = p["tasks"], p["team"]
    p["end"] = scheduler.schedule(tasks)
    rows = []
    for t in tasks:
        exp = min(1, max(0, (p["today"] - t["es"]) / t["duration"]))
        rows.append({"duration": t["duration"], "n_deps": len(t["deps"]),
                     "owner_load": min(130, optimizer.owner_load(tasks, team, t["owner"])),
                     "slack": t["slack"],
                     "skill_match": int(t["skill"] in next(m["skills"] for m in team if m["name"] == t["owner"])),
                     "progress_gap": max(0, exp - t["progress"] / 100), "team_size": len(team)})
    prob, factors = model.predict(pd.DataFrame(rows))
    for t, pr, f in zip(tasks, prob, factors):
        t["risk"], t["level"], t["factors"] = float(pr), model.level(pr), f
    p["cost"] = sum(t["duration"] for t in tasks) * DAILY_RATE
    p["recs"] = _recommend(p)
    return p


def _recommend(p):
    recs, done = [], {l["id"] for l in p["log"]}
    for i, t in enumerate(p["tasks"]):
        if t["level"] != "High":
            continue
        alts = [m for m in p["team"] if m["name"] != t["owner"] and t["skill"] in m["skills"]]
        alt = min(alts, key=lambda m: m["load"], default=None)
        if alt:
            r = dict(id=f"reassign-{i}-{alt['name']}", kind="reassign", task=i, to=alt["name"],
                     text=f"Reassign '{t['name']}' from {t['owner']} to {alt['name']}")
        else:
            r = dict(id=f"buffer-{i}", kind="buffer", task=i, text=f"Add a 2-day buffer to '{t['name']}'")
        r["why"] = f"Delay risk {t['risk']:.0%}. Factors: {', '.join(t['factors']) or 'combined effects'}."
        recs.append(r)
    if p["end"] > p["deadline"]:
        crit = max((t for t in p["tasks"] if t["critical"]), key=lambda t: t["duration"])
        recs.append(dict(id="crash", kind="shorten", task=p["tasks"].index(crit),
                         text=f"Shorten '{crit['name']}' by 2 days (add a second person)",
                         why=f"Plan ends day {p['end']}, {p['end'] - p['deadline']} days after the deadline; this task is critical."))
    if p["cost"] > p["budget"]:
        recs.append(dict(id="budget", kind="info", task=None, text="Planned cost exceeds budget: reduce scope or raise budget",
                         why=f"Planned {p['cost']:,.0f} vs budget {p['budget']:,.0f}."))
    return [r for r in recs if r["id"] not in done]


def apply_recommendation(p: dict, rec: dict, approve: bool) -> dict:
    """Human-in-the-loop gate: nothing changes unless approve=True."""
    p["log"].append({"id": rec["id"], "text": rec["text"], "approved": approve})
    if approve and rec["task"] is not None:
        t = p["tasks"][rec["task"]]
        if rec["kind"] == "reassign":
            t["owner"], t["locked"] = rec["to"], True
        elif rec["kind"] == "buffer":
            t["duration"] += 2
        elif rec["kind"] == "shorten":
            t["duration"] = max(1, t["duration"] - 2)
    return analyse(p)
