#!/bin/bash
cd /opt/bots/protocols-bot
source .venv/bin/activate
timeout 5 python3 -m bot 2>&1 || true
