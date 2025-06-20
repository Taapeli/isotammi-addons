#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2013      Nick Hall
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

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------

from gramps.gen.filters._genericfilter import GenericFilterFactory
from gramps.gen.filters.rules import Rule

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext


#-------------------------------------------------------------------------
#
# HasValidDate
#
#-------------------------------------------------------------------------

class HasValidDate(Rule):
    """Rule that matches an event having a valid date"""

#    labels      = [ _('') ]
    name = _('HasValidDate')
    description = _('Matches events with a valid date')
    category = _('Event filters')

    def apply(self, db, event):
        """Rule that matches an event having a valid date"""
        return event.get_date_object().is_valid()

    apply_to_one = apply    # for Gramps 6.0

class HasInValidDate(Rule):
    """Rule that matches an event having a non-blank invalid date"""

#    labels      = [ _('') ]
    name = _('HasInValidDate')
    description = _('Matches events with an invalid date')
    category = _('Event filters')

    def apply(self, db, event):
        """Rule that matches an event having a valid date (or a blank date)"""
        return not (event.get_date_object().get_text() == "" or event.get_date_object().is_valid())
    
    apply_to_one = apply    # for Gramps 6.0
    
