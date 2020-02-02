#!/bin/bash

echo ""
echo "Gramps 5.0"

# Hide filters
mv _* ..

export GRAMPSPATH=/home/kari/Downloads/gramps-maintenance-gramps50
mkdir -p ../addons/gramps50/listings
python3.5 make.py gramps50 as-needed
mv ../_* .

echo ""
echo "Gramps 5.1"
export GRAMPSPATH=/home/kari/Downloads/gramps-maintenance-gramps51
mkdir -p ../addons/gramps51/listings
python3.5 make.py gramps51 as-needed
