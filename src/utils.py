"""
Shared utilities for Docker Monitoring Lab

This module provides common functions used across different pages to reduce code duplication.
"""

import streamlit as st
import docker
from typing import Optional, List, Dict, Any


# Status emojis for containers and other resources
STATUS_EMOJIS = {
    'running': '🟢',
    'exited': '🔴',
    'paused': '⏸️',
    'restarting': '🔄',
    'created': '🔵',
    'dead': '💀',
    'removing': '🗑️'
}


def get_docker_client() -> docker.DockerClient:
    """
    Initialize and return Docker client with error handling.
    
    Returns:
        docker.DockerClient: Connected Docker client
        
    Raises:
        Stops Streamlit execution if connection fails
    """
    try:
        client = docker.from_env()
        return client
    except Exception as e:
        st.error(f"Failed to connect to Docker: {e}")
        st.stop()


def get_containers(client: docker.DockerClient, all_containers: bool = False) -> List[docker.models.containers.Container]:
    """
    Get list of containers with error handling.
    
    Args:
        client: Docker client instance
        all_containers: If True, return all containers (including stopped), else only running
        
    Returns:
        List of Container objects
        
    Raises:
        Stops Streamlit execution if listing fails
    """
    try:
        containers = client.containers.list(all=all_containers)
        return containers
    except Exception as e:
        st.error(f"Failed to list containers: {e}")
        st.stop()


def create_container_selector(
    containers: List[docker.models.containers.Container],
    label: str = "Select a container:",
    show_status: bool = True,
    show_emoji: bool = True,
    key: Optional[str] = None,
    help_text: Optional[str] = None
) -> docker.models.containers.Container:
    """
    Create a container selection dropdown and return the selected container.
    
    Args:
        containers: List of containers to choose from
        label: Label for the selectbox
        show_status: Whether to show container status in the dropdown
        show_emoji: Whether to show status emoji in the dropdown
        key: Unique key for the selectbox widget
        help_text: Optional help text for the selectbox
        
    Returns:
        Selected Container object
        
    Raises:
        Stops Streamlit execution if no containers are available
    """
    if not containers:
        st.warning("No containers found. Please create/start a container first.")
        st.stop()
    
    # Build container options dictionary
    container_dict = {}
    for c in containers:
        # Build display name
        parts = []
        
        if show_emoji:
            emoji = STATUS_EMOJIS.get(c.status, '⚪')
            parts.append(emoji)
        
        if show_status:
            parts.append(f"[{c.status}]")
        
        parts.append(f"{c.name} ({c.short_id})")
        
        display_name = " ".join(parts)
        container_dict[display_name] = c
    
    # Create selectbox
    selected_name = st.selectbox(
        label,
        options=list(container_dict.keys()),
        key=key,
        help=help_text
    )
    
    return container_dict[selected_name]


def get_container_image_name(container: docker.models.containers.Container) -> str:
    """
    Get a readable image name from a container.
    
    Args:
        container: Docker container object
        
    Returns:
        Image name (tag if available, otherwise short ID)
    """
    return container.image.tags[0] if container.image.tags else container.image.short_id


def display_container_info(container: docker.models.containers.Container, cols: int = 4) -> None:
    """
    Display basic container information in columns.
    
    Args:
        container: Docker container object
        cols: Number of columns to use (default: 4)
    """
    columns = st.columns(cols)
    
    with columns[0]:
        st.metric("Name", container.name)
    
    with columns[1]:
        st.metric("Status", container.status)
    
    with columns[2]:
        st.metric("Image", get_container_image_name(container))
    
    if cols >= 4:
        with columns[3]:
            st.metric("ID", container.short_id)


def get_container_ports_display(container: docker.models.containers.Container) -> str:
    """
    Get formatted port mappings for a container.
    
    Args:
        container: Docker container object
        
    Returns:
        Formatted string of port mappings
    """
    ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
    if not ports:
        return "No ports exposed"
    
    port_mapping = []
    for container_port, host_bindings in ports.items():
        if host_bindings:
            for binding in host_bindings:
                port_mapping.append(f"{binding['HostIp']}:{binding['HostPort']} -> {container_port}")
        else:
            port_mapping.append(f"{container_port} (not published)")
    
    return ', '.join(port_mapping) if port_mapping else "No ports published"


def safe_execute(func, error_message: str = "An error occurred", stop_on_error: bool = False):
    """
    Execute a function with error handling.
    
    Args:
        func: Function to execute
        error_message: Message to display on error
        stop_on_error: Whether to stop Streamlit execution on error
        
    Returns:
        Result of func if successful, None if error occurred
    """
    try:
        return func()
    except Exception as e:
        st.error(f"{error_message}: {e}")
        if stop_on_error:
            st.stop()
        return None


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable format.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB", "512 MB")
    """
    if bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    value = float(bytes_value)
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    return f"{value:.2f} {units[unit_index]}"


def create_confirmation_button(
    label: str,
    key: str,
    on_confirm,
    warning_message: str = "Click again to confirm",
    button_type: str = "secondary"
) -> bool:
    """
    Create a two-step confirmation button.
    
    Args:
        label: Button label
        key: Unique key for the button
        on_confirm: Function to execute on confirmation
        warning_message: Message to show after first click
        button_type: Streamlit button type ("primary" or "secondary")
        
    Returns:
        True if action was confirmed and executed, False otherwise
    """
    confirm_key = f"confirm_{key}"
    
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    
    if st.button(label, key=key, type=button_type):
        if not st.session_state[confirm_key]:
            st.session_state[confirm_key] = True
            st.warning(f"⚠️ {warning_message}")
            return False
        else:
            try:
                on_confirm()
                st.session_state[confirm_key] = False
                return True
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state[confirm_key] = False
                return False
    
    return False


def get_volumes(client: docker.DockerClient) -> List[docker.models.volumes.Volume]:
    """
    Get list of volumes with error handling.
    
    Args:
        client: Docker client instance
        
    Returns:
        List of Volume objects
        
    Raises:
        Stops Streamlit execution if listing fails
    """
    try:
        volumes = client.volumes.list()
        return volumes
    except Exception as e:
        st.error(f"Failed to list volumes: {e}")
        st.stop()


def get_networks(client: docker.DockerClient) -> List[docker.models.networks.Network]:
    """
    Get list of networks with error handling.
    
    Args:
        client: Docker client instance
        
    Returns:
        List of Network objects
        
    Raises:
        Stops Streamlit execution if listing fails
    """
    try:
        networks = client.networks.list()
        return networks
    except Exception as e:
        st.error(f"Failed to list networks: {e}")
        st.stop()


def build_resource_usage_map(
    containers: List[docker.models.containers.Container],
    resource_type: str = 'volume'
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build a map of which containers use which resources (volumes or networks).
    
    Args:
        containers: List of containers
        resource_type: Type of resource ('volume' or 'network')
        
    Returns:
        Dictionary mapping resource names to list of container info dicts
    """
    usage_map = {}
    
    for container in containers:
        if resource_type == 'volume':
            mounts = container.attrs.get('Mounts', [])
            for mount in mounts:
                if mount.get('Type') == 'volume':
                    volume_name = mount.get('Name')
                    if volume_name:
                        if volume_name not in usage_map:
                            usage_map[volume_name] = []
                        usage_map[volume_name].append({
                            'name': container.name,
                            'id': container.short_id,
                            'status': container.status,
                            'destination': mount.get('Destination', 'N/A')
                        })
        
        elif resource_type == 'network':
            container_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            for network_name, network_info in container_networks.items():
                if network_name not in usage_map:
                    usage_map[network_name] = []
                usage_map[network_name].append({
                    'name': container.name,
                    'id': container.short_id,
                    'status': container.status,
                    'ipv4_address': network_info.get('IPAddress', 'N/A'),
                    'ipv6_address': network_info.get('GlobalIPv6Address', 'N/A')
                })
    
    return usage_map
