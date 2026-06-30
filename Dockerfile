FROM python:3.11-slim

# Install SSH service and Ping utility
RUN apt-get update && apt-get install -y \
    openssh-server \
    iputils-ping \
    git \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the requirements file FIRST
COPY requirements.txt /app/requirements.txt

# Install the Python dependencies
# (--no-cache-dir keeps the container size small by not saving the downloaded installation files)
RUN pip install --no-cache-dir -r requirements.txt

# Configure the SSH daemon to allow password authentication for testing
RUN mkdir -p /var/run/sshd
RUN echo 'root:peerpatch123' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Bake the ENTIRE project folder into the container
COPY . /app/

# Create a wrapper script named 'peerp'
RUN echo '#!/bin/sh\npython3 /app/peerp.py "$@"' > /usr/local/bin/peerp && \
    chmod +x /usr/local/bin/peerp

# Simple startup command to launch SSH daemon and stay alive
ENTRYPOINT /usr/sbin/sshd && tail -f /dev/null
