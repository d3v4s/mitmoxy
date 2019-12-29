#!/bin/bash

MITMOXY="$0"

while [ -h "$MITMOXY" ] ; do
  ls=$(ls -ld "$MITMOXY")
  link=$(expr "$ls" : '.*-> \(.*\)$')
  if expr "$link" : '/.*' > /dev/null; then
    MITMOXY="$link"
  else
    MITMOXY=$(dirname "$MITMOXY")/"$link"
  fi
done

MITMOXY=$(dirname "$MITMOXY")

cd "$MITMOXY" && ./mitmoxy.py "$@"
