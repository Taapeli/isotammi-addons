#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021 Gramps developers, Kari Kujansuu
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""
Gramps registration file
"""
from gramps.version import major_version, VERSION_TUPLE

#------------------------------------------------------------------------
#
# Isotammi XML export  
#
#------------------------------------------------------------------------


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(EXPORT, 
    id    = 'isotammiexportxml',
    name  = _("Isotammi XML export"),
    description =  _("Isotammi XML export"),
    version = '1.0.7',
    gramps_target_version = major_version,
    status = STABLE,
    fname = 'isotammiexportxml.py',
    authors = ["KKu"],
    export_function = 'export_data',
    export_options = 'IsotammiOptionBox',
    export_options_title = _('Isotammi XML export options'),
    extension = "isotammi.gpkg",
    **additional_args,
)


