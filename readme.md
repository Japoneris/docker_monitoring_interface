# Docker Monitoring Lab


## What 

Graphical interface to interact with docker containers.

## Why

I do not know by heart all docker commands. 
This makes my life easier.

## How 

Python with:

- `streamlit` to configure easily a GUI
- `docker` [SDK](https://docker-py.readthedocs.io/en/stable/) to interact with docker

# Running

## Requirements

- Docker group configured properly (no need for `sudo` for each docker cmd, check [here](https://docs.docker.com/engine/install/linux-postinstall/) if needed)
- Compatible docker version: `Docker version 29.1.1,` (some other may works)

## Docker 

```sh
docker build -t docker-monitoring-lab .
docker run -p 8501:8501 -v /var/run/docker.sock:/var/run/docker.sock docker-monitoring-lab
```

### Troubleshooting

If you have a port conflict, change `"8505:8501"` by `<another_valid_port>:8501`


## Docker Compose

```sh
# Prepare the image
docker compose build

# Run
docker compose up
# or to run in Background
docker-compose up -d

# Stop + volume 
docker compose stop -v 
```

### Troubleshooting

If you have a port conflict, change `"8505:8501"` by `<another_valid_port>:8501`


## Python venv 

```sh
# Create a virtual env
python3 -m venv <my_env_name>

# Load the venv
source <my_env_name>/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Go to app directory
cd src

# Launch app with streamlit
streamlit run app.py
```


### Troubleshooting

If you have a port conflict, add `streamlit run app.py --server.port=<valid_port>`


# Cost

Designed by a human, made by AI.

A dozen of premium request (Github Copilot Agent), around one call per page.
Minor edit