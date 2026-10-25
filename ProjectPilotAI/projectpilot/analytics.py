"""Forecasting and health analytics: Monte Carlo finish dates, health score, cost curve."""
import numpy as np

DAILY_RATE = 400


def monte_carlo(tasks: list[dict], deadline: int, runs: int = 2000, seed: int = 7) -> dict:
    """Simulate task durations (more uncertainty for riskier tasks) and the resulting finish day."""
    rng = np.random.default_rng(seed)
    base = np.array([t["duration"] for t in tasks], float)
    risk = np.array([t.get("risk", 0.2) for t in tasks])
    sigma = 0.10 + 0.45 * risk
    mult = rng.lognormal(-sigma ** 2 / 2 + 0.25 * risk, sigma, size=(runs, len(tasks)))
    dur = np.maximum(1, np.round(base * mult))
    for i, t in enumerate(tasks):                                  # completed work is no longer uncertain
        if t.get("progress", 0) >= 100:
            dur[:, i] = base[i]
    ef = np.zeros_like(dur)
    for i, t in enumerate(tasks):                                  # deps always reference earlier tasks
        start = ef[:, t["deps"]].max(axis=1) if t["deps"] else 0
        ef[:, i] = start + dur[:, i]
    end = ef.max(axis=1)
    return {"end": end, "p_on_time": float((end <= deadline).mean()),
            "p50": float(np.percentile(end, 50)), "p80": float(np.percentile(end, 80)),
            "p95": float(np.percentile(end, 95))}


def health_score(p: dict):
    """0-100 score from schedule overrun, budget overrun, delay risk and overdue tasks."""
    tasks = p["tasks"]
    pen = min(35, max(0, p["end"] - p["deadline"]) * 3)
    if p["budget"] > 0 and p["cost"] > p["budget"]:
        pen += min(20, (p["cost"] - p["budget"]) / p["budget"] * 40)
    pen += min(35, sum(t["risk"] for t in tasks) / len(tasks) * 30 + 3 * sum(t["level"] == "High" for t in tasks))
    pen += min(15, 4 * sum(t["ef"] <= p["today"] and t["progress"] < 100 for t in tasks))
    score = max(0, round(100 - pen))
    return score, ("On track" if score >= 75 else "At risk" if score >= 50 else "Critical")


def cost_curve(p: dict):
    """Cumulative planned cost per project day (one person-day per active task-day)."""
    days = list(range(0, max(p["end"], p["deadline"]) + 1))
    cum, total = [], 0.0
    for d in days:
        total += sum(t["es"] <= d < t["ef"] for t in p["tasks"]) * DAILY_RATE
        cum.append(total)
    return days, cum
