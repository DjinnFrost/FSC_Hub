from pathlib import Path
import base64
import json
import re
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
 
st.set_page_config(page_title="FSC Operations Hub", layout="wide")
 
BASE_DIR = Path(__file__).parent
 
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO  = st.secrets["GITHUB_REPO"]
GITHUB_CSV   = "FSC_ICS_Links.csv"
GITHUB_API   = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_CSV}"
CSV_HEADER_ROW = "FSC Name,TID,Stellantis ICS Link,MarketSource ICS Link"
 
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
 
 
def img_to_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
 
 
# ── Load and patch HTML
html = (BASE_DIR / "FSC_Hub.html").read_text(encoding="utf-8")
 
# Inject live metrics
metrics_json = json.dumps(json.loads((BASE_DIR / "fsc_metrics.json").read_text(encoding="utf-8")))
html = re.sub(
    r'const FSC_METRICS = \{.*?\};',
    f'const FSC_METRICS = {metrics_json};',
    html, count=1, flags=re.DOTALL
)
 
# Inject images as base64 data URIs
html = html.replace('src="Stel_PI.png"',              f'src="{img_to_data_uri(BASE_DIR / "Stel_PI.png")}"')
html = html.replace('src="csms.png"',                 f'src="{img_to_data_uri(BASE_DIR / "csms.png")}"')
html = html.replace('src="UKG.png"',                  f'src="{img_to_data_uri(BASE_DIR / "UKG.png")}"')
html = html.replace('src="MarketSource.png"',         f'src="{img_to_data_uri(BASE_DIR / "MarketSource.png")}"')
html = html.replace('src="Marketsource_Insider.png"', f'src="{img_to_data_uri(BASE_DIR / "Marketsource_Insider.png")}"')
 
# Inject Supabase config for FSC Connect JS
supabase_js = (
    '<script>\n'
    'var SUPABASE_URL = "' + st.secrets["SUPABASE_URL"] + '";\n'
    'var SUPABASE_ANON_KEY = "' + st.secrets["SUPABASE_KEY"] + '";\n'
    '</script>\n'
)
html = html.replace("</head>", supabase_js + "</head>", 1)
 
# Build the GitHub direct-write JS (unchanged from original)
github_js = (
    '<script>\n'
    'var _GH_TOKEN = "' + GITHUB_TOKEN + '";\n'
    'var _GH_API   = "' + GITHUB_API + '";\n'
    'var _CSV_HEADER = "' + CSV_HEADER_ROW + '";\n'
    '\n'
    'async function submitICSToGitHub(name, tid, stellantis, marketsource) {\n'
    '  var getRes = await fetch(_GH_API, {\n'
    '    headers: {\n'
    '      "Authorization": "Bearer " + _GH_TOKEN,\n'
    '      "Accept": "application/vnd.github+json"\n'
    '    }\n'
    '  });\n'
    '  var sha = null;\n'
    '  var existingContent = _CSV_HEADER + "\\n";\n'
    '  if (getRes.ok) {\n'
    '    var data = await getRes.json();\n'
    '    sha = data.sha;\n'
    '    existingContent = atob(data.content.replace(/\\n/g, ""));\n'
    '  }\n'
    '  var lines = existingContent.split("\\n").filter(function(l) { return l.trim() !== ""; });\n'
    '  if (lines.length === 0 || lines[0] !== _CSV_HEADER) {\n'
    '    lines.unshift(_CSV_HEADER);\n'
    '  }\n'
    '  var newRow = \'"\' + name + \'","\' + tid + \'","\' + stellantis + \'","\' + marketsource + \'"\';\n'
    '  lines.push(newRow);\n'
    '  var updated = lines.join("\\n") + "\\n";\n'
    '  var encoded = btoa(unescape(encodeURIComponent(updated)));\n'
    '  var payload = {\n'
    '    message: "ICS submission: " + name + " (" + tid + ")",\n'
    '    content: encoded\n'
    '  };\n'
    '  if (sha) payload.sha = sha;\n'
    '  var putRes = await fetch(_GH_API, {\n'
    '    method: "PUT",\n'
    '    headers: {\n'
    '      "Authorization": "Bearer " + _GH_TOKEN,\n'
    '      "Accept": "application/vnd.github+json",\n'
    '      "Content-Type": "application/json"\n'
    '    },\n'
    '    body: JSON.stringify(payload)\n'
    '  });\n'
    '  if (!putRes.ok) {\n'
    '    var err = await putRes.json();\n'
    '    throw new Error(err.message || "GitHub PUT failed");\n'
    '  }\n'
    '}\n'
    '</script>\n'
)
html = html.replace("</head>", github_js + "</head>")
 
# Patch submitICS() to call submitICSToGitHub instead of postMessage
OLD_SUBMIT = (
    "    window.parent.postMessage({ type: 'ics_submission', payload: { name: name, tid: tid, stellantis: stel, marketsource: ms } }, '*');\n"
    "    document.getElementById('ics-success').style.display = 'block';\n"
    "    document.getElementById('ics-stellantis').value = '';\n"
    "    document.getElementById('ics-marketsource').value = '';"
)
NEW_SUBMIT = (
    "    submitICSToGitHub(name, tid, stel, ms)\n"
    "      .then(function() {\n"
    "        document.getElementById('ics-success').style.display = 'block';\n"
    "        document.getElementById('ics-stellantis').value = '';\n"
    "        document.getElementById('ics-marketsource').value = '';\n"
    "      })\n"
    "      .catch(function(err) {\n"
    "        errEl.textContent = 'Submission failed: ' + err.message;\n"
    "        errEl.style.display = 'block';\n"
    "      });"
)
html = html.replace(OLD_SUBMIT, NEW_SUBMIT)
 
components.html(html, height=2200, scrolling=True)
