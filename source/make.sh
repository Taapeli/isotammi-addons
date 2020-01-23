#!/bin/bash

mkdir -p ../addons/gramps51/listings

export GRAMPSPATH=~/Downloads/gramps-maintenance-gramps51
python3.5 make.py gramps51 as-needed