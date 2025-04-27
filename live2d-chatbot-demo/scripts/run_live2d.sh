#!/bin/bash
rm -rf dist && npm run build && python live2d_display_server.py