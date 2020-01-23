#!/bin/bash

mkdir -p ../addons/gramps50/listings

export GRAMPSPATH=/home/kari/Downloads/gramps-maintenance-gramps51
python3 make.py gramps50 as-needed
