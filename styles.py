"""Estilos visuales del dashboard; no intervienen en el scraping."""
import streamlit as st

def apply_styles():
    """Carga los estilos CSS del dashboard profesional."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"] {font-family: 'Inter', sans-serif;}
[data-testid="stAppViewContainer"] {background: #0B111B; color: #E9EDF5;}
[data-testid="stSidebar"] {background: #101A29; border-right: 1px solid #243247;}
.block-container {max-width: 1500px; padding-top: 1.7rem; padding-bottom: 3rem;}
h1, h2, h3 {letter-spacing: -0.035em;}
h1 {font-size: 2.1rem !important; font-weight: 800 !important;}
h3 {font-size: 1.2rem !important;}
[data-testid="stMetric"] {background: #172232; border: 1px solid #2B3A4D; border-radius: 15px; padding: 18px 20px;}
[data-testid="stMetricLabel"] {color: #9BAFC5;}
[data-testid="stMetricValue"] {color: #F5F8FC; font-size: 1.65rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: #29384B !important; border-radius: 15px !important;}
[data-testid="stForm"] {background: #131F2E; border: 1px solid #2B3A4D; border-radius: 15px; padding: 12px 16px;}
[data-testid="stTabs"] button {font-weight: 600;}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {background: #F02E62; border-color: #F02E62; border-radius: 10px; font-weight: 700;}
.stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button:hover {background: #D71C4E; border-color: #D71C4E;}
.stTextInput input {border-radius: 10px;}
.hero {background: linear-gradient(110deg,#17243A 0%,#1C1B34 58%,#2A1934 100%); border:1px solid #31405B; border-radius:20px; padding:24px 28px; margin-bottom:20px;}
.hero-title {font-size:1.9rem; font-weight:800; color:#FFFFFF; margin:0 0 6px;}
.hero-sub {color:#ACBBD0; font-size:.94rem; margin:0;}
.pill {display:inline-block; padding:5px 11px; border-radius:99px; background:#1C4A41; color:#69E3BE; font-size:.76rem; font-weight:700; margin-top:10px;}
.section-h {font-size:1.12rem; font-weight:750; color:#EAF0F8; margin:12px 0;}
.comment-author {font-weight:750; color:#F3F7FC; font-size:.94rem;}
.comment-num {display:inline-block; color:#F46A90; font-weight:750; margin-right:8px;}
.comment-body {color:#D3DFEC; margin-top:7px; font-size:.93rem; white-space:pre-wrap; overflow-wrap:anywhere;}
.empty-panel {border:1px dashed #344760; background:#111B2A; border-radius:16px; padding:30px 20px; text-align:center; color:#A6B8CC;}
.caption-soft {color:#90A5BD; font-size:.85rem;}
@media (max-width: 768px) {.block-container {padding:1rem .7rem;} .hero {padding:18px;} .hero-title {font-size:1.5rem;}}
</style>
""", unsafe_allow_html=True)
