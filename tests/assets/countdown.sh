#!/usr/bin/env bash
for x in 2 1 Done; do echo ${x}; done
if [ "$1" == "dodgy" ]; then exit 13; else exit 0; fi
