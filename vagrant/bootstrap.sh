#!/usr/bin/env bash

wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | \
        gpg --dearmor - | sudo tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null
apt-add-repository -y 'deb https://apt.kitware.com/ubuntu/ focal main'
apt-get update
apt-get full-upgrade -y
apt-get install -y \
	build-essential \
	cmake \
	gcc-multilib \
	git \
	mercurial \
	python3-pip \
	python-cryptography \
	srecord \
	unzip \
	ninja-build \
