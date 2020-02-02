#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2018       Paul Culley
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
Filter rule to match events with with a valid date
"""
register(RULE,
  id    = 'HasValidDate',
  name  = _("Events with a valid date"),
  description = _("Events with a valid date"),
  version = '1.0.5',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = '5.1',
  status = STABLE,
  fname = "_hasvaliddate.py",
  ruleclass = 'HasValidDate',  # must be rule class name
  namespace = 'Event',  # one of the primary object classes
)

register(RULE,
  id    = 'HasInValidDate',
  name  = _("Events with an in valid date"),
  description = _("Events with an invalid date"),
  version = '1.0.5',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = '5.1',
  status = STABLE,
  fname = "_hasvaliddate.py",
  ruleclass = 'HasInValidDate',  # must be rule class name
  namespace = 'Event',  # one of the primary object classes
)

