FROM condaforge/miniforge3:4.10.3-10

WORKDIR /app
RUN apt-get --allow-releaseinfo-change update && apt-get -y install gcc

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y python3-opencv

COPY env.yml .
RUN conda env create -f env.yml

COPY recorder.py .
CMD conda run -n recorder /bin/bash -c "python -u recorder.py &"
