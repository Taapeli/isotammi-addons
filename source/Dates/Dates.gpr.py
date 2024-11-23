# encoding:utf-8
#
# Gramplet addon - for the Gramps GTK+/GNOME based genealogy program
#
# Copyright (C) 2020-2024 Kari Kujansuu, the Isotammi project
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

register(
    GRAMPLET,
    id="Dates",
    name=_("Dates"),
    description=_("Search and replace within Event date strings"),
    authors="Kari Kujansuu",
    authors_email="kari.kujansuu@gmail.com",
    status=STABLE,
    version="1.2.0",
    gramps_target_version=major_version,
    fname="Dates.py",
    gramplet="Dates",
    height=375,
    detached_width=510,
    detached_height=480,
    expand=True,
    gramplet_title=_("Dates"),
    help_url="Addon:Isotammi_addons#Dates",
    include_in_listing=True,
    navtypes=["Event"],
    **additional_args,
)
