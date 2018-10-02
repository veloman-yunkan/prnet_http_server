# PRNet HTTP Server

This little project enables using the [PRNet](https://github.com/YadiraF/PRNet)
library in a WSGI-compatible web server and provides a docker image with one
such fully functional web-server.

## Getting Started

    # Clone this repository
    git clone https://github.com/veloman-yunkan/prnet_http_server.git
    
    cd prnet_http_server/

    # This script clones the PRNet repo and gets the trained model
    # data from Google Drive
    ./setup_PRNet 

    # Install required dependencies - see Dockerfile.base
    
    # Run the tests (1 of them may fail because of slight numeric differences)
    ./run_tests
    
## Building the docker image

    ./build_docker_image
    
This step takes a while and creates a 1.5GB sized docker image
`prnet_http_server:latest`.

## Updating the docker image

If anything changes in this repo or PRNet, then - after updating them - just
run

    ./update_docker_image

Updating the docker image is much faster - the new image is built on top of the
`prnet_http_server:base` image (containing just the dependencies) that was
created by the `./build_docker_image` script.

## Running tests using the dockerized web-server

    ./run_tests --use-docker

## Using the dockerized web-server

Start the server with

    docker run --rm -d -p 8000:8000 prnet_http_server:latest

Send an image to it with

    curl -OJF image=@test_data/single_face.jpg http://localhost:8000
    
When starting the server, you can specify the upper limit on the image file size
(in bytes) through the `PRNET_MAX_IMAGE_SIZE` environment variable:

    # Make the server reject images exceeding 5MB
    docker run --rm -d -p 8000:8000 -e PRNET_MAX_IMAGE_SIZE=5000000 prnet_http_server:latest

The container runs the [gunicorn](https://gunicorn.org/) web server inside and allows
to specify its [settings](http://docs.gunicorn.org/en/stable/settings.html) through the
command line. For example, to make the web-server use 4
[worker processes](http://docs.gunicorn.org/en/stable/settings.html#worker-processes)
for handling requests, provide the `--workers=4` option:

    docker run --rm -d -p 8000:8000 prnet_http_server:latest --workers=4
    #                                                        ^^^^^^^^^^^
