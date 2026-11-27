"""Kaarkhana UI.  Local:  streamlit run app.py   (everything stays on this machine)"""
import tempfile
from pathlib import Path
import streamlit as st
from kaarkhana import pipeline as P, detect as D
from kaarkhana.config import LineConfig

st.set_page_config(page_title="Kaarkhana", layout="wide")
st.title("Kaarkhana - the industrial engineer in your pocket")
st.caption("Analyses run on this device. Video is never uploaded anywhere.")

with st.sidebar:
    line_file = st.selectbox("Line config", sorted(str(p) for p in Path("assets").glob("*_line.json")))
    cfg = LineConfig.load(line_file)
    st.subheader("Costing (edit)")
    c = cfg.costing
    c.wage_bdt_per_hr = st.number_input("Operator cost BDT/hour", value=c.wage_bdt_per_hr)
    c.cm_usd_per_piece = st.number_input("Cut-and-make USD/garment", value=c.cm_usd_per_piece)
    c.realisation = st.slider("Share of gain realised", 0.2, 1.0, c.realisation)
    feed = st.number_input("Cutting-table feed (garments/hour, 0 = unknown)", value=0.0)
    det_kind = st.radio("Bundle detector", ["classical", "sam3"], help="sam3 needs a GPU + Hugging Face access")
    manual = st.checkbox("Station plates not found? enter first/last station pixels")
    anchors = None
    if manual:
        x1, y1, x2, y2 = (st.number_input(k, value=0.0) for k in ("x first", "y first", "x last", "y last"))
        anchors = ((x1, y1), (x2, y2))

up = st.file_uploader("Line video", type=["mp4", "mov", "avi"])
if up and st.button("Analyse line", type="primary"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(up.read()); vpath = f.name
    bar = st.progress(0.0, "Watching the bundles...")
    try:
        res = P.analyse(vpath, cfg, D.make_detector(det_kind), anchors, progress=lambda x: bar.progress(x),
                        feed_rate_hr=feed or None)
    except RuntimeError as e:
        st.error(str(e)); st.stop()
    bar.empty()
    out = P.save_outputs(res, tempfile.mkdtemp())
    s = res["story"]
    st.markdown(f"**{s['headline']}**"); st.success(s["prescription"])
    c1, c2 = st.columns(2)
    c1.subheader("Station metrics"); c1.dataframe(res["table"].round(2), use_container_width=True)
    c2.subheader("SMV reconciliation"); c2.dataframe(res["recon"].round(2), use_container_width=True)
    for lbl, ok, det in res["constraint"].evidence:
        st.write(f"{'✅' if ok else '⚠️'} **{lbl}** - {det}")
    def _read(path):
        with open(path, "rb") as fh:
            return fh.read()

    st.download_button("Download signable report (PDF)", _read(out["pdf"]), "kaarkhana_report.pdf")
    st.download_button("Download results (JSON)", _read(out["json"]), "results.json")
