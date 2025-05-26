import streamlit as st
from app_config import GLOBAL_SUFFIX, PANDAS_AVAILABLE, pd


def render_detail_dialog():
    if st.session_state.get('show_detail_dialog', False):
        with st.container():
            st.markdown("---")
            st.subheader(f"Detalle: {st.session_state.get('dialog_title', 'Detalles')}")
            st.caption("*(Vista de detalle)*")

            data_to_show = st.session_state.get('dialog_data')

            if PANDAS_AVAILABLE and pd:
                try:
                    if isinstance(data_to_show, list) and data_to_show and all(isinstance(i, dict) for i in data_to_show):
                        st.dataframe(pd.DataFrame(data_to_show), use_container_width=True)
                    elif isinstance(data_to_show, dict):
                        st.dataframe(pd.json_normalize(data_to_show), use_container_width=True)
                    else:
                        st.json(data_to_show)
                except Exception as e_df:
                    st.json(data_to_show)
                    st.caption(f"No se pudo mostrar como tabla: {e_df}")
            else:
                st.json(data_to_show)

            st.markdown("---")
            if st.button("Cerrar Detalles", key=f"close_simple_dialog_btn{GLOBAL_SUFFIX}"):
                st.session_state.show_detail_dialog = False
                st.rerun()
        st.stop()

def trigger_detail_dialog(title, data, current_endpoint_id, current_tab_name):
    st.session_state.dialog_title = title
    st.session_state.dialog_data = data
    st.session_state.show_detail_dialog = True
    st.session_state.active_expander_id = current_endpoint_id
    st.session_state.active_tab_name = current_tab_name
    st.rerun()