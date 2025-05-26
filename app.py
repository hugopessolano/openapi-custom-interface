import streamlit as st
import json
from app_config import GLOBAL_SUFFIX, PANDAS_AVAILABLE
from state_manager import initialize_session_state
from utils import resolve_ref
from api_service import execute_api_request
from ui_components.sidebar import render_sidebar
from ui_components.form_generator import generate_form_fields
from ui_components.response_display import render_response_data
from ui_components.detail_dialog import render_detail_dialog

initialize_session_state()

st.set_page_config(page_title=f"API Client", layout="wide")
st.title(f"Cliente API Interactivo")

render_sidebar()
render_detail_dialog()

if st.session_state.get('error_message'):
    st.error(st.session_state.error_message)

if st.session_state.get('grouped_endpoints') and st.session_state.get('current_api_url'):
    api_base_url = st.session_state.current_api_url
    spec = st.session_state.openapi_spec
    grouped_endpoints = st.session_state.grouped_endpoints
    tag_descriptions = st.session_state.get('tag_descriptions', {})

    sorted_tags = sorted(grouped_endpoints.keys(), key=lambda t: (t == "default", t.lower()))

    if not sorted_tags:
        st.warning("No se encontraron tags o endpoints en la especificación API.")
    else:
        active_tab_index = 0
        if st.session_state.get('active_tab_name') and st.session_state.active_tab_name in sorted_tags:
            try:
                active_tab_index = sorted_tags.index(st.session_state.active_tab_name)
            except ValueError:
                active_tab_index = 0
                st.session_state.active_tab_name = sorted_tags[0] if sorted_tags else None
        elif sorted_tags:
             st.session_state.active_tab_name = sorted_tags[0]
             active_tab_index = 0

        selected_tag_name = st.radio(
            "Grupo de Endpoints:",
            options=sorted_tags,
            format_func=lambda x: x.replace("_", " ").capitalize(),
            index=active_tab_index,
            key=f"tab_selection_radio{GLOBAL_SUFFIX}",
            horizontal=True
        )

        if selected_tag_name != st.session_state.active_tab_name:
            st.session_state.active_tab_name = selected_tag_name
            st.session_state.active_expander_id = None
            st.rerun()

        tag_name_to_display = st.session_state.active_tab_name

        if tag_name_to_display and tag_name_to_display in grouped_endpoints:
            st.header(f"{tag_name_to_display.replace('_', ' ').capitalize()}")
            if tag_name_to_display in tag_descriptions and tag_descriptions[tag_name_to_display].get("description"):
                st.caption(tag_descriptions[tag_name_to_display]["description"])

            for endpoint_info in grouped_endpoints[tag_name_to_display]:
                path = endpoint_info["path"]
                method = endpoint_info["method"]
                operation = endpoint_info["operation"]
                endpoint_id = endpoint_info["id"]

                expander_title = f"**{method.upper()}** `{path}`"
                if operation.get('summary'):
                    expander_title += f"  —  {operation.get('summary')}"

                should_expand = (st.session_state.active_expander_id == endpoint_id)

                with st.expander(expander_title, expanded=should_expand):
                    if not should_expand and st.session_state.get('_last_expander_toggle_true', False):
                         st.session_state.active_expander_id = endpoint_id

                    if operation.get('description'):
                        st.markdown(f"_{operation.get('description')}_")

                    if endpoint_id not in st.session_state.form_field_values:
                        st.session_state.form_field_values[endpoint_id] = {}
                    if endpoint_id not in st.session_state.form_field_includes:
                        st.session_state.form_field_includes[endpoint_id] = {}
                    
                    col_params, col_body = st.columns(2)

                    with col_params:
                        st.markdown("**Parámetros de URL:**")
                        url_params_exist = False
                        if "parameters" in operation:
                            for p_idx, param_schema in enumerate(operation["parameters"]):
                                param_base_key = f"{endpoint_id}_p_{p_idx}_{param_schema['name']}{GLOBAL_SUFFIX}"
                                req_symbol = "*" if param_schema.get("required") else ""
                                param_label = f"`{param_schema['name']}` ({param_schema.get('schema',{}).get('type','string')}){req_symbol}"
                                param_help = param_schema.get('description','')

                                if param_schema['in'] == 'path':
                                    st.text_input(f"Path: {param_label}", key=f"{param_base_key}_path", help=param_help)
                                    url_params_exist = True
                                elif param_schema['in'] == 'query':
                                    st.text_input(f"Query: {param_label}", key=f"{param_base_key}_query", help=param_help)
                                    url_params_exist = True
                        if not url_params_exist:
                            st.caption("Este endpoint no tiene parámetros de URL (path o query).")

                    with col_body:
                        st.markdown("**Cuerpo del Request (Body):**")
                        if "requestBody" in operation:
                            rb_spec = operation["requestBody"]
                            content_spec = rb_spec.get("content", {})

                            if "application/json" in content_spec:
                                schema_ref = content_spec["application/json"].get("schema", {}).get("$ref")
                                request_body_actual_schema = resolve_ref(spec, schema_ref) if schema_ref \
                                                             else content_spec["application/json"].get("schema")

                                body_method_key = f"{endpoint_id}_body_method{GLOBAL_SUFFIX}"
                                body_method_options = ["JSON Crudo"]
                                if request_body_actual_schema :
                                    body_method_options.insert(0, "Campos Dinámicos")

                                default_radio_idx = 0
                                current_body_method_choice = st.session_state.get(body_method_key, body_method_options[0])
                                if current_body_method_choice in body_method_options:
                                    default_radio_idx = body_method_options.index(current_body_method_choice)
                                else:
                                    default_radio_idx = 0

                                chosen_body_method = st.radio(
                                    "Método de entrada para el Body JSON:",
                                    options=body_method_options,
                                    index=default_radio_idx,
                                    horizontal=True,
                                    key=body_method_key
                                )

                                if chosen_body_method == "Campos Dinámicos" and request_body_actual_schema:
                                    generate_form_fields(
                                        request_body_actual_schema,
                                        f"{endpoint_id}_body",
                                        [],
                                        [],
                                        endpoint_id,
                                        spec,
                                        GLOBAL_SUFFIX
                                    )
                                    st.markdown("--- \n JSON Adicional/Sobrescritura (opcional):")
                                    raw_json_key_additional = f"{endpoint_id}_additional_raw_json_body{GLOBAL_SUFFIX}"
                                    st.text_area(
                                        "JSON para fusionar (este tiene precedencia sobre los campos):",
                                        value=st.session_state.get(raw_json_key_additional,"{}"),
                                        height=100,
                                        key=raw_json_key_additional,
                                        help="Este JSON se fusionará con los datos de los campos. En caso de conflicto de claves, este JSON prevalece."
                                    )
                                else:
                                    raw_json_key_main = f"{endpoint_id}_main_raw_json_body{GLOBAL_SUFFIX}"
                                    raw_json_default = "{}"
                                    if request_body_actual_schema and request_body_actual_schema.get("example"):
                                        try:
                                            raw_json_default = json.dumps(request_body_actual_schema.get("example",{}), indent=2)
                                        except TypeError:
                                            raw_json_default = "{}"
                                    st.text_area(
                                        "JSON Crudo para el Body:",
                                        value=st.session_state.get(raw_json_key_main, raw_json_default),
                                        height=200,
                                        key=raw_json_key_main
                                    )

                            elif "application/x-www-form-urlencoded" in content_spec:
                                form_schema_ref = content_spec["application/x-www-form-urlencoded"].get("schema", {}).get("$ref")
                                if form_schema_ref:
                                    form_schema = resolve_ref(spec, form_schema_ref)
                                    if form_schema and "properties" in form_schema:
                                        st.markdown("Campos del formulario (x-www-form-urlencoded):")
                                        for prop_name, prop_details in form_schema["properties"].items():
                                            field_key = f"{endpoint_id}_form_{prop_name}{GLOBAL_SUFFIX}"
                                            label = prop_details.get("title", prop_name)
                                            input_type = "password" if "password" in prop_name.lower() else "default"
                                            default_val = st.session_state.get('user_info',{}).get("username","") if prop_name == "username" else ""

                                            st.text_input(
                                                label,
                                                key=field_key,
                                                type=input_type,
                                                value=default_val,
                                                help=prop_details.get("description","")
                                            )
                            else:
                                st.caption("Tipo de contenido del body no soportado para formulario interactivo.")
                        else:
                            st.caption("Este endpoint no define un cuerpo (body) para el request.")

                    st.markdown("---")

                    is_login_endpoint = "login" in operation.get("operationId","").lower() or \
                                        (operation.get("tags") and "auth" in [t.lower() for t in operation.get("tags",[])])
                    button_label = "🔑 Autenticar" if is_login_endpoint else "🚀 Ejecutar"

                    if st.button(button_label, key=f"{endpoint_id}_execute_button{GLOBAL_SUFFIX}"):
                        execute_api_request(endpoint_info, api_base_url, spec)

                    render_response_data(endpoint_id, tag_name_to_display)

        else:
            if sorted_tags : st.warning("Por favor, selecciona un grupo de endpoints válido.")
else:
    if not st.session_state.get('grouped_endpoints') and not st.session_state.get('error_message'):
        st.info("☝️ Carga una especificación API desde el panel lateral para comenzar.")
