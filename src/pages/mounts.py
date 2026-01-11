"""
Page for managing Docker mounts and binds

Features:
- List all container mounts (volumes, bind mounts, tmpfs)
- Show mount details (type, source, destination, permissions)
- Filter by mount type
- View which containers use specific mounts
- Inspect mount configuration and options
- Manage bind mounts and understand their usage

"""

import streamlit as st
import docker
from datetime import datetime
import os

# Initialize Docker client
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

st.title("🔗 Docker Mounts & Binds Manager")

# Refresh button at the top
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Get all containers
try:
    all_containers = client.containers.list(all=True)
except Exception as e:
    st.error(f"Failed to list containers: {e}")
    st.stop()

# Collect all mounts from all containers
all_mounts = []
for container in all_containers:
    mounts = container.attrs.get('Mounts', [])
    for mount in mounts:
        mount_info = {
            'container_name': container.name,
            'container_id': container.short_id,
            'container_status': container.status,
            'type': mount.get('Type', 'unknown'),
            'source': mount.get('Source', 'N/A'),
            'destination': mount.get('Destination', 'N/A'),
            'mode': mount.get('Mode', 'N/A'),
            'rw': mount.get('RW', True),
            'propagation': mount.get('Propagation', 'N/A'),
            'name': mount.get('Name', 'N/A'),
            'driver': mount.get('Driver', 'N/A'),
        }
        all_mounts.append(mount_info)

# Information section
with st.expander("ℹ️ About Docker Mounts and Binds"):
    st.markdown("""
    ### Docker Mounts
    
    Docker supports several types of mounts to persist data and share files between the host and containers:
    
    **Mount Types:**
    
    1. **📦 Volume Mounts**
       - Managed by Docker in `/var/lib/docker/volumes/`
       - Best for production and persistent data
       - Can be shared between multiple containers
       - Easier to backup and migrate
       - Works on all platforms (Linux, Windows, Mac)
    
    2. **📁 Bind Mounts**
       - Direct mapping from host filesystem to container
       - Full control over exact host path
       - Useful for development (e.g., mounting source code)
       - Host-dependent and less portable
       - Can have performance issues on Docker Desktop (Mac/Windows)
    
    3. **💾 tmpfs Mounts** (Linux only)
       - Stored in host system's memory
       - Never written to host filesystem
       - Fast but temporary (lost when container stops)
       - Good for sensitive data that shouldn't persist
    
    **Mount Modes:**
    - **rw** (read-write): Container can read and modify files
    - **ro** (read-only): Container can only read files
    
    **Best Practices:**
    - Use **volumes** for database data and application state
    - Use **bind mounts** for development and configuration files
    - Use **tmpfs** for temporary data, caches, and secrets
    - Always specify `:ro` for read-only access when modification isn't needed
    - Use absolute paths for bind mounts
    """)

# Statistics
st.header("📊 Mount Statistics")
mount_types = {}
for mount in all_mounts:
    mount_type = mount['type']
    if mount_type not in mount_types:
        mount_types[mount_type] = 0
    mount_types[mount_type] += 1

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Mounts", len(all_mounts))
with col2:
    st.metric("Volume Mounts", mount_types.get('volume', 0))
with col3:
    st.metric("Bind Mounts", mount_types.get('bind', 0))
with col4:
    st.metric("tmpfs Mounts", mount_types.get('tmpfs', 0))

# Filter section
st.header("🔍 Filter Mounts")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    filter_type = st.selectbox(
        "Mount Type",
        ["All"] + list(set([m['type'] for m in all_mounts])),
        index=0
    )

with filter_col2:
    filter_container = st.selectbox(
        "Container",
        ["All"] + sorted(list(set([m['container_name'] for m in all_mounts]))),
        index=0
    )

with filter_col3:
    filter_mode = st.selectbox(
        "Access Mode",
        ["All", "Read-Write", "Read-Only"],
        index=0
    )

# Apply filters
filtered_mounts = all_mounts

if filter_type != "All":
    filtered_mounts = [m for m in filtered_mounts if m['type'] == filter_type]

if filter_container != "All":
    filtered_mounts = [m for m in filtered_mounts if m['container_name'] == filter_container]

if filter_mode == "Read-Write":
    filtered_mounts = [m for m in filtered_mounts if m['rw'] == True]
elif filter_mode == "Read-Only":
    filtered_mounts = [m for m in filtered_mounts if m['rw'] == False]

# Display mounts
st.header(f"📋 Mounts ({len(filtered_mounts)} of {len(all_mounts)})")

if not filtered_mounts:
    st.info("No mounts found matching the current filters.")
else:
    # Group by mount type
    for mount_type in sorted(set([m['type'] for m in filtered_mounts])):
        type_mounts = [m for m in filtered_mounts if m['type'] == mount_type]
        
        # Icon for mount type
        type_icon = {
            'volume': '📦',
            'bind': '📁',
            'tmpfs': '💾'
        }.get(mount_type, '🔗')
        
        st.subheader(f"{type_icon} {mount_type.upper()} Mounts ({len(type_mounts)})")
        
        for mount in type_mounts:
            # Create expander title
            access_mode = "🟢 RW" if mount['rw'] else "🔒 RO"
            status_icon = "🟢" if mount['container_status'] == 'running' else "⚪"
            
            if mount_type == 'volume':
                title = f"{status_icon} **{mount['name']}** → `{mount['destination']}` ({access_mode})"
            elif mount_type == 'bind':
                title = f"{status_icon} **{mount['source']}** → `{mount['destination']}` ({access_mode})"
            else:  # tmpfs
                title = f"{status_icon} **tmpfs** → `{mount['destination']}` ({access_mode})"
            
            with st.expander(title):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("##### Mount Details")
                    st.write(f"**Type:** {mount['type']}")
                    
                    if mount_type == 'volume':
                        st.write(f"**Volume Name:** `{mount['name']}`")
                        if mount['driver'] != 'N/A':
                            st.write(f"**Driver:** `{mount['driver']}`")
                    
                    if mount['source'] != 'N/A':
                        st.write(f"**Source:** `{mount['source']}`")
                    
                    st.write(f"**Destination:** `{mount['destination']}`")
                    st.write(f"**Mode:** `{mount['mode']}`")
                    st.write(f"**Access:** {'Read-Write' if mount['rw'] else 'Read-Only'}")
                    
                    if mount['propagation'] != 'N/A':
                        st.write(f"**Propagation:** `{mount['propagation']}`")
                
                with col2:
                    st.markdown("##### Container Info")
                    st.write(f"**Name:** {mount['container_name']}")
                    st.write(f"**ID:** `{mount['container_id']}`")
                    st.write(f"**Status:** {mount['container_status']}")
                
                # Additional information based on mount type
                if mount_type == 'bind':
                    st.markdown("##### Bind Mount Information")
                    st.info("""
                    **Bind Mount Notes:**
                    - Changes on the host are immediately visible in the container
                    - The host path must exist before mounting
                    - Be careful with permissions and ownership
                    - Consider using volumes for production data
                    """)
                    
                    # Try to get host path information
                    source_path = mount['source']
                    if source_path != 'N/A':
                        try:
                            if os.path.exists(source_path):
                                st.success(f"✅ Host path exists: `{source_path}`")
                                # Get additional info
                                is_dir = os.path.isdir(source_path)
                                st.write(f"**Type:** {'Directory' if is_dir else 'File'}")
                                
                                if is_dir:
                                    try:
                                        items = os.listdir(source_path)
                                        st.write(f"**Items:** {len(items)}")
                                    except PermissionError:
                                        st.warning("Permission denied to list directory contents")
                            else:
                                st.warning(f"⚠️ Host path does not exist: `{source_path}`")
                        except Exception as e:
                            st.warning(f"Unable to check host path: {e}")
                
                elif mount_type == 'tmpfs':
                    st.markdown("##### tmpfs Mount Information")
                    st.info("""
                    **tmpfs Mount Notes:**
                    - Data stored in host system's RAM
                    - Very fast but temporary
                    - Lost when container stops
                    - Good for caches and temporary data
                    - Size limited by available memory
                    """)

# Bind mount analysis
st.header("📁 Bind Mount Analysis")
bind_mounts = [m for m in all_mounts if m['type'] == 'bind']

if bind_mounts:
    with st.expander(f"Analyze Bind Mounts ({len(bind_mounts)} found)", expanded=False):
        st.markdown("""
        **Bind Mount Best Practices Check:**
        - ✅ Using read-only mode when appropriate
        - ✅ Mounting specific files instead of entire directories when possible
        - ⚠️ Avoid mounting system directories
        - ⚠️ Be careful with write permissions on host
        """)
        
        # Group bind mounts by source
        source_map = {}
        for mount in bind_mounts:
            source = mount['source']
            if source not in source_map:
                source_map[source] = []
            source_map[source].append(mount)
        
        # Show sources used by multiple containers
        shared_sources = {k: v for k, v in source_map.items() if len(v) > 1}
        if shared_sources:
            st.markdown("##### 🔗 Shared Bind Mounts")
            st.info(f"{len(shared_sources)} host path(s) are mounted in multiple containers")
            for source, mounts in shared_sources.items():
                with st.expander(f"`{source}` - used by {len(mounts)} containers"):
                    for mount in mounts:
                        st.write(f"- **{mount['container_name']}** → `{mount['destination']}` ({'RW' if mount['rw'] else 'RO'})")
        
        # Check for read-write bind mounts
        rw_binds = [m for m in bind_mounts if m['rw']]
        if rw_binds:
            st.markdown("##### 🟢 Read-Write Bind Mounts")
            st.warning(f"{len(rw_binds)} bind mount(s) have write access. Ensure this is intentional.")
            for mount in rw_binds:
                st.write(f"- **{mount['container_name']}**: `{mount['source']}` → `{mount['destination']}`")
else:
    st.info("No bind mounts found in any container.")

# Volume mount summary
st.header("📦 Volume Mount Summary")
volume_mounts = [m for m in all_mounts if m['type'] == 'volume']

if volume_mounts:
    # Group by volume name
    volume_map = {}
    for mount in volume_mounts:
        vol_name = mount['name']
        if vol_name not in volume_map:
            volume_map[vol_name] = []
        volume_map[vol_name].append(mount)
    
    with st.expander(f"Volume Usage ({len(volume_map)} volumes mounted)", expanded=False):
        for vol_name, mounts in sorted(volume_map.items()):
            st.markdown(f"**{vol_name}** - used by {len(mounts)} container(s)")
            for mount in mounts:
                status_icon = "🟢" if mount['container_status'] == 'running' else "⚪"
                access = "RW" if mount['rw'] else "RO"
                st.write(f"  {status_icon} {mount['container_name']} → `{mount['destination']}` ({access})")
else:
    st.info("No volume mounts found in any container.")

# Tips section
with st.expander("💡 Tips & Recommendations"):
    st.markdown("""
    ### When to use each mount type:
    
    **Use Volumes when:**
    - Storing database data
    - Persisting application state
    - Sharing data between multiple containers
    - Running in production environments
    - Need easy backup and migration
    
    **Use Bind Mounts when:**
    - Developing and need live code reload
    - Mounting configuration files
    - Need to access specific host files
    - Sharing files between host and container
    - Working with tools that expect specific paths
    
    **Use tmpfs when:**
    - Storing temporary data
    - Caching
    - Storing secrets (they won't persist)
    - High-performance temporary storage needed
    
    ### Security Tips:
    - Use `:ro` (read-only) whenever container doesn't need write access
    - Don't mount sensitive system directories
    - Be careful mounting with read-write access
    - Use volumes instead of bind mounts for production
    - Limit bind mount usage to development environments
    """)
