# syntax=docker/dockerfile:1
# Build as `docker build . -t localgpt`, requires BuildKit.
# Run as `docker run -it --mount src="$HOME/.cache",target=/root/.cache,type=bind --gpus=all localgpt`, requires Nvidia container toolkit.

FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y software-properties-common
RUN apt-get install -y g++-11 make python3 python-is-python3 pip git wget tcpdump
RUN pip install --upgrade pip
RUN apt-get -y remove python3-blinker
# only copy what's needed at every step to optimize layer cache
COPY ./requirements.txt .
# use BuildKit cache mount to drastically reduce redownloading from pip on repeated builds
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
RUN dpkg -i cuda-keyring_1.0-1_all.deb
RUN apt-get update && apt-get -y install cuda-11-8
ENV TORCH_CUDA_ARCH_LIST="7.0 7.5 8.0 8.6+PTX"
RUN --mount=type=cache,target=/root/.cache CMAKE_ARGS="-DLLAMA_CUBLAS=on" FORCE_CMAKE=1 pip install --timeout 100 -r requirements.txt
COPY SOURCE_DOCUMENTS ./SOURCE_DOCUMENTS
COPY ingest.py constants.py ./
# Docker BuildKit does not support GPU during *docker build* time right now, only during *docker run*.
# See <https://github.com/moby/buildkit/issues/1436>.
# If this changes in the future you can `docker build --build-arg device_type=cuda  . -t localgpt` (+GPU argument to be determined).
#Streamlit
#RUN mkdir Chatbot && cd Chatbot && ln -s ../localGPT_UI.py localGPT_UI.py && ln -s ../constants.py constants.py && ln -s ../load_models.py load_models.py && ln -s ../run_localGPT.py run_localGPT.py && ln -s ../prompt_template_utils.py prompt_template_utils.py
#
#RUN git clone -b v0.4.2 https://github.com/PanQiWei/AutoGPTQ.git && cd AutoGPTQ && pip install .
#
ARG device_type=cpu
RUN --mount=type=cache,target=/root/.cache python ingest.py --device_type $device_type
COPY . .
ENV device_type=cuda

#CMD python run_localGPT.py --device_type $device_type --use_history
CMD python run_localGPT.py --device_type $device_type

#CMD python run_localGPT_API.py --device_type $device_type & python /localGPTUI/localGPTUI.py --host 0.0.0.0

#WORKDIR "Chatbot"
#CMD streamlit run localGPT_UI.py
