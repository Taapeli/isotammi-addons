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
import functools
import sys
import traceback

try:
    from typing import TYPE_CHECKING
    from typing import Any
    from typing import Callable
    from typing import Dict
    from typing import Generator
    from typing import Iterator
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Type
    from typing import Union
    from gramps.gen.user import User
    from gramps.gen.db import DbGeneric
    from gramps.gen.lib import PrimaryObject
except:
    TYPE_CHECKING = False

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gi.repository import Gtk
from gramps.gen.filters.rules import Rule
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.errors import FilterError

_ = glocale.translation.gettext


# -------------------------------------------------------------------------
#
# Local modules
#
# -------------------------------------------------------------------------
import supertool_engine as engine
import supertool_utils

# -------------------------------------------------------------------------
#
# Helper classes
#
# -------------------------------------------------------------------------
class MyTextView(Gtk.TextView):
    def __init__(self, db):
        # type: (DbGeneric) -> None
        Gtk.TextView.__init__(self)

    def get_text(self):
        # type: () -> str
        buf = self.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        return text.replace("\n", "<br>")

    def set_text(self, text):
        # type: (str) -> None
        self.get_buffer().set_text(text.replace("<br>", "\n"))


class MyBoolean(Gtk.CheckButton):
    def __init__(self, db):
        # type: (DbGeneric) -> None
        Gtk.CheckButton.__init__(self)
        self.show()

    def get_text(self):
        # type: () -> str
        """
        Return the text to save.

        It should be the same no matter the present locale (English or numeric
        types).
        This class sets this to get_display_text, but when localization
        is an issue (events/attr/etc types) then it has to be overridden.

        """
        return str(int(self.get_active()))

    def set_text(self, val):
        # type: (str) -> None
        """
        Set the selector state to display the passed value.
        """
        is_active = bool(int(val))
        self.set_active(is_active)


# -------------------------------------------------------------------------
#
# GenericFilterRules
#
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
        # type: (DbGeneric, User) -> None
        # things we want to do just once, not for every handle
        self.db = db
        self.user = user
        dbstate = self  # self emulates dbstate (i.e. contains dbstate.db)
        self.rule = self.list[0].replace("<br>", " ").strip()

        context = supertool_utils.get_context(db, self.category_name)

        self.initial_statements = self.list[1].replace("<br>", "\n").strip()
        self.initial_statements, files = supertool_utils.process_includes(self.initial_statements)
        self.initial_statements = compile(self.initial_statements, "initial_statements", 'exec')

        self.statements = self.list[2].replace("<br>", "\n").strip()
        self.statements, files = supertool_utils.process_includes(self.statements)
        self.statements = compile(self.statements, "statements", 'exec')

        self.init_env = supertool_utils.get_globals()  # type: Dict[str,Any]
        self.init_env["trans"] = None
        self.init_env["user"] = user
        self.init_env["uistate"] = None # user.uistate is None!
        self.init_env["dbstate"] = dbstate
        self.init_env["db"] = db

        self.init_env["result"] = None
        self.init_env["category"] = self.category_name
        self.init_env["namespace"] = context.objclass
        self.init_env["getproxy"] = functools.partial(supertool_utils.getproxy, db)
        self.init_env["getargs"] = functools.partial(supertool_utils.getargs_dialog, dbstate, None)

        s = self.initial_statements
        if s:
            value, self.init_env = self.execute_func(
                dbstate, None, s, self.init_env, "exec"
            )

    def apply(self, db, obj):
        # type: (DbGeneric, PrimaryObject) -> bool
        self.db = db
        dbstate = self  # self emulates dbstate
        try:
            env = supertool_utils.Lazyenv()
            env.update(self.init_env)
            s = self.statements
            if s:
                value, env = self.execute_func(dbstate, obj, s, env, "exec")
            res, env = self.execute_func(dbstate, obj, self.rule, env)
            return res
        except Exception as e:
            traceback.print_exc()
            self.user.end_progress()
            raise FilterError("SuperTool Query Error", str(e))

    apply_to_one = apply  # for Gramps 6.0

class GenericFilterRule_Family(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Families"
        self.execute_func = engine.execute_family


class GenericFilterRule_Person(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "People"
        self.execute_func = engine.execute_person


class GenericFilterRule_Place(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Places"
        self.execute_func = engine.execute_place


class GenericFilterRule_Event(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Events"
        self.execute_func = engine.execute_event


class GenericFilterRule_Source(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Sources"
        self.execute_func = engine.execute_source


class GenericFilterRule_Citation(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Citations"
        self.execute_func = engine.execute_citation


class GenericFilterRule_Repository(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Repositories"
        self.execute_func = engine.execute_repository


class GenericFilterRule_Note(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Notes"
        self.execute_func = engine.execute_note


class GenericFilterRule_Media(GenericFilterRule):
    def __init__(self, *args):
        # type: (Any) -> None
        GenericFilterRule.__init__(self, *args)
        self.category_name = "Media"
        self.execute_func = engine.execute_media
