#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021     Kari Kujansuu
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
from gramps.version import major_version
from gramps.gui import plug
plug.tool.tool_categories["Isotammi"] = ("Isotammi", _("Isotammi tools"))

#------------------------------------------------------------------------
#
# SuperTool  
#
#------------------------------------------------------------------------

register(TOOL, 
    id    = 'SuperTool',
    name  = _("SuperTool"),
    description =  _(""),
    version = '1.0.3',
    gramps_target_version = major_version,
    status = STABLE,
    fname = 'SuperTool.py',
    authors = ["KKu"],
    category = "Isotammi",
    toolclass = 'Tool',
    optionclass = 'Options',
    tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI]
)

register(
    RULE,
    id="family-genfilter",
    name=_("Generic family filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Family",  # must be rule class name
    namespace="Family",  # one of the primary object classes
)

register(
    RULE,
    id="person-genfilter",
    name=_("Generic person filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Person",  # must be rule class name
    namespace="Person",  # one of the primary object classes
)

register(
    RULE,
    id="place-genfilter",
    name=_("Generic place filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Place",  # must be rule class name
    namespace="Place",  # one of the primary object classes
)

register(
    RULE,
    id="event-genfilter",
    name=_("Generic event filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Event",  # must be rule class name
    namespace="Event",  # one of the primary object classes
)

register(
    RULE,
    id="citation-genfilter",
    name=_("Generic citation filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Citation",  # must be rule class name
    namespace="Citation",  # one of the primary object classes
)

register(
    RULE,
    id="source-genfilter",
    name=_("Generic source filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Source",  # must be rule class name
    namespace="Source",  # one of the primary object classes
)

register(
    RULE,
    id="repository-genfilter",
    name=_("Generic repository filter"),
    description=_("Generic filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Repository",  # must be rule class name
    namespace="Repository",  # one of the primary object classes
)

register(
    RULE,
    id="note-genfilter",
    name=_("Generic filter"),
    description=_("Generic note filter"),
    version="1.0.2",
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="genfilter.py",
    ruleclass="GenericFilterRule_Note",  # must be rule class name
    namespace="Note",  # one of the primary object classes
)


