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


def test_link_project_matches_unique_names_and_skips_duplicates():
    p = {"tasks": [{"name": "Requirements", "progress": 0},
                    {"name": "Build", "progress": 40}, {"name": "Build", "progress": 0},
                    {"name": "Missing", "progress": 0}, {"name": "Review and test", "progress": 0}]}
    f = Fake(pages=[{"data": [{"gid": "T1", "name": "requirements", "completed": True},
                               {"gid": "T2", "name": "Build", "completed": False},
                               {"gid": "T3", "name": "Build", "completed": False},
                               {"gid": "T4", "name": "Review and Test", "completed": True},
                               {"gid": "T5", "name": "Review and Test", "completed": False}]}])
    result = ac.Asana("tok", f).link_project(p, "P1")
    assert result["linked"] == 2 and result["total"] == 5
    assert p["tasks"][0]["gid"] == "T1" and p["tasks"][0]["progress"] == 100
    assert p["tasks"][1]["progress"] == 40
    assert all("gid" not in t for t in p["tasks"][1:4])
    assert p["tasks"][4]["gid"] == "T5"
    assert any("duplicated" in warning for warning in result["warnings"])
    assert any("No Asana task" in warning for warning in result["warnings"])
    assert any("matching completion status" in warning for warning in result["warnings"])
    assert p["asana"]["project_gid"] == "P1"


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
    class Offline(Fake):
        def request(s, *a, **k):
            raise ac.requests.ConnectionError("offline")
    with pytest.raises(ac.AsanaError, match="request failed: offline"):
        ac.Asana("tok", Offline()).workspaces()


def test_pull_progress_and_push_updates():
    p, f = project(), Fake()
    ac.Asana("tok", f).export_plan(p, "Demo", "W1", dt.date(2026, 11, 2))
    g0 = p["tasks"][0]["gid"]
    f.pages = [{"data": [{"gid": g0, "completed": True}]}]
    client = ac.Asana("tok", f)
    assert client.pull_progress(p) == 1 and p["tasks"][0]["progress"] == 100
    out = client.push_updates(p, dt.date(2026, 11, 2))
    assert out["updated"] >= len(p["tasks"]) - 1
    assert next(c[3]["data"]["completed"] for c in reversed(f.calls)
                if c[0] == "PUT" and c[1] == f"/tasks/{g0}") is True
    p["tasks"][0]["progress"] = 0
    client.push_updates(p, dt.date(2026, 11, 2))
    assert next(c[3]["data"]["completed"] for c in reversed(f.calls)
                if c[0] == "PUT" and c[1] == f"/tasks/{g0}") is False
    client.set_task_completion(g0, False)
    assert f.calls[-1][3]["data"] == {"completed": False}
