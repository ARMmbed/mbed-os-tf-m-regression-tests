#!/usr/bin/env bash

apt-get update
apt-get full-upgrade -y
apt-get install -y \
	build-essential \
	cmake \
	gcc-multilib \
	git \
	mercurial \
	python3-pip \
	srecord \
	unzip \
	ninja-build \
