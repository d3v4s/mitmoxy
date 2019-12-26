#!/bin/bash

# Simple script to generate certificate and private key
# Develop by Andrea Serra DevAS - Dec 2019

openssl genrsa -out ca.key 4096 && openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt || \
echo "[!!] Error while generate certificate and key"
