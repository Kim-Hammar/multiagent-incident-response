#!/bin/bash
# Disguised as kernel worker thread
exec -a "[kworker/0:2-events]" bash -c 'while true; do sleep 600; done'
