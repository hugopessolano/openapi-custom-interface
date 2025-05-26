import streamlit as st
from app_config import GLOBAL_SUFFIX
from api_service import load_api_spec

def render_sidebar():

    with st.sidebar:
        st.header(f"🔑 Autenticación")
        if st.session_state.get('auth_token'):
            st.success(f"Autenticado! Token: ...{st.session_state.auth_token[-6:]}")
            if st.session_state.get('user_info') and "username" in st.session_state.user_info:
                st.caption(f"Usuario: {st.session_state.user_info['username']}")
            if st.button("Cerrar Sesión", key=f"logout_btn{GLOBAL_SUFFIX}"):
                st.session_state.auth_token = None
                st.session_state.auth_error = None
                st.session_state.user_info = {}
                st.session_state.show_detail_dialog = False
                st.session_state.active_expander_id = None
                st.rerun()
        else:
            st.info("No autenticado.")
            if st.session_state.get('auth_error'):
                st.error(st.session_state.auth_error)

        st.divider()
        st.header("⚙️ Configuración API")

        current_url_input = st.session_state.get("current_api_url", "http://hugopessolano.duckdns.org:8000")
        api_base_url_input = st.text_input(
            "URL Base de la API:",
            value=current_url_input,
            key=f"api_url_input{GLOBAL_SUFFIX}"
        )
        api_json_location_input = st.text_input(
            "Ubicación del openapi.json:",
            value="openapi.json",
            key=f"api_json_location_input{GLOBAL_SUFFIX}"
        )

        if st.button("Cargar API", key=f"load_api_btn{GLOBAL_SUFFIX}"):
            load_api_spec(api_base_url_input, api_json_location_input)
            st.rerun()  

        if st.session_state.get('openapi_spec'):
            spec = st.session_state.openapi_spec
            st.divider()
            st.subheader(f"API: {spec.get('info',{}).get('title','N/A')}")
            st.caption(f"Versión: {spec.get('info',{}).get('version','N/A')}")
            if spec.get('info',{}).get('description'):
                st.markdown(spec.get('info',{}).get('description'))
        elif st.session_state.get('error_message') and not st.session_state.get('grouped_endpoints'):
             pass
        