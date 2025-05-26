import streamlit as st
import requests
import json
from collections import defaultdict
import copy
from utils import resolve_ref, deep_merge
from ui_components.form_generator import build_json_from_form
from app_config import GLOBAL_SUFFIX

def reset_api_spec(api_base_url_input:str) -> None:
    st.session_state.openapi_spec = None
    st.session_state.error_message = None
    st.session_state.grouped_endpoints = None
    st.session_state.tag_descriptions = {}
    st.session_state.current_api_url = api_base_url_input
    st.session_state.auth_token = None
    st.session_state.auth_error = None
    st.session_state.user_info = {}
    st.session_state.show_detail_dialog = False
    st.session_state.active_expander_id = None
    st.session_state.endpoint_responses = {}
    st.session_state.active_tab_name = None
    st.session_state.form_field_values = {} 
    st.session_state.form_field_includes = {}

def load_api_spec(api_base_url_input:str, api_json_location_input:str) -> None:
        
    reset_api_spec(api_base_url_input)

    if api_base_url_input:
        openapi_url = f"{api_base_url_input.rstrip('/')}/{api_json_location_input.lstrip('/')}"
        try:
            with st.spinner(f"Cargando especificación desde {openapi_url}..."):
                response = requests.get(openapi_url, timeout=15)
                response.raise_for_status()
                spec_data: dict = response.json()
                st.session_state.openapi_spec = spec_data

                grouped = defaultdict(list)
                st.session_state.tag_descriptions = {
                    tag_def.get("name", f"tag_desconocido_{i}"): tag_def
                    for i, tag_def in enumerate(spec_data.get("tags", []))
                }

                if "paths" in spec_data:
                    for path_str, path_item in spec_data["paths"].items():
                        for method_str, operation_obj in path_item.items():
                            tag_name = operation_obj.get("tags", ["default"])[0]
                            endpoint_id = f"{tag_name}_{method_str.upper()}_{path_str.replace('/','_').replace('{','').replace('}','')}"
                            grouped[tag_name].append({
                                "path": path_str,
                                "method": method_str,
                                "operation": operation_obj,
                                "id": endpoint_id
                            })
                    for tag_name_iter in grouped:
                        grouped[tag_name_iter].sort(key=lambda x: (x["path"], x["method"]))
                    
                    st.session_state.grouped_endpoints = dict(grouped)

                    if grouped:
                        sorted_keys = sorted(grouped.keys(), key=lambda t: (t == "default", t.lower()))
                        st.session_state.active_tab_name = sorted_keys[0] if sorted_keys else None
                else:
                    st.session_state.grouped_endpoints = {}
            st.success(f"API '{spec_data.get('info',{}).get('title','N/A')}' cargada exitosamente.")

        except requests.exceptions.RequestException as e:
            st.session_state.error_message = f"Error de red al cargar API: {e}"
        except json.JSONDecodeError as e:
            st.session_state.error_message = f"Error al parsear JSON de la API: {e}. Contenido: {response.text[:200]}"
        except Exception as e:
            st.session_state.error_message = f"Error inesperado al cargar API: {e}"
    else:
        st.warning("Por favor, ingrese la URL base de la API.")
        st.session_state.current_api_url = ""
        st.session_state.grouped_endpoints = None


def execute_api_request(endpoint_info:dict, api_base_url:str, spec:dict) -> None:
    path = endpoint_info["path"]
    method = endpoint_info["method"]
    operation = endpoint_info["operation"]
    endpoint_id = endpoint_info["id"]

    if endpoint_id in st.session_state.endpoint_responses:
        del st.session_state.endpoint_responses[endpoint_id]

    current_path_req = path
    query_params_req = {}
    path_params_missing = False

    if "parameters" in operation:
        for p_idx, param_schema in enumerate(operation["parameters"]):
            param_base_key = f"{endpoint_id}_p_{p_idx}_{param_schema['name']}{GLOBAL_SUFFIX}"
            param_value = None

            if param_schema['in'] == 'path':
                param_value = st.session_state.get(f"{param_base_key}_path", "")
                if not param_value and param_schema.get("required", False):
                    st.error(f"Parámetro de path requerido '{param_schema['name']}' está vacío.")
                    path_params_missing = True
                    break
                current_path_req = current_path_req.replace(f"{{{param_schema['name']}}}", str(param_value))
            elif param_schema['in'] == 'query':
                param_value = st.session_state.get(f"{param_base_key}_query", "")
                if param_value: # Solo añade si tiene valor
                    query_params_req[param_schema['name']] = param_value
                elif param_schema.get("required", False) and not param_value:
                     st.warning(f"Parámetro de query requerido '{param_schema['name']}' está vacío pero se continuará.")


    if path_params_missing:
        return

    full_url_req = f"{api_base_url.rstrip('/')}{current_path_req}"
    
    request_kwargs = {
        "params": {k: v for k, v in query_params_req.items() if v is not None} or None, 
        "timeout": 20
    }
    
    headers_req = {"Accept": "application/json"}
    is_login_endpoint = "login" in operation.get("operationId","").lower() or \
                        (operation.get("tags") and "auth" in [t.lower() for t in operation.get("tags",[])])
    
    if st.session_state.get('auth_token') and not is_login_endpoint:
        headers_req["Authorization"] = f"Bearer {st.session_state.auth_token}"

    actual_body_to_send = None
    content_type_for_request = None

    if "requestBody" in operation:
        request_body_spec = operation["requestBody"]
        content_spec = request_body_spec.get("content", {})

        if "application/json" in content_spec:
            content_type_for_request = "application/json"
            json_schema_ref = content_spec["application/json"].get("schema", {}).get("$ref")
            actual_request_body_schema = resolve_ref(spec, json_schema_ref) if json_schema_ref \
                                         else content_spec["application/json"].get("schema")

            chosen_body_method_key = f"{endpoint_id}_body_method{GLOBAL_SUFFIX}"
            chosen_body_method = st.session_state.get(chosen_body_method_key, "Campos Dinámicos")

            final_body_dict = {}
            if chosen_body_method == "Campos Dinámicos" and actual_request_body_schema:
                json_from_fields = build_json_from_form(endpoint_id, spec, actual_request_body_schema)
                final_body_dict = copy.deepcopy(json_from_fields) if json_from_fields is not None else {}

                additional_raw_json_key = f"{endpoint_id}_additional_raw_json_body{GLOBAL_SUFFIX}"
                additional_raw_str = st.session_state.get(additional_raw_json_key, "{}")
                if additional_raw_str.strip() and additional_raw_str != "{}":
                    try:
                        json_from_additional = json.loads(additional_raw_str)
                        final_body_dict = deep_merge(json_from_additional, final_body_dict)
                    except json.JSONDecodeError as e_merge:
                        st.warning(f"JSON adicional/de sobrescritura inválido, no se fusionará: {e_merge}")
                actual_body_to_send = final_body_dict if final_body_dict else None

            else:
                raw_json_key_main = f"{endpoint_id}_main_raw_json_body{GLOBAL_SUFFIX}"
                raw_json_str = st.session_state.get(raw_json_key_main, "{}")
                try:
                    actual_body_to_send = json.loads(raw_json_str) if raw_json_str.strip() else None
                except json.JSONDecodeError as e_raw:
                    st.error(f"JSON crudo para el body es inválido: {e_raw}")
                    return

            if actual_body_to_send is not None:
                request_kwargs["json"] = actual_body_to_send

        elif "application/x-www-form-urlencoded" in content_spec:
            content_type_for_request = "application/x-www-form-urlencoded"
            form_data_req = {}
            form_schema_ref = content_spec["application/x-www-form-urlencoded"].get("schema", {}).get("$ref")
            if form_schema_ref:
                form_schema = resolve_ref(spec, form_schema_ref)
                if form_schema and "properties" in form_schema:
                    for prop_name, _ in form_schema["properties"].items():
                        field_key = f"{endpoint_id}_form_{prop_name}{GLOBAL_SUFFIX}"
                        if field_key in st.session_state and st.session_state[field_key]:
                            form_data_req[prop_name] = st.session_state[field_key]
            if form_data_req:
                request_kwargs["data"] = form_data_req

    if content_type_for_request:
        headers_req["Content-Type"] = content_type_for_request
    
    request_kwargs["headers"] = headers_req

    if request_kwargs.get("json") is None and request_kwargs.get("data") is None and \
       method.upper() in ["POST", "PUT", "PATCH"]:
        st.warning("El cuerpo del request (body) está vacío. Se enviará la solicitud igualmente.")

    st.info(f"Ejecutando: {method.upper()} {full_url_req}")
    if request_kwargs.get("params"): st.caption(f"Query Params: {request_kwargs['params']}")
    if request_kwargs.get("json"): st.caption(f"JSON Body: {json.dumps(request_kwargs['json'])}")
    if request_kwargs.get("data"): st.caption(f"Form Data: {request_kwargs['data']}")


    try:
        with st.spinner("Enviando solicitud API..."):
            api_response = requests.request(method.upper(), full_url_req, **request_kwargs)

        response_content_type = api_response.headers.get("Content-Type", "")
        response_data = None
        if "application/json" in response_content_type:
            try:
                response_data = api_response.json()
            except json.JSONDecodeError:
                response_data = {
                    "error": "La respuesta indicó ser JSON pero no pudo ser parseada.",
                    "status_code": api_response.status_code,
                    "raw_text": api_response.text
                }
        else:
            response_data = {
                "error": f"Tipo de contenido no JSON recibido: {response_content_type}",
                "status_code": api_response.status_code,
                "raw_text": api_response.text
            }
        
        st.session_state.endpoint_responses[endpoint_id] = response_data

        if is_login_endpoint:
            if api_response.status_code == 200 and isinstance(response_data, dict) and "access_token" in response_data:
                st.session_state.auth_token = response_data["access_token"]
                st.session_state.auth_error = None
                st.session_state.user_info = {k: v for k, v in response_data.items() if k != "access_token"}
                st.success("Autenticación exitosa!")
            else:
                st.session_state.auth_token = None
                error_detail = response_data.get('detail', response_data.get('error', api_response.text if api_response.text else "Error desconocido"))
                st.session_state.auth_error = f"Fallo en la autenticación ({api_response.status_code}). Detalle: {error_detail}"
                st.error(st.session_state.auth_error)


    except requests.exceptions.Timeout:
        st.error(f"Error de API: Timeout después de {request_kwargs['timeout']} segundos.")
        st.session_state.endpoint_responses[endpoint_id] = {"error": f"Timeout ({request_kwargs['timeout']}s)"}
    except requests.exceptions.RequestException as e_req:
        st.error(f"Error de API: {e_req}")
        st.session_state.endpoint_responses[endpoint_id] = {"error": f"Excepción en la solicitud: {e_req}"}
    
    st.session_state.active_expander_id = endpoint_id
    st.rerun()