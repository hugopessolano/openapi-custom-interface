import streamlit as st
from app_config import GLOBAL_SUFFIX
from api_service import load_api_spec
from api_service import reset_api_spec

def render_sidebar():

    with st.sidebar:
        st.header(f"🔑 Autenticación")

        if st.session_state.get('active_security_credentials') and \
           any(st.session_state.active_security_credentials.get(scheme, {}).get("value") for scheme in st.session_state.active_security_credentials):
            
            active_schemes_with_values = [
                f"{scheme_name} (...{creds.get('value', '')[-6:]})" 
                for scheme_name, creds in st.session_state.active_security_credentials.items() 
                if creds.get("value")
            ]
            if active_schemes_with_values:
                st.success(f"Autenticado con: {', '.join(active_schemes_with_values)}")
            else:
                st.info("No hay credenciales activas con valor.")


            if st.session_state.get('user_info') and "username" in st.session_state.user_info:
                st.caption(f"Usuario: {st.session_state.user_info['username']}")
            
            if st.button("Limpiar Autorización", key=f"clear_auth_btn{GLOBAL_SUFFIX}"):
                st.session_state.active_security_credentials = {}
                st.session_state.auth_input_values = {}
                st.session_state.auth_status_message = "Autorización limpiada."
                st.session_state.user_info = {}
                st.rerun()
        else:
            st.info("No autenticado.")
            if st.session_state.get('auth_status_message'):
                if "error" in st.session_state.auth_status_message.lower() or \
                   "fallo" in st.session_state.auth_status_message.lower() or \
                   "failed" in st.session_state.auth_status_message.lower():
                    st.error(st.session_state.auth_status_message)
                else:
                    st.info(st.session_state.auth_status_message)
        
        if st.button("⚙️ Configurar Autorización", key=f"auth_dialog_btn{GLOBAL_SUFFIX}"):
            if st.session_state.get('openapi_spec') and \
               st.session_state.openapi_spec.get("components", {}).get("securitySchemes"):
                st.session_state.auth_dialog_security_schemes = st.session_state.openapi_spec["components"]["securitySchemes"]
                st.session_state.show_auth_dialog = True
                st.session_state.auth_status_message = None 
                st.rerun()
            elif not st.session_state.get('openapi_spec'):
                st.warning("Carga una especificación API primero para configurar la autorización.")
            else:
                st.info("La API cargada no define esquemas de seguridad (securitySchemes).")


        st.divider()
        st.header("⚙️ Configuración API")

        current_url_input = st.session_state.get("current_api_url", "http://hugopessolano.duckdns.org:8000")
        api_base_url_input = st.text_input(
            "URL Base de la API:",
            value=current_url_input,
            key=f"api_url_input{GLOBAL_SUFFIX}"
        )
        
        current_json_loc = st.session_state.get("api_json_location", "openapi.json")
        api_json_location_input = st.text_input(
            "Ubicación del openapi.json:",
            value=current_json_loc,
            key=f"api_json_location_input{GLOBAL_SUFFIX}"
        )

        if st.button("Cargar API", key=f"load_api_btn{GLOBAL_SUFFIX}"):
            st.session_state.current_api_url = api_base_url_input
            st.session_state.api_json_location = api_json_location_input
            load_api_spec(api_base_url_input, api_json_location_input)
            st.rerun()  

        if st.session_state.get('openapi_spec'):
            spec = st.session_state.openapi_spec
            st.divider()
            st.subheader(f"API: {spec.get('info',{}).get('title','N/A')}")
            st.caption(f"Versión: {spec.get('info',{}).get('version','N/A')}")
            if spec.get('info',{}).get('description'):
                st.markdown(spec.get('info',{}).get('description'))
            
            security_schemes = spec.get("components", {}).get("securitySchemes")
            if security_schemes:
                st.markdown("**Esquemas de Seguridad Definidos:**")
                for name, details in security_schemes.items():
                    st.caption(f"- `{name}` (Tipo: {details.get('type')}, En: {details.get('in', 'N/A')}, Nombre: {details.get('name', 'N/A')})")
            else:
                st.caption("No hay esquemas de seguridad definidos en 'components.securitySchemes'.")

        elif st.session_state.get('error_message') and not st.session_state.get('grouped_endpoints'):
             pass
