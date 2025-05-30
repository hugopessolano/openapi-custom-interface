import streamlit as st
from app_config import GLOBAL_SUFFIX

def render_auth_dialog():
    if not st.session_state.get('show_auth_dialog', False):
        return

    with st.container():
        st.markdown("---")
        st.subheader("🔑 Configurar Autorización API")
        
        security_schemes = st.session_state.get('auth_dialog_security_schemes', {})
        
        if not security_schemes:
            st.warning("No se encontraron esquemas de seguridad (securitySchemes) en la especificación de la API.")
            if st.button("Cerrar", key=f"auth_dialog_close_no_schemes_btn{GLOBAL_SUFFIX}"):
                st.session_state.show_auth_dialog = False
                st.session_state.auth_input_values = {}
                st.rerun()
            return

        for scheme_name in security_schemes.keys():
            if scheme_name not in st.session_state.auth_input_values:
                st.session_state.auth_input_values[scheme_name] = {"value": ""}

        for scheme_name, scheme_details in security_schemes.items():
            st.markdown(f"**Esquema: `{scheme_name}`** (Tipo: `{scheme_details.get('type')}`)")

            current_input_value = st.session_state.auth_input_values.get(scheme_name, {}).get("value", "")
            user_input = ""

            if scheme_details.get('type') == 'apiKey':
                param_location = scheme_details.get('in', 'Desconocido')
                param_name = scheme_details.get('name', 'Desconocido')
                field_label = f"Valor para API Key `{scheme_name}` (en: {param_location}, nombre: {param_name}):"
                user_input = st.text_input(
                    field_label, 
                    value=current_input_value, 
                    key=f"auth_input_{scheme_name}{GLOBAL_SUFFIX}",
                    type="password",
                    help=scheme_details.get('description', f'Ingrese el valor para la API Key: {param_name}')
                )
            
            elif scheme_details.get('type') == 'http':
                auth_scheme_type = scheme_details.get('scheme', 'Desconocido').lower()
                if auth_scheme_type == 'bearer':
                    field_label = f"Token Bearer para `{scheme_name}`:"
                    user_input = st.text_input(
                        field_label,
                        value=current_input_value,
                        key=f"auth_input_{scheme_name}{GLOBAL_SUFFIX}",
                        type="password",
                        help=scheme_details.get('description', 'Ingrese su token Bearer.')
                    )
                else:
                    st.caption(f"El esquema HTTP '{auth_scheme_type}' no es directamente soportado para entrada manual en esta versión. Considere el flujo OAuth2 si aplica.")
            
            elif scheme_details.get('type') == 'oauth2':
                field_label = f"Token de Acceso (OAuth2) para `{scheme_name}`:"
                st.caption(f"Flujos OAuth2: {', '.join(scheme_details.get('flows', {}).keys())}. Por ahora, ingrese un token de acceso si ya lo posee.")
                user_input = st.text_input(
                    field_label,
                    value=current_input_value,
                    key=f"auth_input_{scheme_name}{GLOBAL_SUFFIX}",
                    type="password",
                    help=scheme_details.get('description', 'Ingrese su token de acceso OAuth2 si ya lo tiene.')
                )

            elif scheme_details.get('type') == 'openIdConnect':
                st.caption(f"El esquema OpenID Connect no es directamente soportado para entrada manual en esta versión.")

            else:
                st.caption(f"Tipo de esquema de seguridad desconocido o no soportado para entrada manual: {scheme_details.get('type')}")

            if user_input != current_input_value :
                 st.session_state.auth_input_values[scheme_name]["value"] = user_input
            st.markdown("---")


        col_apply, col_cancel = st.columns(2)
        with col_apply:
            if st.button("Aplicar Autorización", key=f"auth_dialog_apply_btn{GLOBAL_SUFFIX}", type="primary"):
                st.session_state.active_security_credentials = {}
                applied_any = False
                for scheme_name, scheme_details_apply in security_schemes.items():
                    input_val_obj = st.session_state.auth_input_values.get(scheme_name, {})
                    token_value = input_val_obj.get("value", "").strip()

                    if token_value:
                        st.session_state.active_security_credentials[scheme_name] = {
                            "type": scheme_details_apply.get("type"),
                            "value": token_value,
                            "in": scheme_details_apply.get("in"), 
                            "name": scheme_details_apply.get("name"),
                            "scheme": scheme_details_apply.get("scheme")
                        }
                        applied_any = True
                
                if applied_any:
                    st.session_state.auth_status_message = "Autorización aplicada/actualizada."
                else:
                    st.session_state.auth_status_message = "No se ingresaron valores para autorización."
                
                st.session_state.show_auth_dialog = False
                st.rerun()

        with col_cancel:
            if st.button("Cancelar", key=f"auth_dialog_cancel_btn{GLOBAL_SUFFIX}"):
                st.session_state.show_auth_dialog = False
                st.rerun()

def trigger_auth_dialog():
    st.session_state.show_auth_dialog = True
    st.session_state.auth_status_message = None 
    st.rerun()