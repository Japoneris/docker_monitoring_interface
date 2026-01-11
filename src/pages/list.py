"""
Page listing containers 

- running containers
    - can make them stop
    - can restart them
    
- stopped containes 
    - let them start
    - can remove them

    
For each, provide ID, name, image, status, ports, ...
Some info are only avaialable on demand (add a button to fetch more details)

"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import get_docker_client, get_containers, get_container_image_name, get_container_ports_display

# Initialize Docker client
client = get_docker_client()

st.title("🐳 Docker Container Manager")

# Get all containers
all_containers = get_containers(client, all_containers=True)

# Separate running and stopped containers
running_containers = [c for c in all_containers if c.status == 'running']
stopped_containers = [c for c in all_containers if c.status != 'running']

# Running Containers Section
st.header("🟢 Running Containers")
if running_containers:
    for container in running_containers:
        with st.expander(f"**{container.name}** ({container.short_id})", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**ID:** `{container.short_id}`")
                st.write(f"**Name:** {container.name}")
                st.write(f"**Image:** {get_container_image_name(container)}")
                st.write(f"**Status:** {container.status}")
                
                # Ports
                ports_display = get_container_ports_display(container)
                st.write(f"**Ports:** {ports_display}")
                
                # Show details button
                if st.button(f"📋 Show More Details", key=f"details_{container.id}"):
                    st.json({
                        "Created": container.attrs['Created'],
                        "State": container.attrs['State'],
                        "NetworkSettings": container.attrs['NetworkSettings'],
                        "Mounts": container.attrs['Mounts']
                    })
            
            with col2:
                if st.button("⏹️ Stop", key=f"stop_{container.id}", type="primary"):
                    try:
                        container.stop()
                        st.success(f"Stopped {container.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                if st.button("🔄 Restart", key=f"restart_{container.id}"):
                    try:
                        container.restart()
                        st.success(f"Restarted {container.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
else:
    st.info("No running containers found")

# Stopped Containers Section
st.header("⚪ Stopped Containers")
if stopped_containers:
    for container in stopped_containers:
        with st.expander(f"**{container.name}** ({container.short_id}) - {container.status}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**ID:** `{container.short_id}`")
                st.write(f"**Name:** {container.name}")
                st.write(f"**Image:** {get_container_image_name(container)}")
                st.write(f"**Status:** {container.status}")
                
                # Show details button
                if st.button(f"📋 Show More Details", key=f"details_{container.id}"):
                    st.json({
                        "Created": container.attrs['Created'],
                        "State": container.attrs['State'],
                        "Mounts": container.attrs['Mounts']
                    })
            
            with col2:
                if st.button("▶️ Start", key=f"start_{container.id}", type="primary"):
                    try:
                        container.start()
                        st.success(f"Started {container.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                if st.button("🗑️ Remove", key=f"remove_{container.id}", type="secondary"):
                    # Confirmation dialog
                    if f"confirm_remove_{container.id}" not in st.session_state:
                        st.session_state[f"confirm_remove_{container.id}"] = False
                    
                    if not st.session_state[f"confirm_remove_{container.id}"]:
                        st.session_state[f"confirm_remove_{container.id}"] = True
                        st.rerun()
                    else:
                        try:
                            container.remove()
                            st.success(f"Removed {container.name}")
                            st.session_state[f"confirm_remove_{container.id}"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                            st.session_state[f"confirm_remove_{container.id}"] = False
                
                # Show confirmation warning if in confirmation state
                if st.session_state.get(f"confirm_remove_{container.id}", False):
                    st.warning("⚠️ Click Remove again to confirm deletion")
else:
    st.info("No stopped containers found")

