import pandas as pd
from projectpilot import agent, model, scheduler
from projectpilot.data import FEATURES, generate

TEAM = [{"name": "A", "skills": ["plan", "design"], "load": 30}, {"name": "B", "skills": ["dev", "data"], "load": 90},
        {"name": "C", "skills": ["test", "dev", "ops"], "load": 20}]


def test_scheduler_critical_path():
    t = [dict(duration=2, deps=[]), dict(duration=3, deps=[0]), dict(duration=1, deps=[0]), dict(duration=2, deps=[1, 2])]
    assert scheduler.schedule(t) == 7
    assert [x["critical"] for x in t] == [True, True, False, True]
    assert t[2]["slack"] == 2


def test_model_quality_and_probabilities():
    m = model.train()
    assert m["results"][m["best_model"]]["roc_auc"] > 0.75
    p, _ = model.predict(generate(50, seed=1)[FEATURES])
    assert ((p >= 0) & (p <= 1)).all()


def test_agent_flow_and_human_approval():
    p = agent.analyse(agent.build("Build a web app", TEAM, deadline=15, budget=1000))
    assert p["end"] > 15 and p["recs"]
    before = [(t["duration"], t["owner"]) for t in p["tasks"]]
    first = next(r for r in p["recs"] if r["kind"] == "info")
    agent.apply_recommendation(p, first, approve=False)
    assert [(t["duration"], t["owner"]) for t in p["tasks"]] == before      # rejected: no change
    assert first["id"] not in [r["id"] for r in p["recs"]]                  # and not suggested again
    total = sum(t["duration"] for t in p["tasks"])
    rec = next(r for r in p["recs"] if r["kind"] == "shorten")
    agent.apply_recommendation(p, rec, approve=True)
    assert sum(t["duration"] for t in p["tasks"]) == total - 2
    assert [l["approved"] for l in p["log"]] == [False, True]
