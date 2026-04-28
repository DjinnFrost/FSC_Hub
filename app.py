from pathlib import Path
import base64
import json
import re
import requests
import streamlit as st
import streamlit.components.v1 as components
 
st.set_page_config(page_title="FSC Operations Hub", layout="wide")
 
BASE_DIR = Path(__file__).parent
CSV_HEADERS = ["FSC Name", "TID", "Stellantis ICS Link", "MarketSource ICS Link"]
 
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO  = st.secrets["GITHUB_REPO"]
GITHUB_CSV   = "FSC_ICS_Links.csv"
GITHUB_API   = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_CSV}"
GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
 
 
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
 
# Inject GitHub credentials so the browser can write directly to the CSV
GITHUB_JS = f"""
<script>
var _GH_TOKEN = "{GITHUB_TOKEN}";
var _GH_API   = "{GITHUB_API}";
 
async function submitICSToGitHub(name, tid, stellantis, marketsource) {{
  // 1. Fetch current CSV + SHA
  var getRes = await fetch(_GH_API, {{
    headers: {{
      "Authorization": "Bearer " + _GH_TOKEN,
      "Accept": "application/vnd.github+json"
    }}
  }});
 
  var sha = null;
  var existingContent = "{','.join(CSV_HEADERS)}\\n";
 
  if (getRes.ok) {{
    var data = await getRes.json();
    sha = data.sha;
    existingContent = atob(data.content.replace(/\\n/g, ""));
  }}
 
  // 2. Strip blank lines, append new row
  var lines = existingContent.split("\\n").filter(function(l) {{ return l.trim() !== ""; }});
  var newRow = '"' + name + '","' + tid + '","' + stellantis + '","' + marketsource + '"';
  lines.push(newRow);
  var updated = lines.join("\\n") + "\\n";
 
  // 3. Base64 encode and PUT back
  var encoded = btoa(unescape(encodeURIComponent(updated)));
  var payload = {{
    message: "ICS submission: " + name + " (" + tid + ")",
    content: encoded
  }};
  if (sha) payload.sha = sha;
 
  var putRes = await fetch(_GH_API, {{
    method: "PUT",
    headers: {{
      "Authorization": "Bearer " + _GH_TOKEN,
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json"
    }},
    body: JSON.stringify(payload)
  }});
 
  if (!putRes.ok) {{
    var err = await putRes.json();
    throw new Error(err.message || "GitHub PUT failed");
  }}
}}
</script>
"""
html = html.replace("</head>", GITHUB_JS + "\n</head>")
 
# Patch submitICS() in the HTML to call submitICSToGitHub instead of postMessage
OLD_SUBMIT = """    window.parent.postMessage({ type: 'ics_submission', payload: { name: name, tid: tid, stellantis: stel, marketsource: ms } }, '*');
    document.getElementById('ics-success').style.display = 'block';
    document.getElementById('ics-stellantis').value = '';
    document.getElementById('ics-marketsource').value = '';"""
 
NEW_SUBMIT = """    submitICSToGitHub(name, tid, stel, ms)
      .then(function() {
        document.getElementById('ics-success').style.display = 'block';
        document.getElementById('ics-stellantis').value = '';
        document.getElementById('ics-marketsource').value = '';
      })
      .catch(function(err) {
        errEl.textContent = 'Submission failed: ' + err.message;
        errEl.style.display = 'block';
      });"""
 
html = html.replace(OLD_SUBMIT, NEW_SUBMIT)
 
components.html(html, height=2200, scrolling=True)
 
