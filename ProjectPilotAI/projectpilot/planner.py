"""Generative planner. Uses an LLM when ANTHROPIC_API_KEY is set, else template fallback."""
import json
import os
import re

TEMPLATES = {
    "software": (r"app|web|software|portal|website|system|platform|api|dashboard", [
        ("Requirements", 4, [], "plan"), ("UI design", 5, [0], "design"), ("Data model", 3, [0], "data"),
        ("Backend build", 8, [2], "dev"), ("Frontend build", 7, [1], "dev"), ("Integration", 4, [3, 4], "dev"),
        ("Testing", 5, [5], "test"), ("Documentation", 3, [5], "ops"), ("Deployment", 2, [6, 7], "ops")]),
    "event": (r"event|conference|wedding|festival|fest", [
        ("Goals and budget", 3, [], "plan"), ("Venue and dates", 4, [0], "ops"),
        ("Speakers and vendors", 6, [0], "plan"), ("Branding and invites", 5, [1], "design"),
        ("Registration setup", 4, [1], "data"), ("Logistics rehearsal", 3, [2, 3, 4], "ops"),
        ("Event day", 1, [5], "ops"), ("Feedback report", 3, [6], "data")]),
    "general": (r".", [
        ("Define scope", 3, [], "plan"), ("Research", 4, [0], "data"), ("Design the approach", 5, [1], "design"),
        ("Build or execute", 8, [2], "dev"), ("Review and test", 3, [3], "test"), ("Handover", 2, [4], "ops")]),
}
SKILLS = ["plan", "design", "data", "dev", "test", "ops"]


def _template(desc: str):
    for key, (rx, tasks) in TEMPLATES.items():
        if re.search(rx, desc, re.I):
            return [dict(name=n, duration=d, deps=list(dp), skill=s) for n, d, dp, s in tasks], "template:" + key


def _llm(desc: str):
    import anthropic
    client = anthropic.Anthropic()
    prompt = ("Break this project into 6-12 tasks. Return ONLY a JSON list of objects with keys "
              f"name, duration (days, int), deps (list of earlier task indices), skill (one of {SKILLS}). "
              "Dependencies must only reference earlier indices.\nProject: " + desc)
    msg = client.messages.create(model=os.getenv("PROJECTPILOT_MODEL", "claude-sonnet-5-5"),
                                 max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    text = re.sub(r"```(json)?", "", msg.content[0].text).strip()
    tasks = json.loads(text)
    for i, t in enumerate(tasks):
        t["deps"] = [d for d in t.get("deps", []) if isinstance(d, int) and 0 <= d < i]
        t["duration"] = max(1, int(t["duration"]))
        t["skill"] = t["skill"] if t["skill"] in SKILLS else "plan"
    return tasks, "llm"


def generate_plan(desc: str):
    """Returns (tasks, source). Falls back to templates on any LLM problem."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _llm(desc)
        except Exception as e:  # network, parsing, validation
            tasks, src = _template(desc)
            return tasks, src + f" (LLM failed: {type(e).__name__})"
    return _template(desc)
