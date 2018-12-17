FROM circleci/python:3.6.6-jessie-node-browsers

RUN \
  sudo apt-get update && \
  sudo apt-get -y upgrade && \
  sudo apt-get install -y build-essential && \
  sudo apt-get install -y software-properties-common && \
  sudo apt-get install -y wget \
    make \
    build-essential \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    git && \
  sudo echo "deb http://ftp.debian.org/debian jessie-backports main" | sudo tee /etc/apt/sources.list.d/backports.list && \
  sudo apt-get -y -t jessie-backports install openssl libssl-dev

RUN sudo chown -R circleci /home/circleci

WORKDIR /home/circleci
