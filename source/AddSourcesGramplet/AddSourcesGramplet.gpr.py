#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025       Kari Kujansuu
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

from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id = "AddSourcesGramplet",
         name = _("AddSourcesGramplet"),
         description = _("Gramplet to add sources"),
         status = STABLE,
         version = '0.9.9',
         gramps_target_version = major_version,
         fname = "AddSourcesGramplet.py",
         gramplet = 'AddSourcesGramplet',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("AddSourcesGramplet"),
         help_url="Addon:Isotammi_addons#Add_Sources_Gramplet",
         include_in_listing = True,
         navtypes=["Event"],
         **additional_args,
        )
