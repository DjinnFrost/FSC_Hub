from pathlib import Path
import base64
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="FSC Operations Hub", layout="wide")

BASE_DIR = Path(__file__).parent

def img_to_data_uri(path: Path) -> str:
    mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

html = (BASE_DIR / "FSC_Hub.html").read_text(encoding="utf-8")

html = html.replace('src="Stel_PI.png"', f'src="{img_to_data_uri(BASE_DIR / "Stel_PI.png")}"')
html = html.replace('src="csms.png"', f'src="{img_to_data_uri(BASE_DIR / "csms.png")}"')
html = html.replace('src="UKG.png"',     f'src="{img_to_data_uri(BASE_DIR / "UKG.png")}"')

components.html(html, height=2200, scrolling=True)
