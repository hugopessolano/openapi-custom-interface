import streamlit as st

def initialize_session_state():
    """
    Inicializa las claves necesarias en el estado de sesión de Streamlit (st.session_state)
    si aún no existen. Esto evita errores de 'KeyError' y asegura que las variables
    tengan un valor inicial.
    """
    default_states = {
        'show_detail_dialog': False,       # Controla la visibilidad del diálogo de detalles
        'dialog_title': "Detalles",        # Título para el diálogo de detalles
        'dialog_data': None,               # Datos a mostrar en el diálogo de detalles
        
        'form_field_values': {},           # Almacena los valores de los campos de formulario dinámicos
        'form_field_includes': {},         # Almacena qué campos de formulario están marcados para incluir
        
        'active_expander_id': None,        # ID del expander de endpoint actualmente abierto
        'endpoint_responses': {},          # Almacena las respuestas de las llamadas a la API
        'active_tab_name': None,           # Nombre del tag/grupo de API actualmente seleccionado
        
        'show_auth_dialog': False,         # Controla la visibilidad del diálogo de autorización
        'auth_dialog_security_schemes': {},# Esquemas de seguridad para mostrar en el diálogo de auth
        'auth_input_values': {},           # Valores ingresados por el usuario en el diálogo de auth
        'active_security_credentials': {}, # Credenciales activas (reemplaza 'auth_token')
        'auth_status_message': None,       # Mensaje general sobre el estado de autenticación (éxito/error/info)
        'user_info': {},                   # Información del usuario (si la API la devuelve al loguear)
        
        'openapi_spec': None,              # La especificación OpenAPI cargada (en formato JSON/dict)
        'error_message': None,             # Mensaje de error general de la aplicación
        'grouped_endpoints': None,         # Endpoints agrupados por tags
        'current_api_url': "http://hugopessolano.duckdns.org:8000", # URL base de la API por defecto
        'api_json_location': "openapi.json", # Ubicación del JSON de la API por defecto
        'tag_descriptions': {},            # Descripciones de los tags de la API
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value