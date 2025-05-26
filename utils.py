import json

def resolve_ref(spec, ref_string):
    parts = ref_string.strip("#/").split("/")
    current = spec
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def get_nested_value(data_dict, path_list, default=None):
    current = data_dict
    for key_or_index in path_list:
        if isinstance(current, dict) and isinstance(key_or_index, str) and key_or_index in current:
            current = current[key_or_index]
        elif isinstance(current, list) and isinstance(key_or_index, int) and 0 <= key_or_index < len(current):
            current = current[key_or_index]
        else:
            return default
    return current


def set_nested_value(data_dict, path_list, value):
    current = data_dict
    for i, key_or_index in enumerate(path_list):
        if i == len(path_list) - 1:
            if isinstance(current, dict) and isinstance(key_or_index, str):
                current[key_or_index] = value
            elif isinstance(current, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current):
                    current[key_or_index] = value
                elif key_or_index == len(current):
                    current.append(value)
        else:
            if isinstance(current, dict) and isinstance(key_or_index, str):
                current = current.setdefault(key_or_index, {})
            elif isinstance(current, list) and isinstance(key_or_index, int):
                while key_or_index >= len(current):
                    current.append({})
                current_item = current[key_or_index]
                if not isinstance(current_item, dict) and \
                   (i < len(path_list) -1 and isinstance(path_list[i+1], str)):
                    current[key_or_index] = {}
                current = current[key_or_index]
            else:
                return

def deep_merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination