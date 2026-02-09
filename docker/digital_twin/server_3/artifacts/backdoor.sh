#!/bin/bash
# Disguised as sshd listener process
exec -a "/usr/sbin/sshd -D [listener]" bash -c 'while true; do sleep 300; done'
