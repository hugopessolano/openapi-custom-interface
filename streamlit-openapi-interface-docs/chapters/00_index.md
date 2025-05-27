# Tutorial: openapi-custom-interface

This project is an **interactive client** for APIs described by the
*OpenAPI Specification*. It allows users to load an API definition,
which is then used to **dynamically generate input forms** for
each endpoint. Users can fill in parameters and request bodies,
execute API calls via an **API Service**, and view the results,
which are **displayed** in a user-friendly format, including tabular
views and detailed pop-ups. The application manages user input,
API responses, and **authentication tokens** persistently across
interactions using the **Streamlit Session State**.


## Visual Overview

```mermaid
flowchart TD
    A0["Streamlit Session State
"]
    A1["OpenAPI Specification
"]
    A2["API Service
"]
    A3["Dynamic Form Generation
"]
    A4["Request & Response Data Handling
"]
    A5["API Response Display
"]
    A6["Authentication Management
"]
    A2 -- "Reads spec" --> A1
    A1 -- "Guides form creation" --> A3
    A3 -- "Saves form data" --> A0
    A0 -- "Provides form data" --> A3
    A2 -- "Updates state" --> A0
    A0 -- "Provides config/data" --> A2
    A2 -- "Processes request/response" --> A4
    A4 -- "Accesses state data" --> A0
    A5 -- "Reads response data" --> A0
    A5 -- "Triggers dialog state" --> A0
    A6 -- "Manages auth state" --> A0
    A0 -- "Provides auth state" --> A6
    A2 -- "Executes auth logic" --> A6
```

## Chapters

1. [OpenAPI Specification
](01_openapi_specification_.md)
2. [Dynamic Form Generation
](02_dynamic_form_generation_.md)
3. [Authentication Management
](03_authentication_management_.md)
4. [Streamlit Session State
](04_streamlit_session_state_.md)
5. [API Service
](05_api_service_.md)
6. [Request & Response Data Handling
](06_request___response_data_handling_.md)
7. [API Response Display
](07_api_response_display_.md)

---