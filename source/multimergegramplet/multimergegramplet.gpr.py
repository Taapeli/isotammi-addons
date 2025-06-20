#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
# Copyright (C) 2019-2021 Kari Kujansuu
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
         id="Multimergegramplet Gramplet",
         name=_("Multimerge Gramplet"),
         description = _("Multimerge Gramplet"),
         status=STABLE, 
         fname="multimergegramplet.py",
         authors = ['Kari Kujansuu', 'Nick Hall'],
         authors_email = ['kari.kujansuu@gmail.com', 'nick-h@gramps-project.org'],
         height=230,
         expand=True,
         gramplet = 'MultiMergeGramplet',
         gramplet_title=_("MultiMergeGramplet"),
         detached_width = 510,
         detached_height = 480,
         version = '1.2.6',
         gramps_target_version = major_version,
         help_url="http://github.com/Taapeli/isotammi-addons/tree/master/source/multimergegramplet/README.md",
         navtypes=["Person","Family","Place","Source","Repository","Note","Event",
                   "Citation","Media"],
         **additional_args,
         )
