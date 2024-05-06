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
from gramps.version import major_version, VERSION_TUPLE
from gramps.gui import plug

plug.tool.tool_categories["Isotammi"] = ("Isotammi", _("Isotammi tools"))

# ------------------------------------------------------------------------
#
# SuperTool
#
# ------------------------------------------------------------------------
VERSION="1.4.2"
 

if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(
    TOOL,
    id="SuperTool",
    name=_("SuperTool"),
    description=_("General purpose scripting tool that can be used to do 'ad-hoc' queries against a Gramps family tree/database"),
    version=VERSION,
    gramps_target_version=major_version,
    status=STABLE,
    fname="SuperTool.py",
    authors=["Kari Kujansuu"],
    category="Isotammi",
    toolclass="Tool",
    optionclass="Options",
    tool_modes=[TOOL_MODE_GUI, TOOL_MODE_CLI],
    **additional_args,
)

register(
    RULE,
    id="person-genfilter",
    name=_("Generic person filter"),
    description=_("Generic person filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Person",
    namespace="Person",
    **additional_args,
)

register(
    RULE,
    id="family-genfilter",
    name=_("Generic family filter"),
    description=_("Generic family filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Family",
    namespace="Family",
    **additional_args,
)

register(
    RULE,
    id="place-genfilter",
    name=_("Generic place filter"),
    description=_("Generic place filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Place",
    namespace="Place",
    **additional_args,
)

register(
    RULE,
    id="event-genfilter",
    name=_("Generic event filter"),
    description=_("Generic event filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Event",
    namespace="Event",
    **additional_args,
)

register(
    RULE,
    id="citation-genfilter",
    name=_("Generic citation filter"),
    description=_("Generic citation filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Citation",
    namespace="Citation",
    **additional_args,
)

register(
    RULE,
    id="source-genfilter",
    name=_("Generic source filter"),
    description=_("Generic source filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Source",
    namespace="Source",
    **additional_args,
)

register(
    RULE,
    id="repository-genfilter",
    name=_("Generic repository filter"),
    description=_("Generic repository filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Repository",
    namespace="Repository",
    **additional_args,
)

register(
    RULE,
    id="note-genfilter",
    name=_("Generic note filter"),
    description=_("Generic note filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Note",
    namespace="Note",
    **additional_args,
)

register(
    RULE,
    id="media-genfilter",
    name=_("Generic media filter"),
    description=_("Generic media filter"),
    version=VERSION,
    authors=["Kari Kujansuu"],
    authors_email=["kari.kujansuu@gmail.com"],
    gramps_target_version=major_version,
    status=STABLE,
    fname="supertool_genfilter.py",
    ruleclass="GenericFilterRule_Media",
    namespace="Media",
    **additional_args,
)
