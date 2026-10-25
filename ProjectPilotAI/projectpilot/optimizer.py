"""Resource optimizer: greedy assignment by skill match, then lowest workload."""


def assign(tasks: list[dict], team: list[dict]) -> None:
    load = {m["name"]: m["load"] for m in team}
    for t in tasks:
        if t.get("locked"):
            continue
        best = min(team, key=lambda m: (0 if t["skill"] in m["skills"] else 40) + load[m["name"]])
        t["owner"] = best["name"]
        load[best["name"]] += t["duration"] * 2


def owner_load(tasks, team, name):
    base = next(m["load"] for m in team if m["name"] == name)
    return base + 2 * sum(t["duration"] for t in tasks if t.get("owner") == name)
