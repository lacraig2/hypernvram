docker build -t nvram .
docker run -v `realpath .`:/vsock  -w /vsock -it nvram bash docker_inner_build_targets.sh
# docker run -v `realpath .`:/vsock  -w /vsock -it nvram bash 