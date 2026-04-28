
Copy

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
 
GITHUB_TOKEN   = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO    = st.secrets["GITHUB_REPO"]
GITHUB_CSV     = "FSC_ICS_Links.csv"
GITHUB_API     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_CSV}"
GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
 
 
def img_to_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
 
 
def _get_csv_from_github():
    r = requests.get(GITHUB_API, headers=GITHUB_HEADERS, timeout=10)
    if r.status_code == 404:
        return ",".join(CSV_HEADERS) + "\n", None
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]
 
 
def append_ics_submission(name, tid, stellantis, marketsource):
    current, sha = _get_csv_from_github()
    new_row = ",".join([
        f'"{name}"',
        f'"{tid}"',
        f'"{stellantis}"',
        f'"{marketsource}"',
    ]) + "\n"
    lines = [l for l in current.splitlines() if l.strip()]
    updated = "\n".join(lines) + "\n" + new_row
    encoded = base64.b64encode(updated.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"ICS submission: {name} ({tid})",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(GITHUB_API, headers=GITHUB_HEADERS, json=payload, timeout=10)
    r.raise_for_status()
 
 
# ── Handle incoming ICS submission via query params from JS postMessage bridge
params = st.query_params
if "ics_name" in params:
    try:
        append_ics_submission(
            params["ics_name"],
            params["ics_tid"],
            params["ics_stellantis"],
            params["ics_marketsource"],
        )
    except Exception as e:
        st.error(f"Failed to save ICS submission: {e}")
    st.query_params.clear()
 
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
 
# Inject postMessage → query_params bridge so iframe submissions reach Streamlit
BRIDGE_JS = """
<script>
window.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'ics_submission') {
    var p = e.data.payload;
    var url = new URL(window.location.href);
    url.searchParams.set('ics_name',         p.name);
    url.searchParams.set('ics_tid',          p.tid);
    url.searchParams.set('ics_stellantis',   p.stellantis);
    url.searchParams.set('ics_marketsource', p.marketsource);
    window.location.href = url.toString();
  }
});
</script>
"""
html = html.replace("</body>", BRIDGE_JS + "\n</body>")
 
components.html(html, height=2200, scrolling=True)
