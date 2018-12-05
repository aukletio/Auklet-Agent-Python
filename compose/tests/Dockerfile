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

COPY ./auklet /home/circleci/auklet
COPY ./tests /home/circleci/tests
COPY ./.devops /home/circleci/.devops
COPY ./.git /home/circleci/.git

COPY ./compose /home/circleci/compose
COPY ./.coveragerc /home/circleci/.coveragerc
COPY ./README.md /home/circleci/README.md
COPY ./requirements.txt /home/circleci/requirements.txt
COPY ./setup.cfg /home/circleci/setup.cfg
COPY ./setup.py /home/circleci/setup.py
COPY ./tests.txt /home/circleci/tests.txt

RUN sudo chown -R circleci /home/circleci
RUN mkdir /home/circleci/htmlcov


WORKDIR /home/circleci
