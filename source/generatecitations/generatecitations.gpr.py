#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
#               2018-2022 Kari Kujansuu
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
from gramps.gui import plug
plug.tool.tool_categories["Isotammi"] = ("Isotammi", _("Isotammi tools"))

#------------------------------------------------------------------------
#
# Generate Source Citations from citations from Digihakemisto etc.
#
#------------------------------------------------------------------------


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(TOOL, 
    id    = 'generatecitations',
    name =  _("Generate source citations from notes"),
    description =  _("Generate source citations from notes"),
    version = '1.2.5',
    gramps_target_version = major_version,
    status = STABLE,
    fname = 'generatecitations.py',
    authors = ["Kari Kujansuu"],
    authors_email = ["kari.kujansuu@gmail.com"],
    category = "Isotammi",
    toolclass = 'GenerateCitations',
    optionclass = 'GenerateCitationsOptions',
    tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI],
    **additional_args,
)
