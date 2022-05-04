# CCTV Recorder

### Continuous Camera Recording Service

## Setup instructions

1. Edit **docker-compose.yml** file: create a new service for each camera, specify the camera name, the rtsp stream link and cpu cores (the template is already provided in the file)
2. Run **"docker-compose up -d --build"** in root directory
