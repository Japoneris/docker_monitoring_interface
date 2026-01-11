"""
Page to view Docker container logs

Features:
- Select a container (all or running only)
- Limit history view with configurable options
- Navigate through logs with pagination
- Filter by timestamp
- Auto-refresh option
- Show stderr separately if available
"""

import streamlit as st
import docker
from datetime import datetime, timedelta
from docker.errors import DockerException, APIError

st.title("📜 Docker Container Logs")

# Get Docker client
try:
    client = docker.from_env()
except DockerException as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

# Initialize session state for pagination
if 'log_offset' not in st.session_state:
    st.session_state.log_offset = 0
if 'logs_per_page' not in st.session_state:
    st.session_state.logs_per_page = 100

# Get containers
try:
    show_all = st.checkbox("Show all containers (including stopped)", value=False)
    containers = client.containers.list(all=show_all)
    
    if not containers:
        st.warning("No containers found." + (" Please start a container first." if not show_all else ""))
        st.stop()
    
    # Add status emojis
    status_emojis = {
        'running': '🟢',
        'exited': '🔴',
        'paused': '⏸️',
        'restarting': '🔄',
        'created': '🔵',
        'dead': '💀',
        'removing': '🗑️'
    }

    container_dict = {f"{status_emojis.get(c.status, '⚪')} [{c.status}] {c.name} ({c.short_id}) ": c for c in containers}
except APIError as e:
    st.error(f"Error fetching containers: {e}")
    st.stop()

# Container selection
st.subheader("Container Selection")
selected_container_name = st.selectbox(
    "Select a container:",
    options=list(container_dict.keys()),
    help="Choose the container whose logs you want to view"
)
selected_container = container_dict[selected_container_name]

# Log configuration
st.subheader("Log Options")
col1, col2, col3 = st.columns(3)

with col1:
    # Time range options
    time_filter = st.selectbox(
        "Time range:",
        options=["All time", "Last hour", "Last 6 hours", "Last 24 hours", "Last 7 days", "Custom"],
        index=0
    )
    
with col2:
    # Number of lines
    tail_option = st.selectbox(
        "Tail lines:",
        options=["All", "100", "500", "1000", "5000"],
        index=1,
        help="Number of most recent log lines to fetch"
    )
    
with col3:
    # Auto-refresh
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    if auto_refresh:
        st.info("🔄 Auto-refreshing every 5 seconds")

# Calculate time parameters
since = None
until = None

if time_filter == "Last hour":
    since = datetime.now() - timedelta(hours=1)
elif time_filter == "Last 6 hours":
    since = datetime.now() - timedelta(hours=6)
elif time_filter == "Last 24 hours":
    since = datetime.now() - timedelta(days=1)
elif time_filter == "Last 7 days":
    since = datetime.now() - timedelta(days=7)
elif time_filter == "Custom":
    col_start, col_end = st.columns(2)
    with col_start:
        since_date = st.date_input("From date:", value=datetime.now() - timedelta(days=1))
        since_time = st.time_input("From time:", value=datetime.min.time())
        since = datetime.combine(since_date, since_time)
    with col_end:
        until_date = st.date_input("To date:", value=datetime.now())
        until_time = st.time_input("To time:", value=datetime.now().time())
        until = datetime.combine(until_date, until_time)

# Determine tail parameter
tail = "all" if tail_option == "All" else int(tail_option)

# Additional options
col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    show_timestamps = st.checkbox("Show timestamps", value=True)
with col_opt2:
    follow_logs = st.checkbox("Follow logs (streaming)", value=False, 
                              help="Stream logs in real-time. Disable auto-refresh when using this.")

# Fetch and display logs
st.subheader("Logs")

# Action buttons
col_btn1, col_btn2 = st.columns([1, 2])
with col_btn1:
    if st.button("🗑️ Clear Display"):
        st.session_state.log_offset = 0
        st.rerun()

try:
    # Build log parameters
    log_kwargs = {
        'timestamps': show_timestamps,
        'tail': tail,
    }
    
    if since:
        log_kwargs['since'] = since
    if until:
        log_kwargs['until'] = until
    
    # Fetch logs
    if follow_logs:
        st.info("📡 Streaming logs... (this will continue until you stop it)")
        log_kwargs['stream'] = True
        log_kwargs['follow'] = True
        
        # Create a placeholder for streaming logs
        log_placeholder = st.empty()
        log_buffer = []
        max_display_lines = 1000  # Prevent memory issues
        
        try:
            for log_line in selected_container.logs(**log_kwargs):
                decoded_line = log_line.decode('utf-8', errors='replace').rstrip()
                log_buffer.append(decoded_line)
                
                # Keep only last max_display_lines
                if len(log_buffer) > max_display_lines:
                    log_buffer.pop(0)
                
                # Update display
                log_placeholder.code('\n'.join(log_buffer), language='log')
                
        except KeyboardInterrupt:
            st.info("Streaming stopped by user")
    else:
        # Fetch all logs at once
        logs = selected_container.logs(**log_kwargs)
        
        if logs:
            # Decode and split into lines
            log_lines = logs.decode('utf-8', errors='replace').split('\n')
            log_lines = [line for line in log_lines if line.strip()]  # Remove empty lines
            
            total_lines = len(log_lines)
            
            if total_lines > 0:
                # Pagination settings
                st.caption(f"**Total log lines:** {total_lines}")
                
                # Pagination controls
                if total_lines > 100:
                    col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
                    
                    with col_pag1:
                        lines_per_page = st.selectbox(
                            "Lines per page:",
                            options=[50, 100, 200, 500, 1000],
                            index=1,
                            key="lines_per_page_select"
                        )
                    
                    with col_pag2:
                        total_pages = (total_lines + lines_per_page - 1) // lines_per_page
                        current_page = st.number_input(
                            f"Page (1 to {total_pages}):",
                            min_value=1,
                            max_value=total_pages,
                            value=1,
                            step=1,
                            key="page_number"
                        )
                        st.session_state.log_offset = (current_page - 1) * lines_per_page
                    
                    with col_pag3:
                        st.write(f"Showing lines {st.session_state.log_offset + 1} - {min(st.session_state.log_offset + lines_per_page, total_lines)}")
                    
                    # Get current page lines
                    start_idx = st.session_state.log_offset
                    end_idx = min(start_idx + lines_per_page, total_lines)
                    display_lines = log_lines[start_idx:end_idx]
                else:
                    display_lines = log_lines
                    st.caption("Showing all lines")
                
                # Display logs
                st.code('\n'.join(display_lines), language='log')
                
                # Navigation buttons for pagination
                if total_lines > 100:
                    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
                    with col_nav1:
                        if st.button("⏮️ First Page", disabled=(current_page == 1)):
                            st.session_state.log_offset = 0
                            st.rerun()
                    with col_nav2:
                        if st.button("⬅️ Previous", disabled=(current_page == 1)):
                            st.session_state.log_offset = max(0, st.session_state.log_offset - lines_per_page)
                            st.rerun()
                    with col_nav3:
                        if st.button("➡️ Next", disabled=(current_page == total_pages)):
                            st.session_state.log_offset = min(total_lines - 1, st.session_state.log_offset + lines_per_page)
                            st.rerun()
                    with col_nav4:
                        if st.button("⏭️ Last Page", disabled=(current_page == total_pages)):
                            st.session_state.log_offset = (total_pages - 1) * lines_per_page
                            st.rerun()
            else:
                st.info("No logs available for the selected criteria.")
        else:
            st.info("No logs available for this container.")
            
except Exception as e:
    st.error(f"Error fetching logs: {e}")
    import traceback
    with st.expander("Show error details"):
        st.code(traceback.format_exc())

# Auto-refresh functionality
if auto_refresh and not follow_logs:
    import time
    time.sleep(5)
    st.rerun()

# Help section
with st.expander("ℹ️ Help & Tips"):
    st.markdown("""
    ### Log Viewing Options
    
    **Time Range:**
    - Select predefined ranges or use custom date/time filters
    - Filters are applied at the Docker API level for efficiency
    
    **Tail Lines:**
    - Limits how many recent lines to fetch from the container
    - Use smaller values for faster loading on containers with large log files
    
    **Pagination:**
    - Navigate through large log files without loading everything at once
    - Adjust lines per page based on your needs
    
    **Follow Logs:**
    - Enable to stream logs in real-time (similar to `docker logs -f`)
    - Useful for monitoring active containers
    - Note: Auto-refresh is not needed when following logs
    
    **Auto-refresh:**
    - Automatically reloads logs every 5 seconds
    - Useful for monitoring without streaming
    
    **Timestamps:**
    - Show/hide log entry timestamps
    - Useful for debugging time-sensitive issues
    """)
