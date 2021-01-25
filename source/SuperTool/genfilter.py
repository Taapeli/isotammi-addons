#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020       Kari Kujansuu
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

# -------------------------------------------------------------------------
#
# Standard Python modules
#
# -------------------------------------------------------------------------
import traceback


from gi.repository import Gtk


# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gramps.gen.filters.rules import Rule

from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext


class MyTextView(Gtk.TextView):
    def __init__(self, db):
        Gtk.TextView.__init__(self)

    def get_text(self):
        buf = self.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        return text.replace("\n", "<br>")

    def set_text(self, text):
        self.get_buffer().set_text(text.replace("<br>", "\n"))


class MyBoolean(Gtk.CheckButton):
    def __init__(self, db):
        Gtk.CheckButton.__init__(self)
        self.show()

    def get_text(self):
        """
        Return the text to save.

        It should be the same no matter the present locale (English or numeric
        types).
        This class sets this to get_display_text, but when localization
        is an issue (events/attr/etc types) then it has to be overridden.

        """
        return str(int(self.get_active()))

    def set_text(self, val):
        """
        Set the selector state to display the passed value.
        """
        is_active = bool(int(val))
        self.set_active(is_active)


# -------------------------------------------------------------------------
# Generic filter rule
# -------------------------------------------------------------------------
class GenericFilterRule(Rule):
    "Generic filter rule"

    labels = [
        #        (_("Ask for arguments"), MyBoolean),
        (_("Rule:"), MyTextView),
        (_("Initial statements:"), MyTextView),
        (_("Statements:"), MyTextView),
    ]
    name = _("Generic filter rule")

    description = "Generic filter rule"
    category = _("Isotammi filters")

    def prepare(self, db, user):
        # things we want to do just once, not for every handle
        
        self.db = db
        dbstate = self  # self emulates dbstate
        self.rule = self.list[0].replace("<br>", " ").strip()
        self.initial_statements = self.list[1].replace("<br>", "\n").strip()
        self.statements = self.list[2].replace("<br>", "\n").strip()

        self.init_env = {}  # type: Dict[str,Any]
        s = self.initial_statements
        if s:
            value, self.init_env = self.execute_func(dbstate, None, s, self.init_env, "exec")

    #         if len(self.list) == 1:
    #             self.list = ["0", self.list[0]]
    #         self.rule = self.list[1]
    #         print("Rule:", self.rule)
    #         if int(self.list[0]):
    #             OkDialog("Rule",self.rule)

    def apply(self, db, obj):
        self.db = db
        dbstate = self  # self emulates dbstate
        try:
            env = {}
            env.update(self.init_env)
            s = self.statements
            if s:
                value, env = self.execute_func(dbstate, obj, s, env, "exec")
            res, env = self.execute_func(dbstate, obj, self.rule, env)
            return res
        except:
            traceback.print_exc()
            return False


class GenericFilterRule_Family(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_family


class GenericFilterRule_Person(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_person


class GenericFilterRule_Place(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_place

class GenericFilterRule_Event(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_event

class GenericFilterRule_Source(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_source

class GenericFilterRule_Citation(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_citation

class GenericFilterRule_Repository(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_repository

class GenericFilterRule_Note(GenericFilterRule):
    def __init__(self, *args):
        GenericFilterRule.__init__(self, *args)
        self.execute_func = engine.execute_note

import supertool_engine as engine
