from projectpilot import agent, analytics

TEAM = [{"name": "A", "skills": ["plan", "design", "ops"], "load": 30, "email": ""},
        {"name": "B", "skills": ["dev", "data", "test"], "load": 40, "email": ""}]


def proj(deadline=40, budget=30000):
    return agent.analyse(agent.build("Build a web app", TEAM, deadline, budget))


def test_monte_carlo_is_ordered_and_bounded():
    p = proj()
    mc = analytics.monte_carlo(p["tasks"], p["deadline"])
    assert 0 <= mc["p_on_time"] <= 1 and mc["p50"] <= mc["p80"] <= mc["p95"]
    assert analytics.monte_carlo(p["tasks"], 10_000)["p_on_time"] == 1.0
    assert analytics.monte_carlo(p["tasks"], 1)["p_on_time"] == 0.0


def test_health_score_drops_when_late_and_over_budget():
    good, bad = analytics.health_score(proj(60, 10**6))[0], analytics.health_score(proj(10, 100))[0]
    assert 0 <= bad < good <= 100


def test_cost_curve_is_monotonic_and_matches_total():
    p = proj()
    days, cum = analytics.cost_curve(p)
    assert cum == sorted(cum) and cum[-1] == p["cost"]
