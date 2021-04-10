FROM jupyter/minimal-notebook:8d32a5208ca1

# Set some environment variables
ENV PROJDIR=${HOME}/mask_children \
    URL_SDM=https://www.sdmproject.com/software/updates/SdmPsiGui-linux64-v6.21.tar.gz \
    PATH=${HOME}/software/SdmPsiGui-linux64-v6.21:${PATH}

# Copy code and data into the container
WORKDIR ${PROJDIR}
COPY code/ code/
COPY data/ data/

# Install SDM and Python packages
COPY requirements.txt .
RUN wget -P software/ ${URL_SDM} && \
    tar -xf software/SdmPsiGui-linux64-v6.21.tar.gz -C software/ && \
    pip install -U -r requirements.txt

# Add permissions for default user
USER root
RUN chown -R ${NB_UID} ${PROJDIR}
USER ${NB_USER}
