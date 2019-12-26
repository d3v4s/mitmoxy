#!/bin/bash

# FAKE CERTIFICATE GENERATOR SCRIPT
# Used for FakeCertFactory class of Mitmoxy
# Developed by Andrea Serra (DevAS) - Dec 2019

# set arguments
DOMAIN="$1"
BYTES="$2"

# get path of key, csr and cert file
KEY="fake-gen/$DOMAIN.key"
CSR="fake-gen/$DOMAIN.csr"
CRT="fake-gen/$DOMAIN.crt"
CONF="fake-gen/$DOMAIN.conf"

# generate key and certificate with openssl
openssl genrsa -out "$KEY" "$BYTES" && openssl req -new -key "$KEY" -out "$CSR" -config "$CONF" && \
openssl x509 -req -in "$CSR" -CA ca.crt -CAkey ca.key -CAcreateserial -out "$CRT" -days 365 -extensions v3_req -extfile "$CONF"
