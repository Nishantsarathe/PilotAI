"""ProjectPilot AI: mission-control dashboard. Run with:  streamlit run app.py"""
import datetime as dt
import json
import os

import altair as alt
import pandas as pd
import streamlit as st

from projectpilot import agent, analytics, asana_client, model, ui
from projectpilot.data import FEATURES

st.set_page_config(page_title="ProjectPilot AI", page_icon="🧭", layout="wide")
ui.inject()

DEFAULT_TEAM = [{"name": "Asha", "skills": "plan,design", "load": 30, "email": ""},
                {"name": "Ravi", "skills": "dev,data", "load": 55, "email": ""},
                {"name": "Meera", "skills": "test,data,dev", "load": 40, "email": ""},
                {"name": "Kabir", "skills": "ops,plan", "load": 20, "email": ""}]
DEFAULT_DESC = "Build a web portal where customers track orders and raise support tickets"


def team_from_df(df):
    out = []
    for _, r in df.dropna(subset=["name"]).iterrows():
        em = r.get("email")
        out.append({"name": r["name"], "skills": [s.strip() for s in str(r["skills"]).split(",") if s.strip()],
                    "load": float(r["load"]), "email": em.strip() if isinstance(em, str) else ""})
    return out


def metrics():
    if not model.METRICS_PATH.exists():
        model.train()
    return json.loads(model.METRICS_PATH.read_text())


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Mission setup")
    name = st.text_input("Project name", "Customer Portal Redesign")
    desc = st.text_area("Describe the project", DEFAULT_DESC, height=100)
    c1, c2 = st.columns(2)
    deadline = c1.number_input("Deadline (day)", 5, 365, 25)
    budget = c2.number_input("Budget", 0, 10_000_000, 15000, step=1000)
    with st.expander("Team and skills"):
        team_df = st.data_editor(pd.DataFrame(DEFAULT_TEAM), num_rows="dynamic", width="stretch")
    go = st.button("Generate plan", type="primary")


def launch():
    st.session_state.p = agent.analyse(agent.build(desc, team_from_df(team_df), int(deadline), float(budget)))
    st.session_state.name = name


if go or st.session_state.get("p") is None:
    launch()
p = st.session_state.p
MET = metrics()
best = MET["results"][MET["best_model"]]

ui.hero(st.session_state.get("name", name), [
    ("ok", "Model ", f"{MET['best_model'].replace('_', ' ')}, AUC {best['roc_auc']:.2f}"),
    ("ok" if "llm" in p["source"] else "off", "Planner ", "LLM" if p["source"] == "llm" else p["source"].split(":")[-1] + " template"),
    ("ok" if st.session_state.get("asana_ws") else "off", "Asana ", "connected" if st.session_state.get("asana_ws") else "not connected"),
    ("ok", f"{len(p['tasks'])} tasks ", f"{len(p['team'])} people")])
ui.pipeline(["done"] * 5 + ["act" if p["recs"] else "done"])

t_dash, t_risk, t_fc, t_ai, t_model, t_asana = st.tabs(
    ["Mission control", "Tasks and risk", "Forecast", "Responsible AI", "Model lab", "Asana"])


def gantt(p):
    g = pd.DataFrame([{"Task": t["name"], "start": t["es"], "end": t["ef"], "Owner": t["owner"], "Risk": round(t["risk"] * 100),
                       "Level": t["level"], "Critical": t["critical"], "pend": t["es"] + t["duration"] * t["progress"] / 100}
                      for t in p["tasks"]])
    y = alt.Y("Task:N", sort=None, title=None)
    bars = alt.Chart(g).mark_bar(cornerRadius=3, size=16).encode(
        y=y, x=alt.X("start:Q", title="Project day"), x2="end:Q",
        color=alt.Color("Level:N", scale=ui.level_scale, legend=alt.Legend(title="Delay risk", orient="top")),
        stroke=alt.condition(alt.datum.Critical, alt.value("#ffffff"), alt.value("transparent")), strokeWidth=alt.value(1.5),
        tooltip=["Task", "Owner", "start", "end", alt.Tooltip("Risk:Q", title="Delay risk %"), "Critical"])
    prog = alt.Chart(g).mark_bar(size=4, color="#0a0f1a", opacity=.6).encode(y=y, x="start:Q", x2="pend:Q")
    today = alt.Chart(pd.DataFrame({"x": [p["today"]]})).mark_rule(color="#fbbf24", strokeWidth=2).encode(x="x:Q")
    dl = alt.Chart(pd.DataFrame({"x": [p["deadline"]]})).mark_rule(color="#fb7185", strokeDash=[6, 4], strokeWidth=2).encode(x="x:Q")
    return ui.dark((bars + prog + today + dl).properties(height=28 * len(g) + 60))


def risk_chart(p):
    d = pd.DataFrame([{"Task": t["name"], "Delay risk": t["risk"] * 100, "Level": t["level"]} for t in p["tasks"]])
    bars = alt.Chart(d).mark_bar(cornerRadius=3).encode(
        y=alt.Y("Task:N", sort="-x", title=None), x=alt.X("Delay risk:Q", scale=alt.Scale(domain=[0, 100]), title="Delay risk %"),
        color=alt.Color("Level:N", scale=ui.level_scale, legend=None), tooltip=["Task", alt.Tooltip("Delay risk:Q", format=".0f")])
    rules = alt.Chart(pd.DataFrame({"x": [35, 60]})).mark_rule(color="#4b5f80", strokeDash=[4, 4]).encode(x="x:Q")
    return ui.dark((bars + rules).properties(height=28 * len(d) + 40))


def dep_graph(p):
    q = lambda s: str(s).replace('"', "'")
    L = ['digraph G{rankdir=LR;bgcolor="transparent";nodesep=.35;ranksep=.5;node[shape=box,style="rounded,filled",fontname="Helvetica",'
         'fontsize=11,fontcolor="#e6edf7",fillcolor="#111a2b"];edge[color="#4b5f80",arrowsize=.7];']
    for i, t in enumerate(p["tasks"]):
        L.append(f'n{i}[label="{q(t["name"])}\\n{q(t["owner"])} · {t["duration"]}d",color="{ui.COL[t["level"]]}",penwidth={2.6 if t["critical"] else 1}];')
    for i, t in enumerate(p["tasks"]):
        for d in t["deps"]:
            hot = t["critical"] and p["tasks"][d]["critical"]
            L.append(f'n{d}->n{i}[color="{"#fb7185" if hot else "#4b5f80"}",penwidth={2.4 if hot else 1}];')
    return "".join(L) + "}"


# ---------------------------------------------------------------- mission control
with t_dash:
    a, b = st.columns([4, 1])
    p["today"] = a.slider("Today (project day)", 0, max(p["end"], p["deadline"]), p["today"])
    agent.analyse(p)
    done = sum(t["progress"] * t["duration"] for t in p["tasks"]) / sum(t["duration"] for t in p["tasks"])
    overdue = sum(t["ef"] <= p["today"] and t["progress"] < 100 for t in p["tasks"])
    hi = sum(t["level"] == "High" for t in p["tasks"])
    score, label = analytics.health_score(p)
    tone = "good" if score >= 75 else "warn" if score >= 50 else "bad"
    late = p["end"] - p["deadline"]
    over = p["cost"] - p["budget"]
    k = st.columns([1.35, 1, 1, 1, 1])
    k[0].markdown(ui.ring(score, label, tone), unsafe_allow_html=True)
    k[1].markdown(ui.kpi("Complete", f"{done:.0f}%", f"{overdue} overdue", "bad" if overdue else "good"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi("Forecast finish", f"Day {p['end']}", f"{abs(late)} days {'late' if late > 0 else 'early or on time'}",
                         "bad" if late > 0 else "good"), unsafe_allow_html=True)
    k[3].markdown(ui.kpi("Planned cost", f"{p['cost'] / 1000:.1f}k", f"{abs(over) / 1000:.1f}k {'over' if over > 0 else 'under'} budget",
                         "bad" if over > 0 else "good"), unsafe_allow_html=True)
    k[4].markdown(ui.kpi("High-risk tasks", str(hi), "predicted delay above 60%", "bad" if hi else "good"), unsafe_allow_html=True)
    st.write("")
    with st.container(key="panel-gantt"):
        ui.head("Schedule", "White outline = critical path. Dark inner bar = progress. Amber line = today, red dashed = deadline.")
        st.altair_chart(gantt(p), width="stretch")
    left, right = st.columns([3, 2])
    with left, st.container(key="panel-agent"):
        ui.head("Agent console", "Recommendations are proposals. Nothing changes until you approve.")
        if not p["recs"]:
            st.markdown('<div class="rc"><div class="tx">All clear</div><div class="wy">No actions needed. Move the day slider or update progress to re-check.</div></div>', unsafe_allow_html=True)
        for r in list(p["recs"]):
            st.markdown(ui.rec_card(r), unsafe_allow_html=True)
            x1, x2, _ = st.columns([1, 1, 4])
            if x1.button("Approve", key=f"a{r['id']}", type="primary"):
                agent.apply_recommendation(p, r, True)
                st.rerun()
            if x2.button("Reject", key=f"r{r['id']}"):
                agent.apply_recommendation(p, r, False)
                st.rerun()
        st.markdown("**Decision log**")
        st.markdown(ui.terminal(p["log"]), unsafe_allow_html=True)
    with right, st.container(key="panel-risk"):
        ui.head("Delay-risk ranking", "Dashed lines mark the medium (35%) and high (60%) thresholds.")
        st.altair_chart(risk_chart(p), width="stretch")

# ---------------------------------------------------------------- tasks and risk
with t_risk:
    with st.container(key="panel-prog"):
        ui.head("Update progress", "Drag a slider as work completes. Risks and recommendations recalculate.")
        cols = st.columns(3)
        for i, t in enumerate(p["tasks"]):
            t["progress"] = cols[i % 3].slider(f"{t['name']} ({t['owner']})", 0, 100, t["progress"], 10, key=f"pg{i}")
    agent.analyse(p)
    with st.container(key="panel-table"):
        ui.head("Task risk table", "Risk factors come from the model's explainer, not a black box.")
        st.dataframe(pd.DataFrame([{"Task": t["name"], "Owner": t["owner"], "Days": t["duration"], "Slack": t["slack"],
                                    "Critical": t["critical"], "Delay risk": round(t["risk"] * 100), "Level": t["level"],
                                    "Main factors": ", ".join(t["factors"]) or "None significant"} for t in p["tasks"]]),
                     hide_index=True, width="stretch",
                     column_config={"Delay risk": st.column_config.ProgressColumn("Delay risk", min_value=0, max_value=100, format="%d%%"),
                                    "Critical": st.column_config.CheckboxColumn("Critical path")})
    with st.container(key="panel-graph"):
        ui.head("Dependency network", "Box colour = delay risk. Thick red path = critical path.")
        st.graphviz_chart(dep_graph(p))

# ---------------------------------------------------------------- forecast
with t_fc:
    mc = analytics.monte_carlo(p["tasks"], p["deadline"])
    pot = mc["p_on_time"]
    k = st.columns(4)
    k[0].markdown(ui.kpi("Chance of meeting deadline", f"{pot:.0%}", f"deadline day {p['deadline']}",
                         "good" if pot >= .8 else "warn" if pot >= .5 else "bad"), unsafe_allow_html=True)
    k[1].markdown(ui.kpi("Median finish (P50)", f"Day {mc['p50']:.0f}", "half of simulations finish sooner"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi("Safe finish (P80)", f"Day {mc['p80']:.0f}", "plan commitments here", "warn"), unsafe_allow_html=True)
    k[3].markdown(ui.kpi("Worst case (P95)", f"Day {mc['p95']:.0f}", "1 in 20 runs is slower"), unsafe_allow_html=True)
    st.write("")
    with st.container(key="panel-mc"):
        ui.head("Finish-date simulation", "2,000 runs. Riskier tasks get wider duration uncertainty; completed tasks are fixed.")
        sim = pd.DataFrame({"end": mc["end"]})
        sim["Result"] = (sim.end <= p["deadline"]).map({True: "On time", False: "Late"})
        h = alt.Chart(sim).mark_bar(cornerRadius=2).encode(
            x=alt.X("end:Q", bin=alt.Bin(maxbins=32), title="Finish day"), y=alt.Y("count()", title="Runs"),
            color=alt.Color("Result:N", scale=alt.Scale(domain=["On time", "Late"], range=["#3dd6f5", "#fb7185"]), legend=alt.Legend(orient="top", title=None)))
        rule = alt.Chart(pd.DataFrame({"x": [p["deadline"]]})).mark_rule(color="#fbbf24", strokeWidth=2).encode(x="x:Q")
        st.altair_chart(ui.dark((h + rule).properties(height=260)), width="stretch")
    with st.container(key="panel-cost"):
        ui.head("Planned spend", "Cumulative cost against budget.")
        days, cum = analytics.cost_curve(p)
        cd = pd.DataFrame({"Day": days, "Cost": cum})
        area = alt.Chart(cd).mark_area(color="#3dd6f5", opacity=.25, line={"color": "#3dd6f5"}).encode(x="Day:Q", y=alt.Y("Cost:Q", title="Cumulative cost"))
        br = alt.Chart(pd.DataFrame({"y": [p["budget"]]})).mark_rule(color="#fb7185", strokeDash=[6, 4], strokeWidth=2).encode(y="y:Q")
        st.altair_chart(ui.dark((area + br).properties(height=220)), width="stretch")

# ---------------------------------------------------------------- responsible AI
with t_ai:
    with st.container(key="panel-rai"):
        ui.head("How this system makes decisions", "Plain-language summary for reviewers and stakeholders.")
        st.markdown(ui.cards([
            ("Planning", "An LLM (when an API key is set) or keyword templates split the project into tasks. Treat the result as a first draft."),
            ("Scheduling", "Critical Path Method finds each task's slack and the chain that decides the finish date."),
            ("Delay prediction", "A scikit-learn model trained on synthetic history scores every task. Top risk factors are shown beside each score."),
            ("Human approval", "The agent only proposes. Every change needs an explicit Approve, and rejections are logged and not repeated."),
            ("Privacy", "Project data stays in this session. Only the description goes to an LLM, and only if you configure a key. Asana tokens are never saved."),
            ("Known limits", "No real project history was used for training, so scores show the method, not proven accuracy."),
        ]), unsafe_allow_html=True)
    with st.container(key="panel-log"):
        ui.head("Audit trail", "Every decision this session.")
        st.markdown(ui.terminal(p["log"]), unsafe_allow_html=True)

# ---------------------------------------------------------------- model lab
with t_model:
    with st.container(key="panel-model"):
        ui.head("Delay-risk model", f"Deployed: {MET['best_model'].replace('_', ' ')}. Trained on {MET['train_rows']} and tested on {MET['test_rows']} synthetic rows.")
        st.dataframe(pd.DataFrame(MET["results"]).T.round(3), width="stretch")
    c1, c2 = st.columns(2)
    with c1, st.container(key="panel-cm"):
        ui.head("Confusion matrix", "Held-out test set.")
        st.image(str(model.ROOT / "models" / "confusion_matrix.png"))
    with c2, st.container(key="panel-fi"):
        ui.head("Feature influence", "Standardised weights. Positive raises delay risk, negative lowers it.")
        coef = model.load()["explainer"][-1].coef_[0]
        fi = pd.DataFrame({"Feature": [model.LABELS[f] for f in FEATURES], "Weight": coef})
        st.altair_chart(ui.dark(alt.Chart(fi).mark_bar(cornerRadius=3).encode(
            y=alt.Y("Feature:N", sort="-x", title=None), x=alt.X("Weight:Q", title="Weight"),
            color=alt.condition(alt.datum.Weight > 0, alt.value("#fb7185"), alt.value("#3dd6f5")),
            tooltip=["Feature", alt.Tooltip("Weight:Q", format=".2f")]).properties(height=280)), width="stretch")


with t_asana:
    st.subheader("Asana")
    st.caption("Create a personal access token in Asana (profile photo > Settings > Apps > Manage developer apps > "
               "Personal access tokens). It stays in this session only. Add team emails in the sidebar to assign tasks.")
    token = st.text_input("Personal access token", value=os.getenv("ASANA_TOKEN", ""), type="password")
    if st.button("Connect to Asana"):
        try:
            st.session_state.asana_ws = asana_client.Asana(token).workspaces()
            st.session_state.asana_token = token
            st.session_state.pop("asana_projects", None)
        except Exception as e:
            st.error(str(e))
    ws_list = st.session_state.get("asana_ws")
    if ws_list:
        try:
            cl = asana_client.Asana(st.session_state.asana_token)
            ws = st.selectbox("Workspace", ws_list, format_func=lambda w: w["name"])
            left, right = st.columns(2)
            with left:
                st.markdown("**Send plan to Asana**")
                start = st.date_input("Project start date", dt.date.today())
                team_gid = None
                if ws.get("is_organization"):
                    teams = cl.teams(ws["gid"])
                    team_gid = st.selectbox("Team", teams, format_func=lambda t: t["name"])["gid"] if teams else None
                if p is None:
                    st.info("Generate a plan first.")
                elif st.button("Create Asana project"):
                    r = cl.export_plan(p, st.session_state.get("name", "ProjectPilot plan"), ws["gid"], start, team_gid)
                    st.success(f"Created {len(p['tasks'])} tasks. {r['url'] or ''}")
                    for w in r["warnings"]:
                        st.warning(w)
                if p is not None and p.get("asana"):
                    st.markdown("**Keep in sync**")
                    if st.button("Push schedule, owners and progress"):
                        r = cl.push_updates(p, start)
                        st.success(f"Updated {r['updated']} tasks in Asana.")
                        for w in r["warnings"]:
                            st.warning(w)
                    if st.button("Pull completion from Asana"):
                        n = cl.pull_progress(p)
                        agent.analyse(p)
                        st.success(f"{n} tasks changed.")
            with right:
                st.markdown("**Import an Asana project**")
                if st.button("Load projects"):
                    st.session_state.asana_projects = cl.projects(ws["gid"])
                projs = st.session_state.get("asana_projects")
                if projs:
                    pr = st.selectbox("Project", projs, format_func=lambda x: x["name"])
                    dl = st.number_input("Deadline (day) for imported project", 5, 365, 40, key="imp_dl")
                    bg = st.number_input("Budget", 0, 10_000_000, 30000, step=1000, key="imp_bg")
                    if st.button("Import into ProjectPilot"):
                        nm, tasks, meta = cl.import_project(pr["gid"])
                        today = max(0, (dt.date.today() - meta["start"]).days) if meta["start"] else 0
                        proj = agent.from_tasks(tasks, int(dl), float(bg), today)
                        proj["asana"] = {"project_gid": pr["gid"], "url": None}
                        st.session_state.p = agent.analyse(proj)
                        st.session_state.name = nm
                        st.rerun()
        except asana_client.AsanaError as e:
            st.error(str(e))
