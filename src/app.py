import streamlit as st


##############
# Load pages #
##############


with st.sidebar:
    if st.button("🔄 Refresh page", use_container_width=True):
        st.rerun()

pages = [
    st.Page("pages/list.py", title="List existing containers", icon=":material/folder:", url_path="list"),
    st.Page("pages/config.py", title="Edit container configuration", icon=":material/settings:", url_path="config"),
    st.Page("pages/navigate.py", title="Navigate folder, upload/download files", icon=":material/folder:", url_path="navigate"),
    st.Page("pages/shell.py", title="Run shell commands in container", icon=":material/terminal:", url_path="shell"),
    st.Page("pages/logs.py", title="View container logs", icon=":material/description:", url_path="logs"),
    st.Page("pages/volumes.py", title="Manage Docker volumes", icon=":material/storage:", url_path="volumes"),
    st.Page("pages/mounts.py", title="Manage mounts and binds", icon=":material/link:", url_path="mounts"),
    st.Page("pages/networks.py", title="Manage Docker networks", icon=":material/wifi:", url_path="networks"),
 ] 
    
pg = st.navigation(pages)
pg.run()

