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
import docker
from datetime import datetime

# Initialize Docker client
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

st.title("🐳 Docker Container Manager")

# Get all containers
try:
    all_containers = client.containers.list(all=True)
except Exception as e:
    st.error(f"Failed to list containers: {e}")
    st.stop()

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
                st.write(f"**Image:** {container.image.tags[0] if container.image.tags else container.image.short_id}")
                st.write(f"**Status:** {container.status}")
                
                # Ports
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                if ports:
                    port_mapping = []
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                port_mapping.append(f"{binding['HostIp']}:{binding['HostPort']} -> {container_port}")
                        else:
                            port_mapping.append(f"{container_port} (not published)")
                    st.write(f"**Ports:** {', '.join(port_mapping)}")
                
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
                st.write(f"**Image:** {container.image.tags[0] if container.image.tags else container.image.short_id}")
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

