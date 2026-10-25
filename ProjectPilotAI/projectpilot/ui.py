"""Visual layer: theme CSS and small HTML components for the Streamlit app."""
import html
import math

import altair as alt
import streamlit as st

COL = {"High": "#fb7185", "Medium": "#fbbf24", "Low": "#3dd6f5"}
TONE = {"good": "#34d399", "warn": "#fbbf24", "bad": "#fb7185", "": "#3dd6f5"}

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
:root{--bg:#0a0f1a;--p1:#111a2b;--p2:#162238;--ln:#223250;--tx:#e6edf7;--mu:#8da2c0;--cy:#3dd6f5;--ok:#34d399;--wn:#fbbf24;--bd:#fb7185}
.stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:'Space Grotesk',system-ui,sans-serif}
.stApp{background-color:var(--bg);background-image:linear-gradient(rgba(61,214,245,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(61,214,245,.035) 1px,transparent 1px);background-size:36px 36px}
#MainMenu,footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1400px;padding-top:1.1rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#0d1524;border-right:1px solid var(--ln)}
[data-testid="stSidebar"] .stButton>button{width:100%}
.mono,.kv,.ring .rt{font-family:'JetBrains Mono',ui-monospace,monospace}
.hero{display:flex;align-items:center;gap:16px;flex-wrap:wrap;justify-content:space-between;padding:6px 0 14px}
.hero .l{display:flex;align-items:center;gap:14px}
.hero .t{font:700 1.7rem/1.1 'Space Grotesk';letter-spacing:-.01em;color:var(--tx)}
.hero .s{color:var(--mu);font-size:.92rem;margin-top:2px}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--ln);background:var(--p1);color:var(--mu);border-radius:999px;padding:4px 11px;font-size:.78rem}
.chip b{color:var(--tx);font-weight:500}
.dot{width:7px;height:7px;border-radius:50%;background:var(--mu);display:inline-block}
.dot.ok{background:var(--ok);box-shadow:0 0 8px var(--ok)}.dot.off{background:#4b5f80}
.pipe{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.pst{display:flex;align-items:center;gap:7px;padding:5px 11px;border:1px solid var(--ln);border-radius:6px;background:var(--p1);color:var(--mu);font-size:.82rem}
.pst.done{color:var(--tx);border-color:#1f4a57}.pst.done i{background:var(--cy)}
.pst.act{color:var(--tx);border-color:var(--wn)}.pst.act i{background:var(--wn);box-shadow:0 0 8px var(--wn)}
.pst i{width:8px;height:8px;border-radius:2px;background:#33466a}
.pln{width:18px;height:1px;background:var(--ln)}
.kpi{background:var(--p1);border:1px solid var(--ln);border-left:3px solid var(--cy);border-radius:10px;padding:13px 16px;height:100%}
.kpi.good{border-left-color:var(--ok)}.kpi.warn{border-left-color:var(--wn)}.kpi.bad{border-left-color:var(--bd)}
.kl{color:var(--mu);font-size:.8rem}
.kv{font-weight:600;font-size:1.75rem;line-height:1.2;color:var(--tx)}
.ks{color:var(--mu);font-size:.8rem;margin-top:2px}
.kpi.ring{display:flex;align-items:center;gap:14px;border-left-width:1px}
.kv2{font-weight:700;font-size:1.35rem;color:var(--tx)}
.ring .rt{font-size:22px;font-weight:600}
div[class*="st-key-panel"]{background:var(--p1);border:1px solid var(--ln);border-radius:12px;padding:16px 18px 10px;margin-bottom:14px}
.ph{font-weight:600;font-size:1.02rem;color:var(--tx);margin:0 0 2px}
.pd{color:var(--mu);font-size:.84rem;margin:0 0 10px}
.rc{border:1px solid var(--ln);background:var(--p2);border-radius:8px;padding:10px 12px;margin:6px 0 4px}
.rc .tx{color:var(--tx);font-weight:500}.rc .wy{color:var(--mu);font-size:.85rem;margin-top:3px}
.tag{display:inline-block;font-size:.72rem;padding:1px 8px;border-radius:4px;margin-right:8px;border:1px solid currentColor}
.term{background:#070b13;border:1px solid var(--ln);border-radius:8px;padding:10px 14px;font:12.5px/1.75 'JetBrains Mono',monospace;color:#b9c8df;overflow-x:auto}
.term .ok{color:var(--ok)}.term .no{color:var(--bd)}.term .m{color:#5d7399}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}
.card{background:var(--p2);border:1px solid var(--ln);border-radius:10px;padding:14px 16px}
.card h4{margin:0 0 4px;font-size:.98rem;color:var(--tx)}.card p{margin:0;color:var(--mu);font-size:.86rem;line-height:1.5}
button[role="tab"]{font-weight:500;font-size:.95rem}
.stButton>button{border-radius:7px;border:1px solid var(--ln);background:var(--p2);color:var(--tx)}
.stButton>button:hover{border-color:var(--cy);color:var(--cy)}
.stButton>button[kind="primary"]{background:var(--cy);color:#04141a;border-color:var(--cy);font-weight:600}
.stButton>button[kind="primary"]:hover{color:#04141a;filter:brightness(1.1)}
@media(max-width:700px){.kv{font-size:1.4rem}.hero .t{font-size:1.35rem}}
</style>"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def e(x):
    return html.escape(str(x))


def hero(project, chips):
    logo = ('<svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true"><rect x="1" y="1" width="38" height="38" rx="9" '
            'fill="#111a2b" stroke="#223250"/><path d="M20 7 L31 31 L20 25 L9 31 Z" fill="none" stroke="#3dd6f5" stroke-width="2" '
            'stroke-linejoin="round"/><circle cx="20" cy="19" r="2.2" fill="#3dd6f5"/></svg>')
    cs = "".join(f'<span class="chip"><i class="dot {c[0]}"></i><b>{e(c[1])}</b>{e(c[2])}</span>' for c in chips)
    st.markdown(f'<div class="hero"><div class="l">{logo}<div><div class="t">ProjectPilot AI</div>'
                f'<div class="s">{e(project)}: planning, risk prediction and agent-assisted decisions</div></div></div>'
                f'<div class="chips">{cs}</div></div>', unsafe_allow_html=True)


def pipeline(states):
    names = ["Plan", "Schedule", "Assign", "Predict", "Recommend", "Approve"]
    parts = [f'<div class="pst {s}"><i></i>{n}</div>' for n, s in zip(names, states)]
    st.markdown('<div class="pipe">' + '<div class="pln"></div>'.join(parts) + "</div>", unsafe_allow_html=True)


def kpi(label, value, sub="", tone=""):
    return f'<div class="kpi {tone}"><div class="kl">{e(label)}</div><div class="kv">{e(value)}</div><div class="ks">{e(sub)}</div></div>'


def ring(score, label, tone):
    r, c = 38, 2 * math.pi * 38
    return (f'<div class="kpi ring {tone}"><svg width="96" height="96" viewBox="0 0 96 96" role="img" aria-label="Health {score} of 100">'
            f'<circle cx="48" cy="48" r="{r}" fill="none" stroke="#1b2a44" stroke-width="8"/>'
            f'<circle cx="48" cy="48" r="{r}" fill="none" stroke="{TONE[tone]}" stroke-width="8" stroke-linecap="round" '
            f'stroke-dasharray="{c * score / 100:.1f} {c:.1f}" transform="rotate(-90 48 48)"/>'
            f'<text x="48" y="55" text-anchor="middle" class="rt" fill="#e6edf7">{score}</text></svg>'
            f'<div><div class="kl">Project health</div><div class="kv2">{e(label)}</div><div class="ks">score out of 100</div></div></div>')


def head(title, sub=""):
    st.markdown(f'<div class="ph">{e(title)}</div><div class="pd">{e(sub)}</div>', unsafe_allow_html=True)


def rec_card(r):
    kind = {"reassign": ("Reassign", "#3dd6f5"), "buffer": ("Buffer", "#fbbf24"), "shorten": ("Deadline", "#fb7185"),
            "info": ("Budget", "#8da2c0")}[r["kind"]]
    return (f'<div class="rc"><div class="tx"><span class="tag" style="color:{kind[1]}">{kind[0]}</span>{e(r["text"])}</div>'
            f'<div class="wy">{e(r["why"])}</div></div>')


def terminal(log):
    if not log:
        return '<div class="term"><span class="m">$ awaiting decisions. Approve or reject a recommendation to log it here.</span></div>'
    rows = "".join(f'<div><span class="m">[{i + 1:02d}]</span> <span class="{"ok" if l["approved"] else "no"}">'
                   f'{"APPROVED" if l["approved"] else "REJECTED"}</span>  {e(l["text"])}</div>' for i, l in enumerate(log))
    return f'<div class="term">{rows}</div>'


def cards(items):
    return '<div class="cards">' + "".join(f'<div class="card"><h4>{e(t)}</h4><p>{e(d)}</p></div>' for t, d in items) + "</div>"


def dark(chart):
    return (chart.configure(background="transparent")
            .configure_axis(labelColor="#8da2c0", titleColor="#8da2c0", gridColor="#1b2a44", domainColor="#223250",
                            tickColor="#223250", labelFont="Space Grotesk", titleFont="Space Grotesk")
            .configure_view(strokeWidth=0)
            .configure_legend(labelColor="#8da2c0", titleColor="#8da2c0", labelFont="Space Grotesk"))


LEVELS, LEVEL_COLORS = ["High", "Medium", "Low"], [COL["High"], COL["Medium"], COL["Low"]]
level_scale = alt.Scale(domain=LEVELS, range=LEVEL_COLORS)
