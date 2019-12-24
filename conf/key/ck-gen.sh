#!/bin/bash

# Simple script to generate certificate and private key
# Develop by Andrea Serra DevAS 2019

openssl genrsa -out ca.key 4096 && openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt && \
openssl genrsa -out server.key 4096 && openssl req -new -key server.key -out server.csr -config csr.conf && \
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extensions v3_req -extfile csr.conf || \
echo "[!!] Error while generate certificate and key"
# cat server.crt ca.crt > chain.crt
