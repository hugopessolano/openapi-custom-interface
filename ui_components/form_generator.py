import streamlit as st
import json
from utils import resolve_ref, get_nested_value, set_nested_value
from app_config import GLOBAL_SUFFIX

def generate_form_fields(schema_obj, key_prefix, data_path_list, include_path_list, endpoint_id, spec_root, current_suffix_local):
    if not isinstance(schema_obj, dict):
        return

    schema_type = schema_obj.get("type")

    if schema_type == "object":
        if "properties" not in schema_obj:
            return

        for prop_name, prop_schema in schema_obj.get("properties", {}).items():
            actual_prop_schema = resolve_ref(spec_root, prop_schema["$ref"]) if "$ref" in prop_schema else prop_schema
            if actual_prop_schema is None:
                st.error(f"Error de referencia: {prop_schema.get('$ref')} para la propiedad '{prop_name}' no pudo ser resuelta.")
                continue

            new_data_path = data_path_list + [prop_name]
            new_include_path = include_path_list + [prop_name]
            new_key_prefix = f"{key_prefix}_{prop_name}"
            include_key_str = f"{endpoint_id}_include__{'__'.join(map(str,new_include_path))}"

            is_required = prop_name in schema_obj.get("required", [])
            has_default_or_example = actual_prop_schema.get("default") is not None or \
                                     actual_prop_schema.get("example") is not None
            default_include = is_required or (has_default_or_example and actual_prop_schema.get("type") not in ["object", "array"])

            current_include_val = get_nested_value(st.session_state.form_field_includes.get(endpoint_id, {}), new_include_path, default=default_include)
            if get_nested_value(st.session_state.form_field_includes.get(endpoint_id, {}), new_include_path) is None:
                 set_nested_value(st.session_state.form_field_includes.setdefault(endpoint_id, {}), new_include_path, default_include)
                 current_include_val = default_include

            field_desc = actual_prop_schema.get("description", "")

            if is_required:
                st.checkbox(f"Incluir `{prop_name}` (requerido)", value=True, key=f"{include_key_str}_cb_req{current_suffix_local}", disabled=True, help=field_desc)
                set_nested_value(st.session_state.form_field_includes.setdefault(endpoint_id, {}), new_include_path, True) # Forzar inclusión
                is_field_active = True
            else:
                new_include_state = st.checkbox(f"Incluir `{prop_name}`", value=current_include_val, key=include_key_str + current_suffix_local, help=field_desc)
                set_nested_value(st.session_state.form_field_includes.setdefault(endpoint_id, {}), new_include_path, new_include_state)
                is_field_active = new_include_state

            with st.container():
                if len(data_path_list) > 0:
                    st.markdown(f"<div style='margin-left: 25px; border-left: 1px solid #ccc; padding-left: 10px;'>", unsafe_allow_html=True)

                if is_field_active or actual_prop_schema.get("type") in ["object", "array"]:
                    if actual_prop_schema.get("type") == "object":
                        st.markdown(f"**{prop_name.capitalize()}:**")
                    generate_form_fields(actual_prop_schema, new_key_prefix, new_data_path, new_include_path, endpoint_id, spec_root, current_suffix_local)
                elif not is_field_active :
                     st.caption(f"(Campo '{prop_name}' no incluido)")

                if len(data_path_list) > 0:
                    st.markdown("</div>", unsafe_allow_html=True)

    elif schema_type == "array":
        prop_name_array = data_path_list[-1] if data_path_list else "ArrayRaiz"
        is_array_field_active = get_nested_value(st.session_state.form_field_includes.get(endpoint_id,{}), include_path_list, default=True)

        if is_array_field_active:
            st.markdown(f"**{prop_name_array.capitalize()} (Array):**")
            items_schema = schema_obj.get("items", {}) 
            actual_items_schema = resolve_ref(spec_root, items_schema["$ref"]) if "$ref" in items_schema else items_schema

            if actual_items_schema and actual_items_schema.get("type") == "object":
                array_items_values = get_nested_value(st.session_state.form_field_values.setdefault(endpoint_id, {}), data_path_list, default=[])
                array_items_includes = get_nested_value(st.session_state.form_field_includes.setdefault(endpoint_id, {}), include_path_list, default=[])

                if not isinstance(array_items_values, list): array_items_values = []
                if not isinstance(array_items_includes, list) or len(array_items_includes) != len(array_items_values):
                    array_items_includes = [{} for _ in array_items_values]

                for idx_sync in range(len(array_items_values)):
                    if not isinstance(array_items_values[idx_sync], dict): array_items_values[idx_sync] = {}
                    if idx_sync < len(array_items_includes) and not isinstance(array_items_includes[idx_sync], dict):
                        array_items_includes[idx_sync] = {}
                    elif idx_sync >= len(array_items_includes):
                        array_items_includes.append({})

                set_nested_value(st.session_state.form_field_values[endpoint_id], data_path_list, array_items_values)
                set_nested_value(st.session_state.form_field_includes[endpoint_id], include_path_list, array_items_includes)

                for idx, _ in enumerate(array_items_values):
                    with st.container():
                        st.markdown(f"<div style='border: 1px solid #444; padding: 10px; margin-top:5px; margin-bottom:5px; border-radius:5px;'>", unsafe_allow_html=True)
                        item_key_prefix_arr = f"{key_prefix}_{idx}"
                        item_data_path_arr = data_path_list + [idx]
                        item_include_path_arr = include_path_list + [idx]

                        cols_item_header_arr = st.columns([0.9, 0.1])
                        with cols_item_header_arr[0]: st.markdown(f"**Item #{idx + 1}**")
                        with cols_item_header_arr[1]:
                            if st.button("🗑️", key=f"{item_key_prefix_arr}_delete{current_suffix_local}", help="Eliminar item"):
                                array_items_values.pop(idx)
                                array_items_includes.pop(idx)
                                set_nested_value(st.session_state.form_field_values[endpoint_id], data_path_list, array_items_values)
                                set_nested_value(st.session_state.form_field_includes[endpoint_id], include_path_list, array_items_includes)
                                st.rerun()
                        generate_form_fields(actual_items_schema, item_key_prefix_arr, item_data_path_arr, item_include_path_arr, endpoint_id, spec_root, current_suffix_local)
                        st.markdown("</div>", unsafe_allow_html=True)

                button_add_label = f"✚ Añadir a `{prop_name_array}`"
                if st.button(button_add_label, key=f"{key_prefix}_add_item{current_suffix_local}"):
                    array_items_values.append({})
                    array_items_includes.append({})
                    set_nested_value(st.session_state.form_field_values[endpoint_id], data_path_list, array_items_values)
                    set_nested_value(st.session_state.form_field_includes[endpoint_id], include_path_list, array_items_includes)
                    st.rerun()

            else:
                array_field_key_simple = f"{endpoint_id}_value__{'__'.join(map(str,data_path_list))}{current_suffix_local}"
                default_simple_array_val = schema_obj.get("default", schema_obj.get("example", []))
                default_simple_array_str = json.dumps(default_simple_array_val, indent=2)

                current_simple_array_str = get_nested_value(st.session_state.form_field_values.get(endpoint_id, {}), data_path_list, default=default_simple_array_str)
                if get_nested_value(st.session_state.form_field_values.get(endpoint_id, {}), data_path_list) is None:
                    set_nested_value(st.session_state.form_field_values.setdefault(endpoint_id, {}), data_path_list, default_simple_array_str)

                user_simple_array_input = st.text_area(
                    f"JSON para array `{prop_name_array}`:",
                    value=str(current_simple_array_str),
                    key=array_field_key_simple,
                    height=100,
                    help=f"Array en formato JSON. Ejemplo: {default_simple_array_str if default_simple_array_val else '[]'}"
                )
                set_nested_value(st.session_state.form_field_values.setdefault(endpoint_id, {}), data_path_list, user_simple_array_input)
        else:
            st.caption(f"(Array '{prop_name_array}' no incluido)")

    else:
        prop_name_simple = data_path_list[-1] if data_path_list else "valor_raiz"
        is_simple_field_active = get_nested_value(st.session_state.form_field_includes.get(endpoint_id,{}), include_path_list, default=True)

        if is_simple_field_active:
            field_key = f"{endpoint_id}_value__{'__'.join(map(str,data_path_list))}{current_suffix_local}"
            default_val_prop = schema_obj.get("default", schema_obj.get("example"))

            current_val_prop = get_nested_value(st.session_state.form_field_values.get(endpoint_id, {}), data_path_list, default=None)
            if current_val_prop is None:
                 current_val_prop = default_val_prop if default_val_prop is not None else ""
                 if schema_type in ["integer","number"] and current_val_prop=="": current_val_prop=0
                 elif schema_type=="boolean" and current_val_prop=="": current_val_prop=False
                 set_nested_value(st.session_state.form_field_values.setdefault(endpoint_id,{}), data_path_list, current_val_prop)

            field_label = f"`{prop_name_simple}` ({schema_type or 'desconocido'})"
            val_prop = None

            if schema_type=="integer":
                val_prop=st.number_input(field_label, value=int(current_val_prop) if str(current_val_prop).strip().lstrip('-').isdigit() else 0, key=field_key, step=1)
            elif schema_type=="number":
                val_prop=st.number_input(field_label, value=float(current_val_prop) if str(current_val_prop).strip().replace('.','',1).lstrip('-').isdigit() else 0.0, key=field_key, format="%.2f")
            elif schema_type=="boolean":
                val_prop=st.toggle(field_label, value=bool(current_val_prop), key=field_key)
            elif schema_type=="string":
                if "enum" in schema_obj:
                    enum_options = schema_obj["enum"]
                    idx=0
                    try:
                        idx = enum_options.index(current_val_prop) if current_val_prop in enum_options else \
                              (enum_options.index(default_val_prop) if default_val_prop in enum_options else 0)
                    except ValueError: idx=0
                    val_prop = st.selectbox(field_label, options=enum_options, index=idx, key=field_key)
                else:
                    val_prop = st.text_input(field_label, value=str(current_val_prop), key=field_key)
            else:
                val_prop = st.text_input(f"`{prop_name_simple}` (tipo '{schema_type}')", value=str(current_val_prop), key=field_key)

            if val_prop is not None:
                set_nested_value(st.session_state.form_field_values.setdefault(endpoint_id,{}), data_path_list, val_prop)

def build_json_from_form(endpoint_id, schema_root, request_body_schema_param):
    if endpoint_id not in st.session_state.form_field_values or \
       endpoint_id not in st.session_state.form_field_includes:
        return {}

    form_values_root = st.session_state.form_field_values.get(endpoint_id, {})
    form_includes_root = st.session_state.form_field_includes.get(endpoint_id, {})

    def recurse_build(current_values_node, current_includes_node, current_schema_node):
        if not current_schema_node:
            return None

        schema_type = current_schema_node.get("type")
        built_node = None

        if schema_type == "object":
            if not isinstance(current_values_node, dict) or not isinstance(current_includes_node, dict):
                return None
            current_result_dict = {}
            for key, prop_schema_ref in current_schema_node.get("properties", {}).items():
                actual_prop_schema = resolve_ref(schema_root, prop_schema_ref["$ref"]) if "$ref" in prop_schema_ref else prop_schema_ref
                if not actual_prop_schema: continue

                include_status_val = current_includes_node.get(key)

                if include_status_val:
                    if key in current_values_node:
                        value_data = current_values_node[key]
                    
                        built_prop = recurse_build(
                            value_data,
                            include_status_val if isinstance(include_status_val, (dict,list)) else True,
                            actual_prop_schema
                        )
                        if built_prop is not None:
                            current_result_dict[key] = built_prop
            if current_result_dict:
                built_node = current_result_dict

        elif schema_type == "array":
            items_schema_ref = current_schema_node.get("items", {})
            actual_items_schema = resolve_ref(schema_root, items_schema_ref["$ref"]) if "$ref" in items_schema_ref else items_schema_ref
            if not actual_items_schema: return []

            if actual_items_schema.get("type") == "object":
                if isinstance(current_values_node, list) and \
                   isinstance(current_includes_node, list) and \
                   len(current_values_node) == len(current_includes_node):
                    built_array_items = []
                    for idx, item_values in enumerate(current_values_node):
                        item_includes = current_includes_node[idx]
                        built_item = recurse_build(item_values, item_includes, actual_items_schema)
                        if built_item is not None:
                            built_array_items.append(built_item)
                    built_node = built_array_items
            else:
                if isinstance(current_values_node, str):
                    try:
                        built_node = json.loads(current_values_node) if current_values_node.strip() else []
                    except json.JSONDecodeError:
                        built_node = []
                elif isinstance(current_values_node, list):
                    built_node = current_values_node
                else:
                    built_node = []

        else:
            if current_schema_node.get("type") in ["integer", "number"] and current_values_node == "":
                built_node = None
            else:
                built_node = current_values_node
        return built_node

    return recurse_build(form_values_root, form_includes_root, request_body_schema_param)