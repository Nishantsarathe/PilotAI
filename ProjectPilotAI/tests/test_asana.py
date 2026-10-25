import datetime as dt
import pytest
from projectpilot import agent, asana_client as ac

TEAM = [{"name": "A", "skills": ["plan", "design"], "load": 30, "email": "a@x.com"},
        {"name": "B", "skills": ["dev", "data", "test", "ops"], "load": 40, "email": "bad@x.com"}]


class R:
    def __init__(s, data, code=200, headers=None):
        s.status_code, s._d, s.headers, s.text = code, data, headers or {}, str(data)

    def json(s):
        return s._d


class Fake:
    def __init__(s, pages=None):
        s.headers, s.calls, s.n, s.pages = {}, [], 0, pages or []

    def request(s, method, url, params=None, json=None, timeout=None):
        path = url.replace(ac.BASE, "")
        s.calls.append((method, path, params, json))
        if method == "POST" and path == "/projects":
            return R({"data": {"gid": "P1", "permalink_url": "https://app.asana.com/0/P1"}})
        if method == "POST" and path == "/tasks":
            if json["data"].get("assignee") == "bad@x.com":
                return R({"errors": [{"message": "Unknown user"}]}, 400)
            s.n += 1
            return R({"data": {"gid": f"T{s.n}"}})
        if method == "GET" and s.pages:
            return R(s.pages.pop(0))
        return R({"data": {}})


def project():
    return agent.analyse(agent.build("Build a web app", TEAM, 40, 30000))


def test_export_creates_project_tasks_dependencies_and_falls_back_on_bad_assignee():
    p, f = project(), Fake()
    r = ac.Asana("tok", f).export_plan(p, "Demo", "W1", dt.date(2026, 11, 2))
    posts = [c for c in f.calls if c[0] == "POST"]
    assert posts[0][1] == "/projects" and r["url"].endswith("/P1")
    created = [c for c in posts if c[1] == "/tasks" and "assignee" not in (c[3] or {}).get("data", {})]
    assert all(t.get("gid") for t in p["tasks"])
    assert len([c for c in posts if c[1].endswith("addDependencies")]) == sum(bool(t["deps"]) for t in p["tasks"])
    first = [c[3]["data"] for c in posts if c[1] == "/tasks"][0]
    assert first["start_on"] == "2026-11-02" and first["due_on"] >= first["start_on"]
    assert any("without assignee" in w for w in r["warnings"]) or all(t["owner"] == "A" for t in p["tasks"])
    assert p["asana"]["project_gid"] == "P1"


def test_import_orders_dependencies_and_paginates():
    page1 = {"data": [{"gid": "2", "name": "Build API", "start_on": "2026-11-05", "due_on": "2026-11-09",
                       "dependencies": [{"gid": "1"}], "assignee": {"name": "Ravi", "email": "r@x.com"}}],
             "next_page": {"offset": "abc"}}
    page2 = {"data": [{"gid": "1", "name": "Requirements", "completed": True, "dependencies": []}]}
    f = Fake(pages=[{"data": {"name": "My project"}}, page1, page2])
    name, tasks, meta = ac.Asana("tok", f).import_project("P9")
    assert name == "My project" and [t["name"] for t in tasks] == ["Requirements", "Build API"]
    assert tasks[1]["deps"] == [0] and tasks[1]["duration"] == 5 and tasks[1]["skill"] == "dev"
    assert tasks[0]["progress"] == 100 and meta["start"] == dt.date(2026, 11, 5)
    p = agent.analyse(agent.from_tasks(tasks, 30, 10000))
    assert p["tasks"][1]["owner"] == "Ravi" and p["end"] == 8 and p["tasks"][0]["owner"]


def test_rate_limit_retry_and_errors(monkeypatch):
    monkeypatch.setattr(ac.time, "sleep", lambda s: None)
    seq = [R({}, 429, {"Retry-After": "1"}), R({"data": []})]

    class S(Fake):
        def request(s, *a, **k):
            return seq.pop(0)
    assert ac.Asana("tok", S()).workspaces() == []
    with pytest.raises(ac.AsanaError, match="401"):
        class E(Fake):
            def request(s, *a, **k):
                return R({"errors": [{"message": "Not Authorized"}]}, 401)
        ac.Asana("tok", E()).workspaces()
    with pytest.raises(ac.AsanaError, match="No Asana token"):
        ac.Asana("", Fake())


def test_pull_progress_and_push_updates():
    p, f = project(), Fake()
    ac.Asana("tok", f).export_plan(p, "Demo", "W1", dt.date(2026, 11, 2))
    g0 = p["tasks"][0]["gid"]
    f.pages = [{"data": [{"gid": g0, "completed": True}]}]
    assert ac.Asana("tok", f).pull_progress(p) == 1 and p["tasks"][0]["progress"] == 100
    out = ac.Asana("tok", f).push_updates(p, dt.date(2026, 11, 2))
    assert out["updated"] >= len(p["tasks"]) - 1
