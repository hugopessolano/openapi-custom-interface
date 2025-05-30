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
    st.session_state.active_security_credentials = {} 
    st.session_state.auth_input_values = {} 
    st.session_state.auth_status_message = None 
    st.session_state.user_info = {}
    st.session_state.show_detail_dialog = False
    st.session_state.show_auth_dialog = False 
    st.session_state.active_expander_id = None
    st.session_state.endpoint_responses = {}
    st.session_state.active_tab_name = None
    st.session_state.form_field_values = {} 
    st.session_state.form_field_includes = {}
    st.session_state.api_json_location = "openapi.json" 

def load_api_spec(api_base_url_input:str, api_json_location_input:str) -> None:
    current_api_url = st.session_state.get("current_api_url", api_base_url_input)
    current_api_json_loc = st.session_state.get("api_json_location", api_json_location_input)

    reset_api_spec(current_api_url) 
    st.session_state.api_json_location = current_api_json_loc

    if current_api_url:
        openapi_url = f"{current_api_url.rstrip('/')}/{current_api_json_loc.lstrip('/')}"
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
                            endpoint_id = f"{tag_name}_{method_str.upper()}_{path_str.replace('/','_').replace('{','').replace('}','')}{GLOBAL_SUFFIX}"
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
            st.session_state.error_message = None 

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
        for p_idx, param_schema_ref in enumerate(operation["parameters"]):
            param_schema = resolve_ref(spec, param_schema_ref["$ref"]) if "$ref" in param_schema_ref else param_schema_ref
            if not param_schema: continue

            param_base_key = f"{endpoint_id}_p_{p_idx}_{param_schema['name']}{GLOBAL_SUFFIX}"
            param_value = None

            if param_schema['in'] == 'path':
                param_value = st.session_state.get(f"{param_base_key}_path", "")
                if not param_value and param_schema.get("required", False):
                    st.error(f"Parámetro de path requerido '{param_schema['name']}' está vacío.")
                    path_params_missing = True
                    break
                current_path_req = current_path_req.replace(f"{{{param_schema['name']}}}", str(param_value or ""))
            elif param_schema['in'] == 'query':
                param_value = st.session_state.get(f"{param_base_key}_query", "")
                if param_value or (param_schema.get("required", False) and param_value == ""): 
                    query_params_req[param_schema['name']] = param_value
    
    if path_params_missing:
        st.session_state.active_expander_id = endpoint_id 
        st.rerun()
        return

    full_url_req = f"{api_base_url.rstrip('/')}{current_path_req}"
    
    request_kwargs = {
        "params": {k: v for k, v in query_params_req.items() if v is not None} or None, 
        "timeout": 20
    }
    
    headers_req = {"Accept": "application/json"}
    query_params_for_auth = {} 

    is_potentially_auth_endpoint = False
    if not operation.get("security"): 
            op_id_lower = operation.get("operationId", "").lower()
            tags_lower = [t.lower() for t in operation.get("tags", [])]
            if any(keyword in op_id_lower for keyword in ["auth", "login", "token", "authorize"]) or \
               any(tag in tags_lower for tag in ["auth", "authentication", "login"]):
                is_potentially_auth_endpoint = True

    if not is_potentially_auth_endpoint and operation.get("security") and st.session_state.get('active_security_credentials'):
        op_security_requirements = operation.get("security", []) 
        
        applied_auth_for_op = False
        for sec_req_option in op_security_requirements: 
            for scheme_name_from_op, _ in sec_req_option.items():
                if scheme_name_from_op in st.session_state.active_security_credentials:
                    creds = st.session_state.active_security_credentials[scheme_name_from_op]
                    
                    if creds.get("value"): 
                        if creds.get("type") == "apiKey":
                            if creds.get("in") == "header" and creds.get("name"):
                                headers_req[creds["name"]] = creds["value"]
                                applied_auth_for_op = True
                            elif creds.get("in") == "query" and creds.get("name"):
                                query_params_for_auth[creds["name"]] = creds["value"]
                                applied_auth_for_op = True
                        
                        elif creds.get("type") == "http" and creds.get("scheme") == "bearer":
                            headers_req["Authorization"] = f"Bearer {creds['value']}"
                            applied_auth_for_op = True
                        
                        elif creds.get("type") == "oauth2" : 
                            if creds.get("value"):
                                headers_req["Authorization"] = f"Bearer {creds['value']}"
                                applied_auth_for_op = True
                        
                        if applied_auth_for_op:
                            st.caption(f"Aplicando autorización con esquema: `{scheme_name_from_op}`.")
                            break 
            if applied_auth_for_op:
                break 

        if not applied_auth_for_op and op_security_requirements:
            required_scheme_names = []
            for sec_req_opt in op_security_requirements:
                required_scheme_names.extend(list(sec_req_opt.keys()))
            unique_required_schemes = list(set(required_scheme_names))
            st.warning(f"Endpoint protegido, pero no se encontraron credenciales activas para los esquemas requeridos: {', '.join(unique_required_schemes)}")


    if query_params_for_auth:
        request_kwargs["params"] = {**(request_kwargs.get("params") or {}), **query_params_for_auth}
    
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
            default_body_method = "Campos Dinámicos" if actual_request_body_schema else "JSON Crudo"
            chosen_body_method = st.session_state.get(chosen_body_method_key, default_body_method)

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
                    st.session_state.active_expander_id = endpoint_id; st.rerun(); return

            if actual_body_to_send is not None:
                request_kwargs["json"] = actual_body_to_send

        elif "application/x-www-form-urlencoded" in content_spec:
            content_type_for_request = "application/x-www-form-urlencoded"
            form_data_req = {}
            form_schema_ref = content_spec["application/x-www-form-urlencoded"].get("schema", {}).get("$ref")
            actual_form_schema = resolve_ref(spec, form_schema_ref) if form_schema_ref else content_spec["application/x-www-form-urlencoded"].get("schema", {})
            
            if actual_form_schema and "properties" in actual_form_schema:
                for prop_name, prop_details in actual_form_schema["properties"].items():
                    field_key = f"{endpoint_id}_form_{prop_name}{GLOBAL_SUFFIX}"
                    if field_key in st.session_state: 
                        field_value = st.session_state[field_key]
                        
                        is_prop_required_in_body = prop_name in actual_form_schema.get("required", [])
                        
                        if (field_value is not None and field_value != "") or \
                           is_prop_required_in_body or \
                           (prop_name == "grant_type" and field_value == prop_details.get("pattern", prop_details.get("default"))):
                            form_data_req[prop_name] = field_value
            
            if form_data_req:
                request_kwargs["data"] = form_data_req
            elif actual_form_schema and actual_form_schema.get("required") and not form_data_req:
                 st.warning("El cuerpo del request x-www-form-urlencoded tiene campos requeridos pero parece estar vacío o no se pudieron construir los datos.")


    if content_type_for_request:
        headers_req["Content-Type"] = content_type_for_request
    
    request_kwargs["headers"] = headers_req

    if request_kwargs.get("json") is None and request_kwargs.get("data") is None and \
       method.upper() in ["POST", "PUT", "PATCH"] and "requestBody" in operation :
        st.warning("El cuerpo del request (body) está vacío. Se enviará la solicitud igualmente.")

    st.info(f"Ejecutando: {method.upper()} {full_url_req}")
    if request_kwargs.get("params"): st.caption(f"Query Params: {request_kwargs['params']}")
    if headers_req: st.caption(f"Headers: {json.dumps(headers_req, indent=2)}") 
    if request_kwargs.get("json"): st.caption(f"JSON Body: {json.dumps(request_kwargs['json'])}")
    if request_kwargs.get("data"): st.caption(f"Form Data: {request_kwargs['data']}")


    try:
        with st.spinner("Enviando solicitud API..."):
            api_response = requests.request(method.upper(), full_url_req, **request_kwargs)

        response_content_type = api_response.headers.get("Content-Type", "")
        response_data = None
        raw_text_response = api_response.text 

        if "application/json" in response_content_type:
            try:
                response_data = api_response.json()
            except json.JSONDecodeError:
                response_data = {
                    "error_msg_internal": "La respuesta indicó ser JSON pero no pudo ser parseada.",
                    "status_code": api_response.status_code,
                    "raw_text": raw_text_response
                }
        else:
            response_data = {
                "error_msg_internal": f"Tipo de contenido no JSON recibido: {response_content_type}",
                "status_code": api_response.status_code,
                "raw_text": raw_text_response
            }
        
        st.session_state.endpoint_responses[endpoint_id] = response_data

        if is_potentially_auth_endpoint and api_response.ok and isinstance(response_data, dict):
            all_security_schemes = spec.get("components", {}).get("securitySchemes", {})
            auth_success_for_scheme = False

            for scheme_name_in_spec, scheme_details_in_spec in all_security_schemes.items():
                token_found_in_response = None
                
                if scheme_details_in_spec.get("type") == "apiKey":
                    key_name_in_response = scheme_details_in_spec.get("name") 
                    if key_name_in_response and key_name_in_response in response_data:
                        token_found_in_response = response_data[key_name_in_response]
                
                elif scheme_details_in_spec.get("type") == "http" and scheme_details_in_spec.get("scheme") == "bearer":
                    possible_token_keys = ["access_token", "accessToken", "token", scheme_name_in_spec.lower()]
                    for tk in possible_token_keys:
                        if tk in response_data:
                            token_found_in_response = response_data[tk]
                            break
                
                elif scheme_details_in_spec.get("type") == "oauth2": 
                    if "access_token" in response_data:
                         token_found_in_response = response_data["access_token"]

                if token_found_in_response:
                    st.session_state.active_security_credentials[scheme_name_in_spec] = {
                        "type": scheme_details_in_spec.get("type"),
                        "value": str(token_found_in_response),
                        "in": scheme_details_in_spec.get("in"), # Para apiKey y http (aunque http no lo usa para 'in')
                        "name": scheme_details_in_spec.get("name"), # Para apiKey
                        "scheme": scheme_details_in_spec.get("scheme") # Para http (ej. 'bearer')
                    }
                    st.session_state.auth_status_message = f"Autenticación exitosa con esquema '{scheme_name_in_spec}'."
                    
                    token_keys_to_exclude = ["access_token", "accessToken", "token"]
                    if scheme_details_in_spec.get("type") == "apiKey" and scheme_details_in_spec.get("name"):
                        token_keys_to_exclude.append(scheme_details_in_spec.get("name"))
                    
                    st.session_state.user_info = {k: v for k, v in response_data.items() if k not in token_keys_to_exclude}
                    auth_success_for_scheme = True
                    break 

            if not auth_success_for_scheme and not response_data.get("error_msg_internal"): # Si fue OK pero no encontramos token
                st.session_state.auth_status_message = f"Respuesta OK del endpoint de autenticación ({api_response.status_code}), pero no se pudo extraer un token conocido. Respuesta: {json.dumps(response_data, indent=2)[:500]}" # Limitar longitud de respuesta
        
        elif is_potentially_auth_endpoint and not api_response.ok: 
            st.session_state.user_info = {}
            error_detail_key = "detail" if "detail" in response_data else "error_msg_internal"
            error_detail = response_data.get(error_detail_key, raw_text_response if raw_text_response else "Error desconocido en login")
            
            if isinstance(error_detail, list):
                try: error_detail = json.dumps(error_detail)
                except TypeError: error_detail = str(error_detail)
            elif isinstance(error_detail, dict):
                 try: error_detail = json.dumps(error_detail)
                 except TypeError: error_detail = str(error_detail)

            st.session_state.auth_status_message = f"Fallo en la autenticación ({api_response.status_code}). Detalle: {error_detail}"
        
        elif not is_potentially_auth_endpoint and api_response.status_code in [401, 403]:
            st.warning(f"Error de autorización ({api_response.status_code}). Verifica tus credenciales en 'Configurar Autorización'. Respuesta: {raw_text_response[:300]}")

    except requests.exceptions.Timeout:
        error_msg = f"Error de API: Timeout después de {request_kwargs['timeout']} segundos."
        st.error(error_msg)
        st.session_state.endpoint_responses[endpoint_id] = {"error_msg_internal": error_msg, "status_code": 408, "raw_text": ""}
    except requests.exceptions.RequestException as e_req:
        error_msg = f"Error de API: {e_req}"
        st.error(error_msg)
        st.session_state.endpoint_responses[endpoint_id] = {"error_msg_internal": error_msg, "status_code": 500, "raw_text": ""} 
    
    st.session_state.active_expander_id = endpoint_id 
    st.rerun()
