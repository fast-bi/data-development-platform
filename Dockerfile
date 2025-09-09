#  Generic dockerfile for dbt image building.
#  See README for operational details
##

# Top level build args
ARG build_for=linux/amd64

##
# base image (abstract)
##
FROM --platform=$build_for python:3.11.11-slim-bullseye AS base
LABEL maintainer=TeraSky(c)

RUN mkdir -p /usr/src/fastbi_tenant

# Install build dependencies and PostgreSQL development libraries
RUN apt-get update \
  && apt-get dist-upgrade -y \
  && apt-get install -y --no-install-recommends \
  build-essential \
  libpq-dev \
  gcc \
  jq \
  ca-certificates \
  curl \
  gnupg \
  dirmngr \
  git-all \
  apt-transport-https \
  openssh-client \
  software-properties-common \
  unzip \
  wget

# Setup Google Cloud SDK
RUN mkdir -p /etc/apt/keyrings
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt update && apt install google-cloud-sdk -y

# Install gke-gcloud-auth-plugin
RUN apt-get install google-cloud-sdk-gke-gcloud-auth-plugin -y

# Setup Kubernetes
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
RUN chmod 644 /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y kubectl

# Setup Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh

# Setup Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
RUN apt-get update && apt-get install -y terraform

# Setup Terragrunt
RUN wget https://github.com/gruntwork-io/terragrunt/releases/download/v0.66.1/terragrunt_linux_amd64
RUN mv terragrunt_linux_amd64 terragrunt
RUN chmod u+x terragrunt
RUN mv terragrunt /usr/local/bin/terragrunt

RUN apt-get clean \
  && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/*

WORKDIR /usr/src/fastbi_tenant

COPY requirements.txt /usr/src/fastbi_tenant

RUN pip3 install --no-cache-dir --upgrade pip

RUN pip3 install --no-cache-dir -r requirements.txt

ENV USE_GKE_GCLOUD_AUTH_PLUGIN=True
ENV CLOUDSDK_PYTHON_SITEPACKAGES=1

COPY ./ /usr/src/fastbi_tenant

RUN git config --global user.email "tda@fast.bi"
RUN git config --global user.name "Tenant Deployment Agent"
RUN git config --global init.defaultBranch "master"

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "-c", "gunicorn -w 5 -b 0.0.0.0:8080 --access-logfile - --error-logfile - --log-level $LOG_LEVEL --timeout 7200 --preload app.wsgi:app"]
#ENTRYPOINT ["/bin/sh", "-c", "tail -f /dev/null"]