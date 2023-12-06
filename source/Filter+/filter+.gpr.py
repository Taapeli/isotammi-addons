#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2023 Gramps developers, Kari Kujansuu
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

# See https://github.com/Taapeli/isotammi-addons/tree/master/source/Filter+
# or https://gramps-project.org/wiki/index.php/Addon:Isotammi_addons#Filter.2B

from gramps.version import major_version, VERSION_TUPLE

objs = """
Person
Family
Event
Place
Citation
Source
Repository
Media
Note
"""

help_url = "https://gramps-project.org/wiki/index.php/Addon:Isotammi_addons#Filter.2B"

for obj in objs.splitlines():
    obj = obj.strip()
    if obj == "": continue
    register(GRAMPLET,
             id=obj + "-Filter+",
             name=_(obj + " Filter+"),
             description = _("Gramplet providing a filter (enhanced)"),
             version="1.0.3",
             gramps_target_version=major_version,
             status = STABLE,
             fname="filter+.py",
             height=200,
             gramplet = obj + 'FilterPlus',
             gramplet_title=_("Filter+"),
             navtypes=[obj],
             help_url=help_url,
     )

if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"help_url": help_url}

register(RULE,
  id    = 'HasEventBase+',
  name  = _("HasEventBase+"),
  description = _("HasEventBase+ - used by Filter+"),
  version = '1.0.3',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = major_version,
  status = STABLE,
  fname = "filter+.py",
  ruleclass = 'HasEventBasePlus',  # rule class name
  namespace = 'Event',  # one of the primary object classes
  **additional_args,
)

register(RULE,
  id    = 'HasSourceBase+',
  name  = _("HasSourceBase+"),
  description = _("HasSourceBase+ - used by Filter+"),
  version = '1.0.3',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = major_version,
  status = STABLE,
  fname = "filter+.py",
  ruleclass = 'HasSourceBasePlus',  # rule class name
  namespace = 'Source',  # one of the primary object classes
  **additional_args,
)

