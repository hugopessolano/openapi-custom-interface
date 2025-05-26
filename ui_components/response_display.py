import streamlit as st
from app_config import GLOBAL_SUFFIX, PANDAS_AVAILABLE, pd
from .detail_dialog import trigger_detail_dialog

def render_response_data(endpoint_id, tag_name_to_display):
    if endpoint_id in st.session_state.get('endpoint_responses', {}):
        st.markdown("--- \n #### Respuesta:")
        saved_resp_req = st.session_state.endpoint_responses[endpoint_id]

        if isinstance(saved_resp_req, dict) and "error" in saved_resp_req:
            st.error(f"Error en la respuesta: {saved_resp_req['error']}")
            if "status_code" in saved_resp_req: st.caption(f"Status: {saved_resp_req['status_code']}")
            if "text" in saved_resp_req: st.code(saved_resp_req['text'], language='text')
            return

        st.write("JSON Crudo de la Respuesta:")
        st.json(saved_resp_req)

        if PANDAS_AVAILABLE and pd:
            st.markdown("--- \n **Respuesta Tabular (si aplica):**")

            if isinstance(saved_resp_req, list) and saved_resp_req and all(isinstance(i, dict) for i in saved_resp_req):
                df_display_list_req = []
                for item_req in saved_resp_req:
                    row_req = {}
                    for k_req, v_req in item_req.items():
                        if isinstance(v_req, (dict, list)) and v_req:
                            row_req[k_req] = f"Ver {k_req.capitalize()}"
                        else:
                            row_req[k_req] = v_req
                    df_display_list_req.append(row_req)

                if df_display_list_req:
                    df_main_req = pd.DataFrame(df_display_list_req)

                    header_cols_req = st.columns(len(df_main_req.columns))
                    for col_i_req, col_n_req in enumerate(df_main_req.columns):
                        header_cols_req[col_i_req].markdown(f"**{col_n_req}**")
                    st.divider()

                    for row_i_req, original_row_data in enumerate(saved_resp_req):
                        row_c_req = st.columns(len(df_main_req.columns))
                        for col_i_req, col_n_req in enumerate(df_main_req.columns):
                            cell_v_req = original_row_data.get(col_n_req)

                            if isinstance(cell_v_req, (dict, list)) and cell_v_req:
                                btn_k_req = f"btn_det_{endpoint_id}_{row_i_req}_{col_n_req}{GLOBAL_SUFFIX}"
                                if row_c_req[col_i_req].button(f"Ver {col_n_req.capitalize()}", key=btn_k_req):
                                    trigger_detail_dialog(
                                        title=f"{col_n_req.capitalize()} (Fila {row_i_req+1})",
                                        data=cell_v_req,
                                        current_endpoint_id=endpoint_id,
                                        current_tab_name=tag_name_to_display
                                    )
                            else:
                                row_c_req[col_i_req].write(str(df_main_req.iloc[row_i_req, col_i_req]))
                        st.divider()

            elif isinstance(saved_resp_req, dict):
                st.write("Objeto Individual:")
                for k_o_req, v_o_req in saved_resp_req.items():
                    if isinstance(v_o_req, (dict, list)) and v_o_req:
                        if st.button(f"Ver Detalle de {k_o_req.capitalize()}", key=f"btn_obj_{endpoint_id}_{k_o_req}{GLOBAL_SUFFIX}"):
                            trigger_detail_dialog(
                                title=f"Detalle: {k_o_req.capitalize()}",
                                data=v_o_req,
                                current_endpoint_id=endpoint_id,
                                current_tab_name=tag_name_to_display
                            )
                    else:
                        st.text_input(f"{k_o_req.capitalize()}:", value=str(v_o_req), disabled=True, key=f"obj_val_{endpoint_id}_{k_o_req}{GLOBAL_SUFFIX}")
            else:
                st.caption("Formato de respuesta no es lista de objetos ni objeto individual para tabla.")
        elif not PANDAS_AVAILABLE:
             st.caption("Instala 'pandas' para ver respuestas tabulares mejoradas.")