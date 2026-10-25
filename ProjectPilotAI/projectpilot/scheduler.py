"""Critical Path Method: earliest/latest times, slack and critical tasks."""


def schedule(tasks: list[dict]) -> int:
    for t in tasks:
        t["es"] = max([tasks[d]["es"] + tasks[d]["duration"] for d in t["deps"]], default=0)
        t["ef"] = t["es"] + t["duration"]
    end = max(t["ef"] for t in tasks)
    for t in tasks:
        t["lf"] = end
    for i in range(len(tasks) - 1, -1, -1):
        for u in tasks:
            if i in u["deps"]:
                tasks[i]["lf"] = min(tasks[i]["lf"], u["lf"] - u["duration"])
    for t in tasks:
        t["slack"] = t["lf"] - t["ef"]
        t["critical"] = t["slack"] == 0
    return end
