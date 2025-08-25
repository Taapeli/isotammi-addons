#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021-2025      Gramps developers, Kari Kujansuu
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
from gramps.gui import plug
from gramps.version import major_version, VERSION_TUPLE

plug.tool.tool_categories["Isotammi"] = ("Isotammi", _("Isotammi tools"))

# ------------------------------------------------------------------------
#
# FilterParams
#
# See https://github.com/kkujansuu/gramps/edit/master/addons/FilterParams/
#
# ------------------------------------------------------------------------

help_url = (
    "https://gramps-project.org/wiki/index.php/Addon:Isotammi_addons#FilterParams_tool"
)


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {
        "audience": EXPERT,
        "help_url": help_url,
    }

register(
    TOOL,
    id="FilterParams",
    name=_("FilterParams"),
    description=_("Display custom filters and allow changing their parameters"),
    version="1.2.7",
    gramps_target_version=major_version,
    status=STABLE,
    fname="FilterParams.py",
    authors=["Kari Kujansuu"],
    category="Isotammi",
    toolclass="Tool",
    optionclass="Options",
    tool_modes=[TOOL_MODE_GUI],
    **additional_args,
)
