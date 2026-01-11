"""
Page for editing Docker container configuration

Features:
- View and edit container configuration
- Some options are only available when container is stopped (e.g., resource limits, restart policy)
- Options available while running: container name, environment variables (requires restart)
- Real-time validation and error handling
"""

import streamlit as st
import docker
import json

# Initialize Docker client
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

st.title("⚙️ Docker Container Configuration Editor")

# Get all containers
try:
    all_containers = client.containers.list(all=True)
except Exception as e:
    st.error(f"Failed to list containers: {e}")
    st.stop()

if not all_containers:
    st.warning("No containers found. Please create a container first.")
    st.stop()

# Container selection
container_options = {f"{c.name} ({c.short_id}) - {c.status}": c for c in all_containers}
selected_name = st.selectbox("Select a container to configure:", list(container_options.keys()))
container = container_options[selected_name]

# Refresh container data
container.reload()

st.divider()

# Display current status
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", container.status)
with col2:
    st.metric("Image", container.image.tags[0] if container.image.tags else container.image.short_id)
with col3:
    st.metric("ID", container.short_id)

is_running = container.status == 'running'

if is_running:
    st.info("ℹ️ Some configuration options are only available when the container is stopped. Stop the container to access all settings.")
else:
    st.success("✅ Container is stopped. All configuration options are available.")

st.divider()

# Tabs for different configuration categories
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏷️ Basic", "🔧 Resources", "🔄 Restart Policy", "🌐 Network", "📊 Advanced"])

# TAB 1: Basic Configuration
with tab1:
    st.subheader("Basic Configuration")
    
    # Container Name (available while running, but requires recreation)
    st.write("**Container Name**")
    current_name = container.name
    new_name = st.text_input("Name:", value=current_name, key="container_name")
    
    if new_name != current_name:
        if st.button("Rename Container", key="rename_btn"):
            try:
                container.rename(new_name)
                st.success(f"Container renamed from '{current_name}' to '{new_name}'")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to rename container: {e}")
    
    st.divider()
    
    # Environment Variables
    st.write("**Environment Variables**")
    env_vars = container.attrs.get('Config', {}).get('Env', [])
    
    if env_vars:
        st.info("Current environment variables (read-only - requires container recreation to modify):")
        for env in env_vars:
            st.code(env)
    else:
        st.info("No environment variables set")
    
    st.divider()
    
    # Labels
    st.write("**Labels**")
    labels = container.labels
    if labels:
        st.json(labels)
    else:
        st.info("No labels set")

# TAB 2: Resource Limits
with tab2:
    st.subheader("Resource Limits")
    
    if is_running:
        st.warning("⚠️ Container must be stopped to modify resource limits")
    
    host_config = container.attrs.get('HostConfig', {})
    
    # CPU configuration
    st.write("**CPU Configuration**")
    
    current_cpu_shares = host_config.get('CpuShares', 0)
    current_cpu_period = host_config.get('CpuPeriod', 0)
    current_cpu_quota = host_config.get('CpuQuota', 0)
    current_cpuset_cpus = host_config.get('CpusetCpus', '')
    
    col1, col2 = st.columns(2)
    with col1:
        cpu_shares = st.number_input("CPU Shares (0 = default)", 
                                     min_value=0, max_value=1024, 
                                     value=current_cpu_shares,
                                     disabled=is_running,
                                     help="Relative CPU weight (0-1024)")
    with col2:
        cpuset_cpus = st.text_input("CPU Set (e.g., 0-3, 0,1)", 
                                    value=current_cpuset_cpus,
                                    disabled=is_running,
                                    help="Which CPUs to use")
    
    st.divider()
    
    # Memory configuration
    st.write("**Memory Configuration**")
    
    current_memory = host_config.get('Memory', 0)
    current_memory_swap = host_config.get('MemorySwap', 0)
    current_memory_reservation = host_config.get('MemoryReservation', 0)
    
    col1, col2 = st.columns(2)
    with col1:
        memory_limit = st.number_input("Memory Limit (MB, 0 = unlimited)", 
                                       min_value=0, max_value=1048576,
                                       value=current_memory // (1024*1024) if current_memory > 0 else 0,
                                       disabled=is_running,
                                       help="Maximum memory the container can use")
    with col2:
        memory_reservation = st.number_input("Memory Reservation (MB, 0 = none)", 
                                             min_value=0, max_value=1048576,
                                             value=current_memory_reservation // (1024*1024) if current_memory_reservation > 0 else 0,
                                             disabled=is_running,
                                             help="Soft memory limit")
    
    memory_swap = st.number_input("Memory + Swap (MB, 0 = unlimited, -1 = disable swap)", 
                                  min_value=-1, max_value=1048576,
                                  value=current_memory_swap // (1024*1024) if current_memory_swap > 0 else 0,
                                  disabled=is_running,
                                  help="Total memory + swap limit")
    
    if not is_running:
        if st.button("💾 Apply Resource Limits", key="apply_resources"):
            st.warning("⚠️ Applying resource limits requires container recreation. This feature creates a new container with the same configuration but different limits.")
            st.info("To implement: This would require stopping the container, getting its full configuration, creating a new container with updated limits, and removing the old one.")

# TAB 3: Restart Policy
with tab3:
    st.subheader("Restart Policy")
    
    if is_running:
        st.warning("⚠️ Container must be stopped to modify restart policy")
    
    current_restart_policy = host_config.get('RestartPolicy', {})
    current_policy_name = current_restart_policy.get('Name', 'no')
    current_max_retry = current_restart_policy.get('MaximumRetryCount', 0)
    
    st.write(f"**Current Policy:** `{current_policy_name}`")
    if current_policy_name == 'on-failure':
        st.write(f"**Max Retry Count:** {current_max_retry}")
    
    st.divider()
    
    restart_options = {
        "no": "No - Do not automatically restart",
        "always": "Always - Always restart the container",
        "unless-stopped": "Unless Stopped - Restart unless explicitly stopped",
        "on-failure": "On Failure - Restart only if container exits with error"
    }
    
    selected_policy = st.selectbox("Select Restart Policy:",
                                   options=list(restart_options.keys()),
                                   format_func=lambda x: restart_options[x],
                                   index=list(restart_options.keys()).index(current_policy_name) if current_policy_name in restart_options else 0,
                                   disabled=is_running)
    
    max_retry_count = 0
    if selected_policy == "on-failure":
        max_retry_count = st.number_input("Maximum Retry Count:",
                                          min_value=0, max_value=100,
                                          value=current_max_retry if current_policy_name == 'on-failure' else 3,
                                          disabled=is_running,
                                          help="Number of times to retry restarting")
    
    if not is_running and selected_policy != current_policy_name:
        if st.button("💾 Apply Restart Policy", key="apply_restart"):
            try:
                # Update restart policy
                policy_dict = {"Name": selected_policy}
                if selected_policy == "on-failure":
                    policy_dict["MaximumRetryCount"] = max_retry_count
                
                container.update(restart_policy=policy_dict)
                st.success(f"Restart policy updated to '{selected_policy}'")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update restart policy: {e}")

# TAB 4: Network Configuration
with tab4:
    st.subheader("Network Configuration")
    
    # Display current network settings
    network_settings = container.attrs.get('NetworkSettings', {})
    networks = network_settings.get('Networks', {})
    
    st.write("**Connected Networks:**")
    if networks:
        for network_name, network_data in networks.items():
            with st.expander(f"📡 {network_name}", expanded=True):
                st.write(f"**IP Address:** {network_data.get('IPAddress', 'N/A')}")
                st.write(f"**Gateway:** {network_data.get('Gateway', 'N/A')}")
                st.write(f"**MAC Address:** {network_data.get('MacAddress', 'N/A')}")
                
                # Option to disconnect (only when stopped)
                if not is_running:
                    if st.button(f"Disconnect from {network_name}", key=f"disconnect_{network_name}"):
                        try:
                            network = client.networks.get(network_name)
                            network.disconnect(container)
                            st.success(f"Disconnected from {network_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to disconnect: {e}")
    else:
        st.info("Not connected to any networks")
    
    st.divider()
    
    # Port mappings (read-only)
    st.write("**Port Mappings:**")
    ports = network_settings.get('Ports', {})
    if ports:
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    st.code(f"{binding['HostIp']}:{binding['HostPort']} → {container_port}")
            else:
                st.code(f"{container_port} (not published)")
    else:
        st.info("No port mappings configured")
    
    st.info("💡 Port mappings can only be changed during container creation.")
    
    st.divider()
    
    # Connect to additional network (only when stopped)
    if not is_running:
        st.write("**Connect to Network:**")
        try:
            available_networks = client.networks.list()
            network_names = [n.name for n in available_networks if n.name not in networks]
            
            if network_names:
                selected_network = st.selectbox("Select network to connect:", network_names)
                
                if st.button("Connect to Network", key="connect_network"):
                    try:
                        network = client.networks.get(selected_network)
                        network.connect(container)
                        st.success(f"Connected to {selected_network}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to connect to network: {e}")
            else:
                st.info("Already connected to all available networks")
        except Exception as e:
            st.error(f"Failed to list networks: {e}")
    else:
        st.warning("⚠️ Stop the container to connect to additional networks")

# TAB 5: Advanced Configuration
with tab5:
    st.subheader("Advanced Configuration")
    
    # Display full container configuration
    st.write("**Full Container Configuration (Read-Only)**")
    
    if st.checkbox("Show raw configuration JSON", key="show_config"):
        st.json(container.attrs)
    
    st.divider()
    
    # Logging configuration
    st.write("**Logging Configuration**")
    log_config = host_config.get('LogConfig', {})
    st.write(f"**Driver:** {log_config.get('Type', 'N/A')}")
    log_opts = log_config.get('Config', {})
    if log_opts:
        st.write("**Options:**")
        st.json(log_opts)
    
    st.divider()
    
    # Privileged mode and capabilities
    st.write("**Security Settings**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Privileged Mode:** {host_config.get('Privileged', False)}")
        st.write(f"**Read-Only Filesystem:** {host_config.get('ReadonlyRootfs', False)}")
    with col2:
        cap_add = host_config.get('CapAdd', [])
        cap_drop = host_config.get('CapDrop', [])
        if cap_add:
            st.write(f"**Capabilities Added:** {', '.join(cap_add)}")
        if cap_drop:
            st.write(f"**Capabilities Dropped:** {', '.join(cap_drop)}")

st.divider()

# Container control buttons
st.subheader("Container Controls")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if is_running:
        if st.button("⏹️ Stop Container", type="primary", key="stop_container"):
            try:
                container.stop()
                st.success("Container stopped")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to stop container: {e}")
    else:
        if st.button("▶️ Start Container", type="primary", key="start_container"):
            try:
                container.start()
                st.success("Container started")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start container: {e}")

with col2:
    if st.button("🔄 Restart Container", disabled=not is_running, key="restart_container"):
        try:
            container.restart()
            st.success("Container restarted")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to restart container: {e}")

with col3:
    if st.button("🔄 Refresh Data", key="refresh_data"):
        st.rerun()

with col4:
    if not is_running:
        if st.button("🗑️ Remove Container", type="secondary", key="remove_container"):
            if "confirm_remove_config" not in st.session_state:
                st.session_state.confirm_remove_config = False
            
            if not st.session_state.confirm_remove_config:
                st.session_state.confirm_remove_config = True
                st.warning("⚠️ Click Remove Container again to confirm deletion")
                st.rerun()
            else:
                try:
                    container.remove()
                    st.success("Container removed")
                    st.session_state.confirm_remove_config = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to remove container: {e}")
                    st.session_state.confirm_remove_config = False
