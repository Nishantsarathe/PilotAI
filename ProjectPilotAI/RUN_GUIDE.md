# ProjectPilot AI: Complete Run Guide

Everything you need to install, run, demo and troubleshoot the project, including the Asana integration.

**Contents**
1. [What this project is](#1-what-this-project-is)
2. [Requirements](#2-requirements)
3. [First-time setup](#3-first-time-setup)
4. [Running the app](#4-running-the-app-every-time)
5. [Tour of the dashboard](#5-tour-of-the-dashboard)
6. [Asana integration (step by step)](#6-asana-integration-step-by-step)
7. [Optional: LLM-powered planning](#7-optional-llm-powered-planning)
8. [Tests and retraining the model](#8-tests-and-retraining-the-model)
9. [Project structure](#9-project-structure)
10. [Demo script for your presentation](#10-demo-script-for-your-presentation)
11. [Troubleshooting](#11-troubleshooting)
12. [Limitations and honest notes](#12-limitations-and-honest-notes)
13. [Security notes](#13-security-notes)

---

## 1. What this project is
ProjectPilot AI turns a project description into a schedule, predicts which tasks are likely to be delayed, explains why, simulates the finish date, and proposes fixes that a human approves or rejects. It can send the plan to Asana, import an existing Asana project, and keep both in sync.

Main parts: planner, critical-path scheduler, resource optimizer, delay-prediction model (scikit-learn), AI project-manager agent with human approval, Monte Carlo forecast, Streamlit dashboard, Asana connector.

## 2. Requirements
- **Python 3.10 or newer.** Check with `python --version`.
- **Internet** for installing packages the first time. The dashboard loads fonts from Google Fonts; without internet it still works with system fonts.
- **Optional:** an Asana account (free works for most features) and an Anthropic API key for the LLM planner.

## 3. First-time setup

### Step 1. Extract the zip and open the right folder
Extract `ProjectPilotAI.zip`. Open the folder that **directly contains `app.py` and `requirements.txt`**. Zips often extract into a folder inside a folder. If you see `ProjectPilotAI\ProjectPilotAI`, go into the inner one.

In VS Code: File > Open Folder, choose the folder that contains `app.py`, then open a terminal (Terminal > New Terminal). Run `dir` (Windows) or `ls` (Mac/Linux) and confirm you can see `app.py`.

### Step 2. Create a virtual environment
**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```
If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` and activate again.

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Your prompt should now start with `(.venv)`.

### Step 3. Install dependencies
```bash
pip install -r requirements.txt
```
This takes a few minutes the first time. Messages about a newer pip version can be ignored.

## 4. Running the app (every time)
```bash
streamlit run app.py
```
The browser opens at **http://localhost:8501**. If it doesn't, paste that address into your browser. If Streamlit asks for an email, press Enter to skip.

To stop the app, click in the terminal and press **Ctrl + C**.

**Coming back later:** open a terminal in the project folder, activate the environment again, and run the app:
```powershell
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
streamlit run app.py
```
If `streamlit` is not recognized, the environment isn't active. Use `python -m streamlit run app.py`.

**No Python?** Double-click `web/projectpilot.html` for the lightweight browser-only demo (no Asana, no trained model).

## 5. Tour of the dashboard
The app loads a **demo project** on first start (deadline day 25, budget 15,000) so there is always something to look at. Use the left sidebar to enter your own project and select **Generate plan**.

| Tab | What you see |
|---|---|
| **Mission control** | Project health score, KPI cards, Gantt chart (bar colour = delay risk, white outline = critical path, amber line = today, red dashed = deadline), the **agent console** with Approve/Reject buttons, decision log, risk ranking. Use the **Today** slider to simulate project time passing. |
| **Tasks and risk** | Progress sliders for each task, a risk table with the main risk factors, and a dependency network graph. |
| **Forecast** | Monte Carlo simulation: chance of meeting the deadline, P50/P80/P95 finish days, and the planned-spend curve vs budget. |
| **Responsible AI** | Plain-language explanation of how decisions are made, plus an audit trail of your approvals and rejections. |
| **Model lab** | Model metrics, confusion matrix, and which factors raise or lower delay risk. |
| **Asana** | Connect, send the plan, import a project, and sync (section 6). |

**Sidebar fields**
- *Project name / description:* the description decides which task template the planner uses (software, event or general), or is sent to the LLM if configured.
- *Deadline (day) and Budget:* used for forecast, cost checks and recommendations.
- *Team and skills:* one row per person. Skills are comma-separated from `plan, design, data, dev, test, ops`. `load` is current workload in percent. `email` is the person's **Asana login email** (needed to assign tasks in Asana).

**Agent console:** the agent only proposes changes (reassign a risky task, add a buffer, shorten a critical task, flag budget overrun). Nothing changes until you press **Approve**. Rejected suggestions are logged and not shown again.

## 6. Asana integration (step by step)

### 6.1 Create a personal access token
1. Sign in to Asana.
2. Click your profile photo (top right) > **Settings** > **Apps** > **Manage developer apps**. Direct link: `https://app.asana.com/0/my-apps`.
3. Under **Personal access tokens**, choose **Create new token**, name it (for example "ProjectPilot"), accept the terms, and **copy the token immediately**. Asana shows it only once.

Menu names can change slightly over time. If you can't find it, search "personal access token" in the Asana help center.

### 6.2 Connect the app
1. In ProjectPilot, open the **Asana** tab.
2. Paste the token in **Personal access token** and select **Connect to Asana**.
3. Pick your **Workspace** from the dropdown. The header chip changes to "Asana connected".

Optional: set the token before launching so you don't paste it each time.
```powershell
$env:ASANA_TOKEN="your-token-here"      # Windows PowerShell
streamlit run app.py
```
```bash
export ASANA_TOKEN="your-token-here"    # Mac / Linux
streamlit run app.py
```

### 6.3 Send your plan to Asana
1. In the sidebar, add each teammate's **Asana email** in the team table (optional; without emails, tasks are created unassigned).
2. Generate or review your plan.
3. In the Asana tab, left column: pick a **Project start date**. If your workspace is an organization, also pick a **Team** (Asana requires one).
4. Select **Create Asana project**.

What gets created:
- A new project with your project name.
- One task per ProjectPilot task, with **start and due dates** calculated from the critical-path schedule (calendar days from your start date; weekends are not skipped).
- Task notes containing the skill, predicted delay risk and main risk factors.
- **Dependencies** between tasks, if your Asana plan supports them. If not, you get a warning and the tasks are still created.
- **Assignees** when the team email matches a user in that workspace. If an email is not recognised, that task is created unassigned and you get a warning.
- Tasks that were already 100% complete are created as completed.

### 6.4 Keep both sides in sync
After you approve recommendations or update progress, the Asana tab shows a **Keep in sync** section:
- **Push schedule, owners and progress** updates every linked task in Asana: new dates, new assignee, and completion.
- **Pull completion from Asana** reads Asana and updates ProjectPilot: tasks checked off in Asana become 100% complete, and tasks you reopened go back to 0%. Risks and forecasts recalculate.

Sync works only for the project created or imported in the current session. Pressing **Generate plan** in the sidebar creates a new plan and breaks the link to Asana, so push before regenerating.

### 6.5 Import an existing Asana project
1. In the Asana tab, right column, select **Load projects**.
2. Choose a project, enter its **deadline (day)** and **budget** (Asana doesn't hold these), and select **Import into ProjectPilot**.
3. ProjectPilot loads the tasks, dates, assignees, dependencies and completion status, then runs the risk analysis, forecast and recommendations on them.

How import maps data:
| Asana | ProjectPilot |
|---|---|
| Task name | Task name |
| Start and due date | Duration in days (3 days if dates are missing, capped at 90) |
| Assignee | Owner. People found become the team, and their owner assignments are kept |
| Dependencies | Dependencies (tasks are reordered so prerequisites come first) |
| Completed | Progress 100% (otherwise 0%) |
| Task name keywords | **Guessed** skill (design, dev, test, data, ops, or plan by default) |

Not imported: subtasks, sections, custom fields, attachments, and comments. Imported schedules are recomputed from dependencies, so the Gantt chart may differ from Asana's own dates.

### 6.6 Asana limits and notes
- Asana allows a limited number of requests per minute. The app waits and retries automatically when Asana says to slow down. Very large projects may take a while.
- Creating a project makes one request per task, plus one per task with dependencies.
- **Test first on a throwaway project.** The integration passes automated tests with a simulated Asana, but has not been run against a live account, so check your first export carefully.
- Your token is kept in memory for the session only. It is never saved to a file.

## 7. Optional: LLM-powered planning
Without a key, the planner uses built-in templates (software, event, general). With a key, an Anthropic model splits your project description into tasks, durations, dependencies and skills.

```powershell
$env:ANTHROPIC_API_KEY="your-key-here"       # Windows PowerShell
streamlit run app.py
```
```bash
export ANTHROPIC_API_KEY="your-key-here"     # Mac / Linux
streamlit run app.py
```
The header chip **Planner** shows "LLM" when it is active. If the call fails for any reason, the app silently falls back to templates and keeps working. To use a different model, set `PROJECTPILOT_MODEL`.

## 8. Tests and retraining the model
Run from the project folder with the environment active:
```bash
pytest                          # 10+ tests: scheduler, model, agent, Asana (simulated), analytics
python -m projectpilot.model    # retrain the delay model, refresh metrics and confusion matrix
python -m projectpilot.data     # regenerate data/synthetic_tasks.csv
```
The trained model is saved in `models/`. If it is missing, the app trains it automatically on start.

## 9. Project structure
```
ProjectPilotAI/
├── app.py                       Streamlit dashboard
├── RUN_GUIDE.md                 this file
├── README.md                    short overview
├── requirements.txt             Python dependencies
├── .streamlit/config.toml       dark theme
├── projectpilot/
│   ├── agent.py                 AI project manager: plan, predict, recommend, approve
│   ├── planner.py               LLM planner with template fallback
│   ├── scheduler.py             Critical Path Method
│   ├── optimizer.py             Skill and workload based assignment
│   ├── model.py                 Train, evaluate and explain the delay model
│   ├── data.py                  Synthetic training data
│   ├── analytics.py             Monte Carlo forecast, health score, cost curve
│   ├── asana_client.py          Asana export, import, sync
│   └── ui.py                    Theme and dashboard components
├── models/                      Trained model, metrics.json, confusion_matrix.png
├── data/synthetic_tasks.csv     Training data
├── docs/REPORT.md               Project report and course-module mapping
├── tests/                       Automated tests
└── web/projectpilot.html        Browser-only demo
```

## 10. Demo script for your presentation
1. Start the app and show the demo project: the health score is "At risk" because the plan finishes after the deadline.
2. **Mission control:** point out the critical path (white outlines) and the risk colours.
3. Open **Agent console**. Read a recommendation, **Approve** one and **Reject** another, and show the decision log. Stress the human-in-the-loop design.
4. **Tasks and risk:** move a progress slider and the **Today** slider, and watch risks and recommendations change.
5. **Forecast:** show the chance of meeting the deadline and explain P50 vs P80.
6. **Model lab:** explain accuracy, precision, recall, F1, ROC-AUC and the confusion matrix. State clearly that the data is synthetic.
7. **Asana:** connect, create the project, open it in Asana to show the dates and dependencies, check a task off in Asana, then pull completion back.
8. **Responsible AI:** privacy, explainability, human approval, limitations.

Course mapping: Module 1 (AI concepts), 2 (tools), 3 (data-driven decisions), 4 (collaboration through Asana), 5 (ethics and bias), 6 (implementation and ROI), 7 (future and forecasting), and AI Agents (the agent module). `docs/REPORT.md` has the full table.

## 11. Troubleshooting
| Problem | Fix |
|---|---|
| `Could not open requirements file` or `File does not exist: app.py` | You are in the wrong folder. Run `dir` / `ls`, and `cd` into the folder that contains `app.py`. |
| `'streamlit' is not recognized` | Activate the environment (`.venv\Scripts\activate`) or run `python -m streamlit run app.py`. |
| PowerShell says scripts are disabled | `Set-ExecutionPolicy -Scope Process Bypass`, then activate again. |
| `ModuleNotFoundError` | Environment not active or install incomplete. Activate it and rerun `pip install -r requirements.txt`. |
| Page doesn't open | Go to http://localhost:8501 manually, or use another port: `streamlit run app.py --server.port 8502`. |
| Port already in use | Close the old terminal (Ctrl + C) or use another port as above. |
| Error mentioning `width` or `use_container_width` | Streamlit is too old. Run `pip install -U streamlit`. |
| Layout looks unstyled | The `.streamlit` folder must stay in the project root. Hidden folders can be skipped by some unzip tools. Create `.streamlit/config.toml` again from `README.md` or re-extract the zip. |
| Asana: `401 Not Authorized` | Token is wrong, expired or revoked. Create a new one and reconnect. |
| Asana: `403` or "not a member" | Your account can't access that workspace, team or project. Choose another or ask the owner for access. |
| Asana: project creation fails in an organization | Pick a **Team** in the Asana tab. Organizations require one. |
| Asana: "created without assignee" warning | The email isn't a user in that workspace. Check spelling and use their Asana login email. |
| Asana: "Dependencies not created" warning | Your Asana plan may not support task dependencies. The tasks themselves were still created. |
| Asana: `429` or slow sync | Asana rate limit. The app retries automatically. Wait a minute for large projects. |
| Import shows wrong skills or durations | Skills are guessed from task names and durations come from start/due dates. Add dates in Asana or edit names, then import again. |
| LLM planner chip says "template" | `ANTHROPIC_API_KEY` is not set in the terminal that started Streamlit, or the call failed. Set the variable and restart the app. |

## 12. Limitations and honest notes
- The delay model is trained on **synthetic** data. Its metrics show the method works; they are not real-world accuracy. Replace `data.generate()` with real task history to make the predictions meaningful.
- Template planning is simple keyword matching. Use the LLM planner or edit the plan for real projects.
- Costs use a flat daily rate (400 per task-day) and one person per task. There are no resource calendars, holidays or weekends.
- The Asana integration is covered by simulated tests but has not been run against a live Asana account.
- The Monte Carlo forecast assumes the duration uncertainty rule in `analytics.py`, which is a modelling assumption, not measured data.

## 13. Security notes
- Never commit your Asana token or Anthropic key to Git or share them in screenshots. If one leaks, revoke it in the provider's settings and create a new one.
- Asana tokens act as you. Anyone with the token can read and change what you can. Revoke tokens you no longer need.
- Project descriptions are sent to the LLM only when `ANTHROPIC_API_KEY` is set. Don't enter confidential details if you don't want them processed by an external service.
