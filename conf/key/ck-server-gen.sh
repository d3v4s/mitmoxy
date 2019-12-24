#!/bin/bash

openssl genrsa -out server.key 4096 && openssl req -new -key server.key -out server.csr -config csr.conf && \
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extensions v3_req -extfile csr.conf || \
echo "[!!] Error while generate certificate and key"