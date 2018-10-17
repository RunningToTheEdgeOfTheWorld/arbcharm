#!/usr/bin/env bash

docker rmi arbcharm || echo
docker build -t arbcharm .