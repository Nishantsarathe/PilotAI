# ProjectPilot AI: Project Report

## 1. Problem and goals
Project managers spend much of their time building plans, balancing workloads and spotting delays late. ProjectPilot AI turns a project description into a schedule, predicts which tasks are likely to slip, explains why, and proposes corrective actions that a manager approves or rejects.

## 2. Features and AI concepts
| Feature | What it does | AI concept |
|---|---|---|
| Project Planner | Converts a description into tasks, dependencies, skills | Generative AI / NLP |
| Smart Scheduler | Critical Path Method: start/finish, slack, critical path | Optimization |
| Delay Predictor | Probability that each task is delayed | Machine learning |
| Risk Analyzer | Top contributing factors per task | Explainable predictive analytics |
| Resource Optimizer | Assigns owners by skill and workload | Optimization |
| AI Project Manager | Reviews status, recommends actions | AI agent |
| Asana integration | Exports plans to Asana, imports existing projects, syncs schedule and completion | Tool integration |
| Forecast | Monte Carlo simulation gives the probability of meeting the deadline | Predictive analytics |
| Dashboard | Completion, forecast, cost, overdue, risk, Gantt | Data visualization |
| Responsible AI | Explanations, approval gate, decision log, privacy notes | AI ethics |

## 3. Method
**Agent workflow:** plan -> assign -> schedule -> predict risk -> recommend -> human approval -> re-analyse.
**Data:** 4,000 synthetic task records (duration, dependencies, owner workload, slack, skill match, progress gap, team size) with a delay label generated from a noisy risk formula. 75/25 stratified train/test split.
**Models compared:** logistic regression and random forest; the one with the higher F1 is deployed. Logistic coefficients also provide per-task explanations.

## 4. Results (held-out test set, 1,000 rows)
| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic regression (deployed) | 0.751 | 0.707 | 0.630 | 0.667 | 0.811 |
| Random forest | 0.736 | 0.697 | 0.587 | 0.637 | 0.796 |

Confusion matrix (deployed): 502 true on-time, 103 false alarms, 146 missed delays, 249 caught delays (see `models/confusion_matrix.png`).
**Interpretation:** the model catches about 63% of delays with about 71% of alerts being correct. The simpler linear model beat the forest because the synthetic labels follow a near-linear rule; on real data, re-run the comparison.

## 5. Mapping to course modules
| Module | Where it appears |
|---|---|
| 1. Introduction to AI | ML, NLP (planner), optimization (scheduler, optimizer) |
| 2. AI tools | Scheduling, resource allocation, risk analysis, reporting |
| 3. Data-driven decisions | Training data, KPIs, dashboard, forecasts |
| 4. Collaboration | Task owners, workload view, decision log, Asana sync for the whole team |
| 5. Ethics and bias | Explanations, human approval, privacy, stated limits |
| 6. Implementation | Data prep, model evaluation, tests, deployment steps, ROI inputs (cost vs budget) |
| 7. Future of AI | Predictive forecasting, continuous re-analysis as progress changes |
| AI Agents | `agent.py`: autonomous analysis with a human-in-the-loop gate |

## 6. Responsible AI
- **Transparency:** every risk score lists its main factors.
- **Human control:** recommendations apply only after explicit approval; rejections are logged and not repeated.
- **Privacy:** data stays in the session; the project description is sent to an LLM only if an API key is configured.
- **Bias and fairness:** the optimizer uses skills and workload only, never personal attributes. With real data, audit predictions across teams and roles.
- **Limits:** synthetic training data, template-based fallback planning, a fixed daily cost rate, and no resource calendars.

## 7. Future work
Train on real project history, add resource calendars and cost rates per person, integrate with Jira or Asana, add monitoring for model drift, and let the agent propose multi-step recovery plans.

## 8. Suggested demo script
1. Generate a plan for the default project and note the forecast is past the deadline.
2. Open Model evaluation and explain the metrics.
3. Move the day slider, update progress, and watch risks change.
4. Approve one recommendation and reject another; show the decision log.
