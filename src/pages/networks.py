"""
Page for managing Docker networks

Features:
- List all networks with details (name, driver, scope, subnet, gateway)
- Show which containers are connected to each network
- Create new networks with custom configuration
- Remove unused networks
- Connect/disconnect containers to/from networks
- Inspect network details
- Prune unused networks

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

st.title("🌐 Docker Network Manager")


# Get all networks
try:
    networks = client.networks.list()
except Exception as e:
    st.error(f"Failed to list networks: {e}")
    st.stop()

# Get all containers to check network connections
try:
    all_containers = client.containers.list(all=True)
except Exception as e:
    st.error(f"Failed to list containers: {e}")
    all_containers = []

# Build a map of networks to containers
network_usage = {}
for container in all_containers:
    container_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
    for network_name, network_info in container_networks.items():
        if network_name not in network_usage:
            network_usage[network_name] = []
        network_usage[network_name].append({
            'name': container.name,
            'id': container.short_id,
            'status': container.status,
            'ipv4_address': network_info.get('IPAddress', 'N/A'),
            'ipv6_address': network_info.get('GlobalIPv6Address', 'N/A')
        })


# Information section
with st.expander("ℹ️ About Docker Networks"):
    st.markdown("""
    ### Docker Networks
    
    Docker networks enable containers to communicate with each other and with external networks.
    
    **Network Drivers:**
    - **bridge**: Default network driver. Containers on the same bridge network can communicate.
    - **host**: Removes network isolation, container uses the host's network directly.
    - **overlay**: Enables swarm services to communicate across multiple Docker daemon hosts.
    - **macvlan**: Assigns a MAC address to a container, making it appear as a physical device.
    - **none**: Disables all networking for the container.
    
    **Network Scopes:**
    - **local**: Network is only available on this Docker daemon host.
    - **swarm**: Network spans across all nodes in a Docker Swarm.
    - **global**: Network is available across all nodes.
    
    **Best Practices:**
    - Use custom bridge networks instead of the default bridge for better isolation
    - Assign meaningful names to networks for easier management
    - Use network aliases for service discovery
    - Regularly prune unused networks to keep your environment clean
    - Use overlay networks for multi-host communication in Swarm mode
    """)


# Create new network section
st.header("➕ Create New Network")
with st.expander("Create a new network", expanded=False):
    st.markdown("""
    **Quick Guide:**
    - **Network Name**: Give your network a descriptive name (e.g., `backend-network`, `frontend-net`).
    - **Driver**: Choose the network driver based on your use case. Use `bridge` for most single-host scenarios.
    - **Subnet**: Optional CIDR block for the network (e.g., `172.20.0.0/16`).
    - **Gateway**: Optional gateway IP address (e.g., `172.20.0.1`).
    - **Labels**: Metadata tags to organize networks (e.g., `environment=production`, `app=web`).
    - **Internal**: If enabled, restricts external access to the network.
    - **Attachable**: Allows standalone containers to attach to the network (useful for overlay networks).
    """)
    
    with st.form("create_network_form"):
        network_name = st.text_input("Network Name", placeholder="my-network")
        
        col1, col2 = st.columns(2)
        with col1:
            driver = st.selectbox("Driver", ["bridge", "host", "overlay", "macvlan", "none"], index=0)
        with col2:
            internal = st.checkbox("Internal Network", value=False, 
                                  help="Restrict external access to the network")
        
        # Advanced options
        with st.expander("Advanced Options"):
            enable_ipv6 = st.checkbox("Enable IPv6", value=False)
            attachable = st.checkbox("Attachable", value=False,
                                   help="Allow standalone containers to attach to this network")
            
            subnet = st.text_input("Subnet (CIDR)", placeholder="172.20.0.0/16",
                                  help="Example: 172.20.0.0/16")
            gateway = st.text_input("Gateway", placeholder="172.20.0.1",
                                   help="Example: 172.20.0.1")
            ip_range = st.text_input("IP Range (CIDR)", placeholder="172.20.10.0/24",
                                    help="Allocate container IPs from a sub-range")
            
            # Labels
            st.subheader("Labels")
            num_labels = st.number_input("Number of labels", min_value=0, max_value=10, value=0, step=1)
            labels = {}
            for i in range(int(num_labels)):
                col1, col2 = st.columns(2)
                with col1:
                    key = st.text_input(f"Label Key {i+1}", key=f"label_key_{i}")
                with col2:
                    value = st.text_input(f"Label Value {i+1}", key=f"label_value_{i}")
                if key:
                    labels[key] = value
        
        submit_create = st.form_submit_button("Create Network", use_container_width=True)
        
        if submit_create:
            if not network_name:
                st.error("Network name is required!")
            else:
                try:
                    # Build IPAM config
                    ipam_config = None
                    if subnet or gateway or ip_range:
                        ipam_pool = {}
                        if subnet:
                            ipam_pool['Subnet'] = subnet
                        if gateway:
                            ipam_pool['Gateway'] = gateway
                        if ip_range:
                            ipam_pool['IPRange'] = ip_range
                        
                        ipam_config = docker.types.IPAMConfig(
                            pool_configs=[docker.types.IPAMPool(**ipam_pool)]
                        )
                    
                    # Create the network
                    network = client.networks.create(
                        name=network_name,
                        driver=driver,
                        options={},
                        ipam=ipam_config,
                        internal=internal,
                        labels=labels if labels else None,
                        enable_ipv6=enable_ipv6,
                        attachable=attachable
                    )
                    st.success(f"✅ Network '{network_name}' created successfully!")
                    st.rerun()
                except docker.errors.APIError as e:
                    st.error(f"Failed to create network: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")


st.divider()

# List existing networks
st.header("📋 Existing Networks")

# Add filter options
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    show_system = st.checkbox("Show system networks", value=True, 
                             help="Show built-in Docker networks (bridge, host, none)")
with filter_col2:
    search_filter = st.text_input("🔍 Filter by name", placeholder="Search networks...")

# Filter networks
filtered_networks = []
for network in networks:
    # Filter system networks
    if not show_system and network.name in ['bridge', 'host', 'none']:
        continue
    
    # Filter by search term
    if search_filter and search_filter.lower() not in network.name.lower():
        continue
    
    filtered_networks.append(network)

st.write(f"**Total networks:** {len(filtered_networks)}")

# Display networks
for network in sorted(filtered_networks, key=lambda n: n.name):
    network.reload()
    attrs = network.attrs
    
    # Determine if network is in use
    connected_containers = network_usage.get(network.name, [])
    in_use = len(connected_containers) > 0
    
    # Network header with name and status
    status_icon = "🟢" if in_use else "⚪"
    is_system = network.name in ['bridge', 'host', 'none']
    system_badge = " 🔒" if is_system else ""
    
    with st.expander(f"{status_icon} **{network.name}** {system_badge}", expanded=False):
        # Network details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Network Information**")
            st.markdown(f"""| Key | Value |
|---|---|   
| Name | {network.name} |
| ID | {network.id[:12]} |
| Driver | {attrs.get('Driver', 'N/A')} |
| Scope | {attrs.get('Scope', 'N/A')} |
| Internal | {attrs.get('Internal', False)} |
| Attachable | {attrs.get('Attachable', False)} |
| IPv6 Enabled | {attrs.get('EnableIPv6', False)} |""")

            # Created date
            created = attrs.get('Created', '')
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    st.text(f"Created: {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    st.text(f"Created: {created}")
        
        with col2:
            st.markdown("**IPAM Configuration**")
            ipam_config = attrs.get('IPAM', {}).get('Config', [])
            if ipam_config:
                for idx, config in enumerate(ipam_config):
                    st.text(f"Subnet: {config.get('Subnet', 'N/A')}")
                    st.text(f"Gateway: {config.get('Gateway', 'N/A')}")
                    if config.get('IPRange'):
                        st.text(f"IP Range: {config.get('IPRange')}")
            else:
                st.text("No IPAM configuration")
        
        # Labels
        labels = attrs.get('Labels')
        if labels:
            st.markdown("**Labels:**")
            for key, value in labels.items():
                st.code(f"{key}: {value}", language=None)
        
        # Connected containers
        if connected_containers:
            st.markdown(f"**Connected Containers ({len(connected_containers)}):**")
            for container_info in connected_containers:
                status_color = "🟢" if container_info['status'] == 'running' else "🔴"
                ipv4 = container_info['ipv4_address']
                ipv6 = container_info['ipv6_address']
                ip_display = f"IPv4: {ipv4}" if ipv4 != 'N/A' else ""
                if ipv6 != 'N/A':
                    ip_display += f", IPv6: {ipv6}" if ip_display else f"IPv6: {ipv6}"
                
                st.text(f"{status_color} {container_info['name']} ({container_info['id']}) - {ip_display}")
        else:
            st.info("No containers connected to this network")
        
        # Network actions
        st.markdown("**Actions:**")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        # Connect container to network
        with action_col1:
            if st.button("🔗 Connect Container", key=f"connect_{network.id}", use_container_width=True):
                st.session_state[f'show_connect_{network.id}'] = True
        
        # Disconnect container from network
        with action_col2:
            if connected_containers:
                if st.button("🔓 Disconnect Container", key=f"disconnect_{network.id}", use_container_width=True):
                    st.session_state[f'show_disconnect_{network.id}'] = True
        
        # Remove network (only if not in use and not system network)
        with action_col3:
            if not in_use and not is_system:
                if st.button("🗑️ Remove Network", key=f"remove_{network.id}", use_container_width=True):
                    try:
                        network.remove()
                        st.success(f"Network '{network.name}' removed successfully!")
                        st.rerun()
                    except docker.errors.APIError as e:
                        st.error(f"Failed to remove network: {e}")
            elif is_system:
                st.button("🗑️ Remove Network", key=f"remove_{network.id}", disabled=True, 
                         use_container_width=True, help="System networks cannot be removed")
            else:
                st.button("🗑️ Remove Network", key=f"remove_{network.id}", disabled=True,
                         use_container_width=True, help="Disconnect all containers first")
        
        # Connect container dialog
        if st.session_state.get(f'show_connect_{network.id}', False):
            with st.form(f"connect_form_{network.id}"):
                st.subheader("Connect Container to Network")
                
                # Get containers not already connected
                connected_ids = [c['id'] for c in connected_containers]
                available_containers = [c for c in all_containers if c.short_id not in connected_ids]
                
                if not available_containers:
                    st.warning("All containers are already connected to this network")
                else:
                    container_options = {f"{c.name} ({c.short_id})": c for c in available_containers}
                    selected_container = st.selectbox("Select container", list(container_options.keys()))
                    
                    # Advanced options
                    with st.expander("Advanced Options"):
                        aliases = st.text_input("Network Aliases (comma-separated)", 
                                              help="Alternative names for this container on the network")
                        ipv4_address = st.text_input("IPv4 Address", 
                                                   help="Optional static IPv4 address")
                        ipv6_address = st.text_input("IPv6 Address",
                                                   help="Optional static IPv6 address")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Connect", use_container_width=True):
                            try:
                                container = container_options[selected_container]
                                
                                # Build connection parameters
                                kwargs = {}
                                if aliases:
                                    kwargs['aliases'] = [a.strip() for a in aliases.split(',') if a.strip()]
                                if ipv4_address:
                                    kwargs['ipv4_address'] = ipv4_address
                                if ipv6_address:
                                    kwargs['ipv6_address'] = ipv6_address
                                
                                network.connect(container, **kwargs)
                                st.success(f"Container '{container.name}' connected to network '{network.name}'!")
                                del st.session_state[f'show_connect_{network.id}']
                                st.rerun()
                            except docker.errors.APIError as e:
                                st.error(f"Failed to connect container: {e}")
                    
                    with col2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            del st.session_state[f'show_connect_{network.id}']
                            st.rerun()
        
        # Disconnect container dialog
        if st.session_state.get(f'show_disconnect_{network.id}', False):
            with st.form(f"disconnect_form_{network.id}"):
                st.subheader("Disconnect Container from Network")
                
                container_options = {f"{c['name']} ({c['id']})": c for c in connected_containers}
                selected_container = st.selectbox("Select container to disconnect", list(container_options.keys()))
                
                force = st.checkbox("Force disconnect", value=False,
                                  help="Force disconnection even if container is running")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Disconnect", use_container_width=True):
                        try:
                            container_info = container_options[selected_container]
                            container = client.containers.get(container_info['id'])
                            network.disconnect(container, force=force)
                            st.success(f"Container '{container_info['name']}' disconnected from network '{network.name}'!")
                            del st.session_state[f'show_disconnect_{network.id}']
                            st.rerun()
                        except docker.errors.APIError as e:
                            st.error(f"Failed to disconnect container: {e}")
                
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        del st.session_state[f'show_disconnect_{network.id}']
                        st.rerun()
        
        # Full inspect data
        with st.expander("🔍 Full Inspection Data (JSON)"):
            st.json(attrs)


# Prune unused networks
st.divider()
st.header("🧹 Cleanup")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("""
    **Prune Unused Networks**: Remove all networks that are not currently in use by any container.
    This helps free up resources and keep your Docker environment clean.
    """)
with col2:
    if st.button("🧹 Prune Unused Networks", use_container_width=True):
        try:
            result = client.networks.prune()
            deleted_networks = result.get('NetworksDeleted', [])
            if deleted_networks:
                st.success(f"✅ Pruned {len(deleted_networks)} unused network(s)!")
                for net_name in deleted_networks:
                    if net_name:
                        st.text(f"  - {net_name}")
                st.rerun()
            else:
                st.info("No unused networks to prune")
        except docker.errors.APIError as e:
            st.error(f"Failed to prune networks: {e}")
