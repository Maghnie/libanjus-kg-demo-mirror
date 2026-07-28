import streamlit as st

def render_503_error() -> None:
    st.image('static/placeholder_503.png')
    st.info(f"""
    🔃 Contact the page owner to get things started again.
    In the meantime, check out the [About page](about) for more info and a demo video.
    """)
    st.stop()