"""Dark modern CSS theme for the AML Monitoring Agent dashboard."""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:        #0A101C;
  --panel:     #111A2B;
  --panel-2:   #16223A;
  --line:      #223049;
  --text:      #E6EDF7;
  --muted:     #8A9AB4;
  --accent:    #4C8DFF;
  --low:       #2FBF71;
  --medium:    #E8B931;
  --high:      #FF7A45;
  --critical:  #FF3B5C;
}

.stApp { background: var(--bg); color: var(--text); }
html, body, [class*="css"] { font-family: 'IBM Plex Sans', system-ui, -apple-system, sans-serif; }

section[data-testid="stSidebar"] {
  background: #080D17;
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] * { color: var(--text); }

h1, h2, h3, h4 { font-family: 'IBM Plex Sans', sans-serif; letter-spacing: -0.01em; color: var(--text); }

.aml-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.aml-title { font-size: 2.1rem; font-weight: 700; margin: 0 0 0.3rem 0; color: #FFFFFF; }
.aml-sub { color: var(--muted); font-size: 0.96rem; margin-bottom: 1.4rem; line-height: 1.5; }

.aml-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1.2rem 1.3rem;
  margin-bottom: 0.9rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

.aml-metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 0.95rem 1.1rem;
  height: 100%;
  transition: transform 0.2s ease, border-color 0.2s ease;
}
.aml-metric:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
.aml-metric .label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.70rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.aml-metric .value {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1.75rem;
  font-weight: 700;
  margin-top: 0.3rem;
  color: #FFFFFF;
}
.aml-metric .note { font-size: 0.78rem; color: var(--muted); margin-top: 0.25rem; }

.aml-badge {
  display: inline-block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  border: 1px solid currentColor;
  margin-right: 0.4rem;
  font-weight: 600;
}
.badge-low      { color: var(--low);      background: rgba(47,191,113,0.12); }
.badge-medium   { color: var(--medium);   background: rgba(232,185,49,0.12); }
.badge-high     { color: var(--high);     background: rgba(255,122,69,0.12); }
.badge-critical { color: var(--critical); background: rgba(255,59,92,0.12); }
.badge-neutral  { color: var(--muted);    background: rgba(138,154,180,0.12); }
.badge-accent   { color: var(--accent);   background: rgba(76,141,255,0.12); }

.aml-evidence {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1.0rem 1.2rem;
  margin-bottom: 0.85rem;
}
.aml-evidence .head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.55rem;
  flex-wrap: wrap;
}
.aml-evidence .rank {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--accent);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.12rem 0.5rem;
  background: var(--panel-2);
}
.aml-evidence .excerpt {
  font-size: 0.92rem;
  line-height: 1.6;
  color: #C7D3E6;
  border-left: 3px solid var(--line);
  padding-left: 0.9rem;
  margin-top: 0.4rem;
  white-space: pre-wrap;
}
.sim-track {
  height: 5px;
  background: var(--line);
  border-radius: 999px;
  margin: 0.6rem 0 0.2rem 0;
  overflow: hidden;
}
.sim-fill { height: 5px; background: linear-gradient(90deg, #4C8DFF, #2FBF71); border-radius: 999px; }
.sim-note { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); }

.aml-gauge-wrap {
  display: flex;
  align-items: center;
  gap: 1.6rem;
  flex-wrap: wrap;
  background: var(--panel);
  border: 1px solid var(--line);
  padding: 1.2rem;
  border-radius: 12px;
}
.aml-gauge {
  width: 150px; height: 150px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  box-shadow: 0 0 15px rgba(0,0,0,0.4);
}
.aml-gauge::after {
  content: ""; position: absolute;
  width: 114px; height: 114px; border-radius: 50%;
  background: var(--panel);
}
.aml-gauge .inner { position: relative; z-index: 1; text-align: center; }
.aml-gauge .score {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 2.3rem; font-weight: 700; line-height: 1;
}
.aml-gauge .of { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); margin-top: 0.15rem; }

.aml-report {
  background: #0D1524;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 1.3rem 1.4rem;
  font-size: 0.95rem;
  line-height: 1.65;
  white-space: pre-wrap;
  font-family: 'IBM Plex Sans', sans-serif;
  color: #DDE6F5;
}

.aml-reason {
  font-size: 0.92rem;
  color: #C7D3E6;
  padding: 0.55rem 0.85rem;
  border-left: 3px solid var(--high);
  background: rgba(255,122,69,0.08);
  margin-bottom: 0.4rem;
  border-radius: 0 6px 6px 0;
}

.stButton > button {
  background: var(--accent);
  color: #061020;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  padding: 0.55rem 1.2rem;
  transition: all 0.2s ease;
}
.stButton > button:hover { background: #6BA1FF; color: #061020; transform: translateY(-1px); }

.stDownloadButton > button {
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 8px;
  font-weight: 600;
  padding: 0.5rem 1.1rem;
}
.stDownloadButton > button:hover {
  background: rgba(76,141,255,0.15);
}

.stTextInput input, .stTextArea textarea, .stNumberInput input {
  background: var(--panel-2) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
}
div[data-baseweb="select"] > div {
  background: var(--panel-2) !important;
  border-color: var(--line) !important;
  border-radius: 8px !important;
}

hr.aml-rule { border: none; border-top: 1px solid var(--line); margin: 1.5rem 0; }
</style>
"""

def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
