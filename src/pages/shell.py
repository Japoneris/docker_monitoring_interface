"""
In the shell, the user should have a minimal interface to run commands in the container.

The user should select in a dropdown the container to run the shell in.
The user should provide the path where it wants to execute the commands.
Check if the path exists, otherwise show an error message.

The output of the command should be streamed directly to the interface, so the user can see it in real-time.

In the info, say that "cd" command may not work as expected, so use the path field to navigate.
"""

import streamlit as st
import docker
from docker.errors import DockerException, APIError

st.title("🐳 Docker Container Shell")

st.info("ℹ️ **Note:** The `cd` command may not work as expected in this interface. "
        "Please use the **Working Directory** field below to navigate to different paths.")

# Get Docker client
try:
    client = docker.from_env()
except DockerException as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

# Get running containers
try:
    containers = client.containers.list()
    if not containers:
        st.warning("No running containers found. Please start a container first.")
        st.stop()
    
    container_dict = {f"{c.name} ({c.short_id})": c for c in containers}
except APIError as e:
    st.error(f"Error fetching containers: {e}")
    st.stop()

# Container selection
st.subheader("Container Selection")
selected_container_name = st.selectbox(
    "Select a container:",
    options=list(container_dict.keys())
)
selected_container = container_dict[selected_container_name]

# Working directory input
st.subheader("Working Directory")
workdir = st.text_input(
    "Enter working directory path:",
    value="/",
    help="The directory where commands will be executed"
)

# Auto-verify path when workdir changes
if workdir:
    try:
        exit_code, _ = selected_container.exec_run(f'test -d {workdir}', workdir='/')
        if exit_code == 0:
            st.success(f"✅ Path '{workdir}' exists")
        else:
            st.error(f"❌ Path '{workdir}' does not exist")
    except Exception as e:
        st.error(f"Error checking path: {e}")


# Command input
st.subheader("Execute Command")
command = st.text_input(
    "Enter command:",
    placeholder="ls -la",
    help="Command to execute in the selected container"
)

# Execute button
if st.button("Execute", type="primary", disabled=not command):
    # Verify path exists
    try:
        exit_code, _ = selected_container.exec_run(f'test -d {workdir}', workdir='/')
        if exit_code != 0:
            st.error(f"Cannot execute: Path '{workdir}' does not exist in container")
        else:
            st.code(f"$ {command}", language="bash")
            
            # Execute and stream output
            try:
                exec_instance = selected_container.exec_run(
                    command,
                    workdir=workdir,
                    stream=True,
                    demux=True
                )
                
                def output_generator():
                    """Generator to stream output from exec_run"""
                    for stdout, stderr in exec_instance.output:
                        if stdout:
                            yield "```sh\n{}```\n".format(stdout.decode('utf-8', errors='replace'))
                        if stderr:
                            yield f"\n\n[STDERR] {stderr.decode('utf-8', errors='replace')}"
                
                st.subheader("Output:")
                with st.chat_message("user"):
                    st.write_stream(output_generator())
                    
            except Exception as e:
                st.error(f"Error executing command: {e}")
                
    except Exception as e:
        st.error(f"Error checking path: {e}")