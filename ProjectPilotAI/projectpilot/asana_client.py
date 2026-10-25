"""Asana integration (REST API v1, Personal Access Token).

Export a ProjectPilot plan to Asana, import an Asana project into ProjectPilot,
and sync schedule, owners and completion in both directions.
The token is kept in memory only and is never written to disk.
"""
import datetime as dt
import os
import re
import time

import requests

BASE = "https://app.asana.com/api/1.0"
SKILL_WORDS = {
    "design": ("design", "wireframe", "mockup", "ui", "ux", "brand"),
    "dev": ("build", "develop", "code", "backend", "frontend", "implement", "integrat", "api"),
    "test": ("test", "qa", "review", "verify", "bug"),
    "data": ("data", "research", "analy", "report", "survey"),
    "ops": ("deploy", "launch", "release", "document", "logistic", "vendor", "handover", "venue"),
}


class AsanaError(RuntimeError):
    pass


def guess_skill(name: str) -> str:
    n = name.lower()
    return next((s for s, words in SKILL_WORDS.items() if re.search(r"\b(" + "|".join(words) + ")", n)), "plan")


def _d(s):
    return dt.date.fromisoformat(s) if s else None


def tasks_from_asana(raw: list[dict]):
    """Convert Asana task dicts to ProjectPilot tasks, ordered so dependencies come first."""
    gids = {t["gid"] for t in raw}
    by = {t["gid"]: t for t in raw}
    indeg = {g: len([d for d in (by[g].get("dependencies") or []) if d["gid"] in gids]) for g in gids}
    order, ready = [], [t["gid"] for t in raw if indeg[t["gid"]] == 0]
    while ready:
        g = ready.pop(0)
        order.append(g)
        for t in raw:
            if g in [d["gid"] for d in (t.get("dependencies") or [])] and t["gid"] in indeg:
                indeg[t["gid"]] -= 1
                if indeg[t["gid"]] == 0:
                    ready.append(t["gid"])
    order += [t["gid"] for t in raw if t["gid"] not in order]       # cycles: keep, drop their deps below
    idx = {g: i for i, g in enumerate(order)}
    tasks, starts, dues = [], [], []
    for g in order:
        a = by[g]
        s, e = _d(a.get("start_on")), _d(a.get("due_on"))
        starts += [x for x in (s, e) if x]
        dues += [x for x in (e,) if x]
        dur = (e - s).days + 1 if s and e else 3
        asg = a.get("assignee") or {}
        tasks.append({"name": a["name"], "duration": max(1, min(dur, 90)), "skill": guess_skill(a["name"]),
                      "deps": [idx[d["gid"]] for d in (a.get("dependencies") or []) if d["gid"] in idx and idx[d["gid"]] < idx[g]],
                      "owner": asg.get("name"), "email": asg.get("email"),
                      "progress": 100 if a.get("completed") else 0, "gid": g})
    return tasks, {"start": min(starts) if starts else None, "due": max(dues) if dues else None}


class Asana:
    def __init__(self, token: str | None = None, session=None):
        self.token = (token or os.getenv("ASANA_TOKEN") or "").strip()
        if not self.token:
            raise AsanaError("No Asana token. Create a personal access token and paste it above.")
        self.s = session or requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.token}", "Accept": "application/json"})

    # ---- low level ----
    def _req(self, method, path, params=None, body=None, retries=3):
        for attempt in range(retries + 1):
            r = self.s.request(method, BASE + path, params=params,
                               json={"data": body} if body is not None else None, timeout=30)
            if r.status_code == 429 and attempt < retries:        # rate limited
                time.sleep(min(int(r.headers.get("Retry-After", 2)), 30))
                continue
            break
        if r.status_code >= 400:
            try:
                msg = "; ".join(e.get("message", "") for e in r.json().get("errors", []))
            except Exception:
                msg = r.text[:200]
            raise AsanaError(f"Asana error {r.status_code}: {msg or 'request failed'}")
        return r.json()

    def _list(self, path, params=None):
        params = dict(params or {})
        params.setdefault("limit", 100)
        out = []
        while True:
            j = self._req("GET", path, params)
            out += j["data"]
            nxt = (j.get("next_page") or {}).get("offset")
            if not nxt:
                return out
            params["offset"] = nxt

    # ---- discovery ----
    def workspaces(self):
        return self._list("/workspaces", {"opt_fields": "name,is_organization"})

    def teams(self, workspace_gid):
        return self._list(f"/organizations/{workspace_gid}/teams", {"opt_fields": "name"})

    def projects(self, workspace_gid):
        return self._list("/projects", {"workspace": workspace_gid, "archived": "false", "opt_fields": "name"})

    # ---- ProjectPilot -> Asana ----
    def export_plan(self, p: dict, name: str, workspace: str, start: dt.date, team: str | None = None):
        body = {"name": name, "workspace": workspace,
                "notes": "Created by ProjectPilot AI. Dates come from the critical-path schedule."}
        if team:
            body["team"] = team
        proj = self._req("POST", "/projects", {"opt_fields": "permalink_url"}, body)["data"]
        warnings = []
        for t in p["tasks"]:
            b = self._task_body(p, t, start)
            b.update({"projects": [proj["gid"]], "notes": self._notes(t)})
            t["gid"] = self._create_task(b, t, warnings)
        for t in p["tasks"]:
            if t["deps"]:
                try:
                    self._req("POST", f"/tasks/{t['gid']}/addDependencies", None,
                              {"dependencies": [p["tasks"][d]["gid"] for d in t["deps"]]})
                except AsanaError as e:
                    warnings.append(f"Dependencies not created ({e}). Asana may require a plan that supports them.")
                    break
        p["asana"] = {"project_gid": proj["gid"], "url": proj.get("permalink_url")}
        return {"project_gid": proj["gid"], "url": proj.get("permalink_url"), "warnings": warnings}

    @staticmethod
    def _notes(t):
        f = ", ".join(t.get("factors") or []) or "none significant"
        return f"Skill: {t['skill']}\nPredicted delay risk: {t.get('risk', 0):.0%} ({t.get('level', 'n/a')})\nMain factors: {f}"

    @staticmethod
    def _task_body(p, t, start):
        b = {"name": t["name"], "start_on": (start + dt.timedelta(days=t["es"])).isoformat(),
             "due_on": (start + dt.timedelta(days=t["ef"] - 1)).isoformat()}
        email = next((m.get("email") for m in p["team"] if m["name"] == t["owner"]), None)
        if email:
            b["assignee"] = email
        if t.get("progress", 0) >= 100:
            b["completed"] = True
        return b

    def _create_task(self, b, t, warnings):
        try:
            return self._req("POST", "/tasks", None, b)["data"]["gid"]
        except AsanaError as e:
            if "assignee" not in b:
                raise
            b = {k: v for k, v in b.items() if k != "assignee"}
            warnings.append(f"'{t['name']}' created without assignee ({e}).")
            return self._req("POST", "/tasks", None, b)["data"]["gid"]

    # ---- keep Asana in sync after approving recommendations ----
    def push_updates(self, p: dict, start: dt.date):
        warnings, n = [], 0
        for t in p["tasks"]:
            if not t.get("gid"):
                continue
            b = self._task_body(p, t, start)
            try:
                self._req("PUT", f"/tasks/{t['gid']}", None, b)
            except AsanaError as e:
                if "assignee" not in b:
                    warnings.append(f"'{t['name']}': {e}")
                    continue
                b.pop("assignee")
                warnings.append(f"'{t['name']}' updated without assignee ({e}).")
                self._req("PUT", f"/tasks/{t['gid']}", None, b)
            n += 1
        return {"updated": n, "warnings": warnings}

    def pull_progress(self, p: dict):
        """Mark tasks complete (or reopen them) to match Asana. Returns number changed."""
        raw = self._list(f"/projects/{p['asana']['project_gid']}/tasks", {"opt_fields": "completed"})
        done = {r["gid"]: r.get("completed", False) for r in raw}
        changed = 0
        for t in p["tasks"]:
            if t.get("gid") in done:
                new = 100 if done[t["gid"]] else (0 if t["progress"] >= 100 else t["progress"])
                changed += new != t["progress"]
                t["progress"] = new
        return changed

    # ---- Asana -> ProjectPilot ----
    def import_project(self, project_gid: str):
        name = self._req("GET", f"/projects/{project_gid}", {"opt_fields": "name"})["data"]["name"]
        raw = self._list(f"/projects/{project_gid}/tasks", {
            "opt_fields": "name,completed,start_on,due_on,assignee.name,assignee.email,dependencies.gid"})
        if not raw:
            raise AsanaError("That Asana project has no tasks to import.")
        tasks, meta = tasks_from_asana(raw)
        return name, tasks, meta
