import streamlit as st

st.set_page_config(page_title="JOYA Enterprise 4.0", layout="wide")

st.title("🏆 JOYA Enterprise 4.0")
st.info("Sprint 1 - Foundation")

st.success("Proyecto base creado correctamente.")

st.subheader("Estado")
st.write("- API: Pendiente")
st.write("- Scanner: Pendiente")
st.write("- Cache: Pendiente")

st.button("🔌 Probar conexión", disabled=True)
st.button("🔍 Escanear partidos", disabled=True)
