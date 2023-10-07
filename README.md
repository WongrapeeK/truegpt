#Docker Compile
`DOCKER_BUILDKIT=1 docker build . -t localgpt && docker run --runtime=nvidia -it --mount src="$HOME/.cache",target=/root/.cache,type=bind -p 80:5111 -p 8501:8501 localgpt`
