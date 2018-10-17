#!/usr/bin/env bash

docker stop arbcharm || echo
docker rm -v arbcharm || echo
docker run -dt --name arbcharm -e ARBCHARM=prd arbcharm