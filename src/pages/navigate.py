"""
1. Select a container
2. Provide the user to navigate the file system 
- by providing a path input 
- by clicking on folders/ going to up from one level, to the root, to common directories, etc.
Should list the files (plus info like size, date modified, type, etc.) 

Allow to download a file (get the raw file) or a folder (make a .tar archive)
Allow to upload a file to the container in the current directory
Provide also a way to delete files/folders (one by one, asking for confirmation)

"""

import streamlit as st
import docker
import tarfile
import io
import os
from datetime import datetime

# Initialize Docker client
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker: {e}")
    st.stop()

st.title("📁 Container File Navigator")

# Get all running containers
try:
    running_containers = client.containers.list()
except Exception as e:
    st.error(f"Failed to list containers: {e}")
    st.stop()

if not running_containers:
    st.warning("No running containers found. Please start a container first.")
    st.stop()

# Container selection
container_options = {f"{c.name} ({c.short_id})": c for c in running_containers}
selected_container_name = st.selectbox("Select a container:", list(container_options.keys()))
container = container_options[selected_container_name]

st.success(f"Connected to: **{container.name}**")

# Get container's working directory
workdir = container.attrs.get('Config', {}).get('WorkingDir', '/')
if not workdir:
    workdir = '/'

# Initialize session state for current path
# Reset path when container changes
if 'selected_container' not in st.session_state or st.session_state.selected_container != container.id:
    st.session_state.selected_container = container.id
    st.session_state.current_path = workdir
elif 'current_path' not in st.session_state:
    st.session_state.current_path = workdir

st.info(f"📂 Container working directory: `{workdir}`")

# Handle navigation action if set
if 'nav_action' in st.session_state and st.session_state.nav_action:
    action = st.session_state.nav_action
    st.session_state.nav_action = None
    
    if action == 'root':
        st.session_state.current_path = '/'
    elif action == 'up':
        current = st.session_state.current_path.rstrip('/')
        if current and current != '/':
            parent = os.path.dirname(current)
            st.session_state.current_path = parent if parent else '/'
    elif action == 'tmp':
        st.session_state.current_path = '/tmp'
    elif action == 'home':
        st.session_state.current_path = '/home'
    elif action.startswith('goto:'):
        new_path = action[5:]
        st.session_state.current_path = new_path
    
    st.rerun()

# Navigation controls
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])


with col1:
    new_path = st.text_input("Current path: ", value=st.session_state.current_path)
    if new_path != st.session_state.current_path:
        st.session_state.nav_action = f'goto:{new_path}'
        st.rerun()

with col2:
    if st.button("🏠 Root", key="btn_root"):
        st.session_state.nav_action = 'root'
        st.rerun()

with col3:
    if st.button("⬆️ Up", key="btn_up"):
        st.session_state.nav_action = 'up'
        st.rerun()

with col4:
    if st.button("📂 Tmp", key="btn_tmp"):
        st.session_state.nav_action = 'tmp'
        st.rerun()

with col5:
    if st.button("🏠 Home", key="btn_home"):
        st.session_state.nav_action = 'home'
        st.rerun()



# List directory contents
def list_directory(container, path):
    """List files and directories in the given path"""
    try:
        # Use ls -la to get detailed file information
        exec_result = container.exec_run(f'ls -la "{path}"', demux=True)
        if exec_result.exit_code != 0:
            return None, f"Error accessing path: {exec_result.output[1].decode() if exec_result.output[1] else 'Unknown error'}"
        
        output = exec_result.output[0].decode() if exec_result.output[0] else ""
        lines = output.strip().split('\n')[1:]  # Skip "total" line
        
        files = []
        for line in lines:
            parts = line.split(None, 8)
            if len(parts) >= 9:
                permissions = parts[0]
                size = parts[4]
                name = parts[8]
                
                # Skip . and ..
                if name in ['.', '..']:
                    continue
                
                is_dir = permissions.startswith('d')
                files.append({
                    'name': name,
                    'is_dir': is_dir,
                    'permissions': permissions,
                    'size': size,
                    'date': f"{parts[5]} {parts[6]} {parts[7]}"
                })
        
        return files, None
    except Exception as e:
        return None, str(e)

files, error = list_directory(container, st.session_state.current_path)

if error:
    st.error(error)
else:
    st.subheader(f"Contents of `{st.session_state.current_path}`")
    
    if files:
        # Separate directories and files
        directories = [f for f in files if f['is_dir']]
        regular_files = [f for f in files if not f['is_dir']]
        
        # Display directories first
        if directories:
            st.write("**📁 Directories:**")
            for item in directories:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    if st.button(f"📁 {item['name']}", key=f"dir_{item['name']}"):
                        print("name", item['name'])
                        # Build new path properly
                        current = st.session_state.current_path.rstrip('/')
                        if current == '':
                            current = '/'
                        new_path = os.path.join(current, item['name'])
                        print("NAV TO:", new_path)
                        st.session_state.nav_action = f'goto:{new_path}'
                        st.rerun()
                with col2:
                    st.text(item['permissions'])
                with col3:
                    st.text(item['date'])
                with col4:
                    if st.button("🗑️", key=f"del_dir_{item['name']}"):
                        st.session_state.dir_to_delete = item['name']
                        st.rerun()
                
                # Delete directory confirmation dialog (appears right under the directory)
                if 'dir_to_delete' in st.session_state and st.session_state.dir_to_delete == item['name']:
                    st.warning(f"⚠️ **Are you sure you want to delete directory:** `{item['name']}`? This will delete all contents and cannot be undone.")
                    
                    col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 3])
                    with col_confirm1:
                        if st.button("✅ Yes, Delete", key=f"confirm_delete_dir_{item['name']}", type="primary"):
                            full_path = os.path.join(st.session_state.current_path, item['name'])
                            try:
                                # Delete the directory using exec_run with rm -rf
                                exec_result = container.exec_run(f'rm -rf "{full_path}"', demux=True)
                                if exec_result.exit_code == 0:
                                    st.success(f"Successfully deleted directory: {item['name']}")
                                    del st.session_state.dir_to_delete
                                    st.rerun()
                                else:
                                    error_msg = exec_result.output[1].decode() if exec_result.output[1] else 'Unknown error'
                                    st.error(f"Failed to delete directory: {error_msg}")
                            except Exception as e:
                                st.error(f"Error deleting directory: {e}")
                    
                    with col_confirm2:
                        if st.button("❌ Cancel", key=f"cancel_delete_dir_{item['name']}"):
                            del st.session_state.dir_to_delete
                            st.rerun()



        # Display files
        if regular_files:
            st.write("**📄 Files:**")
            for item in regular_files:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                with col1:
                    st.text(f"📄 {item['name']}")
                with col2:
                    st.text(f"{item['size']} bytes")
                with col3:
                    st.text(item['date'])
                with col4:
                    # Step 1: Select file for download
                    if st.button("⬇️ Select", key=f"select_{item['name']}"):
                        st.session_state.selected_file_for_download = item['name']
                        st.rerun()
                
                with col5:
                    if st.button("🗑️", key=f"del_file_{item['name']}"):
                        st.session_state.file_to_delete = item['name']
                        st.rerun()
                
                # Delete file confirmation dialog (appears right under the file)
                if 'file_to_delete' in st.session_state and st.session_state.file_to_delete == item['name']:
                    st.warning(f"⚠️ **Are you sure you want to delete:** `{item['name']}`? This action cannot be undone.")
                    
                    col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 3])
                    with col_confirm1:
                        if st.button("✅ Yes, Delete", key=f"confirm_delete_{item['name']}", type="primary"):
                            full_path = os.path.join(st.session_state.current_path, item['name'])
                            try:
                                # Delete the file using exec_run
                                exec_result = container.exec_run(f'rm -f "{full_path}"', demux=True)
                                if exec_result.exit_code == 0:
                                    st.success(f"Successfully deleted: {item['name']}")
                                    del st.session_state.file_to_delete
                                    st.rerun()
                                else:
                                    error_msg = exec_result.output[1].decode() if exec_result.output[1] else 'Unknown error'
                                    st.error(f"Failed to delete file: {error_msg}")
                            except Exception as e:
                                st.error(f"Error deleting file: {e}")
                    
                    with col_confirm2:
                        if st.button("❌ Cancel", key=f"cancel_delete_{item['name']}"):
                            del st.session_state.file_to_delete
                            st.rerun()


            # Step 2: Prepare file for download after selection
            if 'selected_file_for_download' in st.session_state and st.session_state.selected_file_for_download:
                selected_file = st.session_state.selected_file_for_download
                st.divider()
                st.info(f"**Selected file for download:** {selected_file}")
                
                full_path = os.path.join(st.session_state.current_path, selected_file)
                try:
                    bits, stat = container.get_archive(full_path)
                    file_data = b''.join(bits)
                    
                    # Extract file from tar
                    tar_stream = io.BytesIO(file_data)
                    tar = tarfile.open(fileobj=tar_stream)
                    file_member = tar.getmembers()[0]
                    extracted_file = tar.extractfile(file_member)
                    
                    if extracted_file:
                        col_dl1, col_dl2 = st.columns([1, 3])
                        with col_dl1:
                            st.download_button(
                                "⬇️ Download File",
                                data=extracted_file.read(),
                                file_name=selected_file,
                                key=f"dl_{selected_file}"
                            )
                        with col_dl2:
                            if st.button("❌ Cancel", key="cancel_download"):
                                del st.session_state.selected_file_for_download
                                st.rerun()
                except Exception as e:
                    st.error(f"Error preparing file for download: {e}")
                    if st.button("❌ Cancel", key="cancel_download_error"):
                        del st.session_state.selected_file_for_download
                        st.rerun()
    else:
        st.info("Directory is empty")
    
    # Download folder as tar
    st.divider()
    st.subheader("📦 Download Current Folder")
    if st.button("Download folder as .tar"):
        try:
            bits, stat = container.get_archive(st.session_state.current_path)
            tar_data = b''.join(bits)
            folder_name = os.path.basename(st.session_state.current_path.rstrip('/')) or 'root'
            st.download_button(
                "⬇️ Download TAR Archive",
                data=tar_data,
                file_name=f"{folder_name}.tar",
                mime="application/x-tar"
            )
        except Exception as e:
            st.error(f"Error creating archive: {e}")
    
    # Upload file
    st.divider()
    st.subheader("📤 Upload File")
    uploaded_file = st.file_uploader("Choose a file to upload to current directory")
    if uploaded_file is not None:
        if st.button("Upload to container"):
            try:
                # Create a tar archive in memory
                tar_stream = io.BytesIO()
                tar = tarfile.TarFile(fileobj=tar_stream, mode='w')
                
                # Add file to tar
                file_data = uploaded_file.read()
                tarinfo = tarfile.TarInfo(name=uploaded_file.name)
                tarinfo.size = len(file_data)
                tarinfo.mtime = datetime.now().timestamp()
                tar.addfile(tarinfo, io.BytesIO(file_data))
                tar.close()
                
                # Upload to container
                tar_stream.seek(0)
                container.put_archive(st.session_state.current_path, tar_stream.read())
                
                st.success(f"Uploaded {uploaded_file.name} to {st.session_state.current_path}")
                st.rerun()
            except Exception as e:
                st.error(f"Error uploading file: {e}")
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh"):
        st.rerun()