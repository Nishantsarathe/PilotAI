# ProjectPilot AI

> **Full setup, Asana guide, demo script and troubleshooting: see [RUN_GUIDE.md](RUN_GUIDE.md).**
An agentic AI system for intelligent project planning and monitoring (course project: *Managing Projects with AI*).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Optional LLM planner: `export ANTHROPIC_API_KEY=...` (without it, the planner uses built-in templates).
No Python? Open `web/projectpilot.html` in any browser for the standalone demo.

Retrain the delay model: `python -m projectpilot.model` (or `python -c "from projectpilot import model; model.train()"`). Run tests: `pytest`.

## What's in the dashboard
- **Mission control:** project health score, KPIs, risk-coloured Gantt chart with critical path, agent console with approve/reject, decision log.
- **Tasks and risk:** progress sliders, sortable risk table, dependency network graph.
- **Forecast:** Monte Carlo finish-date simulation (chance of meeting the deadline, P50/P80/P95) and planned-spend curve.
- **Responsible AI** and **Model lab:** how decisions are made, metrics, confusion matrix, feature influence.
- **Asana:** export, import and sync (see below).

The dark theme lives in `.streamlit/config.toml` and `projectpilot/ui.py`. Keep the `.streamlit` folder in the project root. The app loads a demo project on first start, and **Generate plan** replaces it.

## Structure
| Path | Purpose |
|---|---|
| `app.py` | Streamlit dashboard (plan, Gantt, risks, approvals, model evaluation) |
| `projectpilot/planner.py` | Generative planner: LLM with template fallback |
| `projectpilot/scheduler.py` | Critical Path Method (slack, critical tasks) |
| `projectpilot/optimizer.py` | Resource optimizer (skill match + workload) |
| `projectpilot/model.py` | Delay-risk ML model: training, evaluation, explanations |
| `projectpilot/agent.py` | AI project-manager agent with human approval |
| `projectpilot/asana_client.py` | Asana REST API: export, import, two-way sync |
| `projectpilot/analytics.py` | Monte Carlo forecast, health score, cost curve |
| `projectpilot/ui.py` | Theme CSS and dashboard components |
| `projectpilot/data.py` | Synthetic training data generator |
| `models/` | Trained model, `metrics.json`, `confusion_matrix.png` |
| `docs/REPORT.md` | Project report and course-module mapping |
| `tests/` | Unit tests |

## Asana integration
Open the **Asana** tab in the app.
1. Create a personal access token in Asana: profile photo > Settings > Apps > Manage developer apps > Personal access tokens. Paste it in the tab (or set `ASANA_TOKEN`). It is kept in memory only.
2. Optional: add each teammate's Asana email in the sidebar team table so tasks are assigned to them.
3. **Send plan to Asana** creates a project with tasks, start/due dates from the critical-path schedule, risk notes and dependencies.
4. **Import an Asana project** loads its tasks, dates, assignees and dependencies into ProjectPilot for risk analysis.
5. To sync an existing project with a generated plan, load projects, select the Asana project, and choose **Link current plan to selected Asana project**. Automatic completion sync pushes completion changes from ProjectPilot and checks Asana every 15 seconds. Turn it off in **Keep in sync** to pause it. Manual push and pull remain available.

Notes: task dependencies need an Asana plan that supports them (you get a warning if not). Organization workspaces require choosing a team. Imported durations come from start/due dates (3 days if missing) and skills are guessed from task names. The integration is covered by mocked tests; it has not been run against a live Asana account.

## Important limitations
The delay model is trained on **synthetic** data, so its scores show the method working, not real-world accuracy. Replace `data.generate()` with your organization's task history before relying on it.
