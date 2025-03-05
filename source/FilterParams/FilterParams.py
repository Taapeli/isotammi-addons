#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021-2025      Gramps developers, Kari Kujansuu

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

import os
import re
import traceback
from collections import defaultdict
from pprint import pprint

try:
    from typing import (
        Any,
        Callable,
        Dict,
        Generator,
        Iterator,
        List,
        Optional,
        Set,
        Tuple,
    )
    from gramps.gen.dbstate import DbState
    from gramps.gen.db import DbTxn, DbGeneric
    from gramps.gen.lib import BaseObject
    from gramps.gen.user import User
    from gramps.gui import DisplayState
    from gramps.gen.filters import GenericFilter
    from gramps.gen.filters.rules import Rule
except:
    pass

from gi.repository import Gdk, GObject, Gtk

import gramps.gen.filters
from gramps.gen.config import config as configman
from gramps.gen.const import CUSTOM_FILTERS
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.datehandler import displayer
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.errors import FilterError, WindowActiveError
from gramps.gen.filters import GenericFilterFactory, reload_custom_filters
from gramps.gen.filters.rules import MatchesFilterBase
from gramps.gen.lib import (
    Citation,
    Event,
    Family,
    Media,
    Note,
    Person,
    Place,
    Repository,
    Source,
)
from gramps.gen.utils.callman import CallbackManager
from gramps.gen.utils.db import family_name
from gramps.gen.utils.db import get_birth_or_fallback
from gramps.gen.utils.string import conf_strings
from gramps.gui.dbguielement import DbGUIElement
from gramps.gui.dialog import ErrorDialog, QuestionDialog
from gramps.gui.editors import (
    EditCitation,
    EditEvent,
    EditFamily,
    EditMedia,
    EditNote,
    EditPerson,
    EditPlace,
    EditRepository,
    EditSource,
)
from gramps.gui.editors.filtereditor import MyEntry
from gramps.gui.editors.filtereditor import (
    EditFilter,
    MyBoolean,
    MyFilters,
    MyID,
    MyInteger,
    MyLesserEqualGreater,
    MyList,
    MyPlaces,
    MySelect,
    MySource,
    _name2typeclass,
)
from gramps.gui.glade import Glade
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.plug import tool
from gramps.gui.user import User
from gramps.gui.views.listview import ListView
from gramps.gui.widgets import DateEntry

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


regex_tip = _(
    "Interpret the contents of string fields as regular "
    "expressions.\n"
    "A decimal point will match any character. "
    "A question mark will match zero or one occurences "
    "of the previous character or group. "
    "An asterisk will match zero or more occurences. "
    "A plus sign will match one or more occurences. "
    "Use parentheses to group expressions. "
    "Specify alternatives using a vertical bar. "
    "A caret will match the start of a line. "
    "A dollar sign will match the end of a line."
)


# -------------------------------------------------------------------------
#
# Tool
#
# -------------------------------------------------------------------------
class Tool(tool.Tool, ManagedWindow):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        # type: (Any, Any, Any, str, Callable) -> None
        tool.Tool.__init__(self, dbstate, options_class, name)
        ManagedWindow.__init__(self, user.uistate, [], self.__class__, modal=False)
        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        self.options_class = options_class
        self.name = name
        self.config = configman.register_manager(name)
        self.config.register("lastfilter.namespace", "")
        self.config.register("lastfilter.filtername", "")

        self.frame = None
        self.categories = [
            "Person",
            "Family",
            "Event",
            "Place",
            "Citation",
            "Source",
            "Repository",
            "Media",
            "Note",
        ]
        self.categories_translated = [_(cat) for cat in self.categories]
        self.colors = [
            Gdk.RGBA(0.75, 0.75, 0.75, 0.250),
            Gdk.RGBA(0.75, 0.75, 0.99, 0.250),
            Gdk.RGBA(0.75, 0.99, 0.99, 0.250),
            Gdk.RGBA(0.75, 0.99, 0.75, 0.250),
            Gdk.RGBA(0.99, 0.99, 0.75, 0.250),
            Gdk.RGBA(0.99, 0.75, 0.75, 0.250),
            Gdk.RGBA(0.99, 0.75, 0.99, 0.250),
        ]
        self.use_colors = True

        self.database_changed_key = self.dbstate.connect(
            "database-changed", self.database_changed
        )
        self.filters_changed_key = self.uistate.connect(
            "filters-changed", self.filters_changed
        )

        self.initialize_category_and_filtername()
        self.dialog = self.create_gui()

        self.set_window(self.dialog, None, _("Filter Parameters"))
        self.dialog.show_all()

    def build_menu_names(self, obj):
        # type: (Any) -> Tuple[str,str]
        """
        Needed by ManagedWindow to build the Windows menu
        """
        return ("FilterParams", 'FilterParams')

    def database_changed(self, db):
        # type: (DbGeneric) -> None
        # print("database_changed", db, db.is_open())
        if db.is_open():
            self.close_clicked(None)  # can't handle database change

    def enable_buttons(self, value):
        # type: (bool) -> None
        self.edit_button.set_sensitive(value)
        self.delete_button.set_sensitive(value)
        self.execute_button.set_sensitive(value)
        self.update_button.set_sensitive(value)

    def populate_filters(self, category):
        # type: (str) -> None
        self.filterdb = gramps.gen.filters.CustomFilters
        filters = self.filterdb.get_filters_dict(category)
        self.filternames = []
        self.combo_filters.get_model().clear()
        current_index = -1
        for i, filter in enumerate(filters.values()):
            filtername = filter.get_name()
            self.filternames.append(filtername)
            self.combo_filters.append_text(filtername)
            # activate the current filter
            # or, after deleting a filter, activate the next one
            if current_index == -1 and filtername.lower() >= self.current_filtername.lower():
                current_index = i
        if len(self.filternames) > 0:
            if current_index == -1:
                current_index = len(self.filternames) - 1  # activate the last in list
            self.combo_filters.set_active(current_index)
            self.enable_buttons(True)
        else:
            self.enable_buttons(False)

    def filters_changed(self, namespace):
        # type: (str) -> None
        if namespace == self.current_category:
            self.populate_filters(namespace)

    def initialize_category_and_filtername(self):
        # type: () -> None
        self.current_filtername = ""
        self.filternames = []
        category = self.uistate.viewmanager.active_page.get_category()  # type: str
        if category == "People":
            category = "Person"
        if category.endswith("ies"):
            category = category[0:-3] + "y"
        if category.endswith("s"):
            category = category[0:-1]
        self.current_category = category

        self.config.load()
        namespace = self.config.get("lastfilter.namespace")
        if namespace:
            self.current_category = namespace
            filtername = self.config.get("lastfilter.filtername")
            if filtername:
                self.current_filtername = filtername
        self.namespace = self.current_category

    def create_gui(self):
        # type: () -> Gtk.Dialog
        glade = Glade(toplevel="dialog1")
        self.dialog = glade.toplevel
        self.combo_categories = glade.get_child_object("combo_categories")
        self.combo_filters = glade.get_child_object("combo_filters")
        self.add_button = glade.get_child_object("add_button")
        self.edit_button = glade.get_child_object("edit_button")
        self.clone_button = glade.get_child_object("clone_button")
        self.delete_button = glade.get_child_object("delete_button")

        self.execute_button = glade.get_child_object("execute_button")
        self.update_button = glade.get_child_object("update_button")
        self.close_button = glade.get_child_object("close_button")
        self.box = glade.get_child_object("box")
        self.errorMsg = glade.get_child_object("errorMsg")

        if 0:
            glade.connect_signals(
                {
                    "on_filter_changed": self.on_filter_changed,
                    "add_new_filter": self.add_new_filter,
                    "edit_filter": self.edit_filter,
                    "delete_filter": self.delete_filter,
                    "execute_clicked": self.execute_clicked,
                    "update_clicked": self.update_clicked,
                    "close_clicked": self.close_clicked,
                    "on_category_changed": self.on_category_changed,
                }
            )
        if 1:
            self.combo_filters.connect("changed", self.on_filter_changed)

            self.add_button.connect("clicked", self.add_new_filter)
            self.edit_button.connect("clicked", self.edit_filter)
            self.clone_button.connect("clicked", self.clone_filter)
            self.delete_button.connect("clicked", self.delete_filter)

            self.execute_button.connect("clicked", self.execute_clicked)
            self.update_button.connect("clicked", self.update_clicked)
            self.close_button.connect("clicked", self.close_clicked)

        for cat in self.categories_translated:
            self.combo_categories.append_text(cat)
        self.combo_categories.connect("changed", self.on_category_changed)

        if self.current_category not in self.categories:
            self.current_category = "Person"
        i = self.categories.index(self.current_category)
        self.combo_categories.set_active(i)

        # put the dialog close to the parent window
        x, y = self.parent_window.get_position()
        self.dialog.move(x + 100, y + 100)

        self.dialog.connect(
            "delete-event", lambda x, y: self.close_clicked(self.dialog)
        )
        return self.dialog

    def on_category_changed(self, combo):
        # type: (Gtk.ComboBox) -> None
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        model = combo.get_model()
        cat_name_translated = model[tree_iter][0]
        i = self.categories_translated.index(cat_name_translated)
        self.current_category = self.categories[i]
        if self.frame:
            self.frame.destroy()
            self.frame = None
        self.populate_filters(self.current_category)

    def get_color(self, level):
        # type: (int) -> str
        return self.colors[level % len(self.colors)]

    def get_all_handles(self, category):
        # type: (str) -> Optional[List[str]]
        # method copied from gramps/gui/editors/filtereditor.py
        # Why use iter for some and get for others?
        if category == "Person":
            return self.db.iter_person_handles()
        elif category == "Family":
            return self.db.iter_family_handles()
        elif category == "Event":
            return self.db.get_event_handles()
        elif category == "Source":
            return self.db.get_source_handles()
        elif category == "Citation":
            return self.db.get_citation_handles()
        elif category == "Place":
            return self.db.iter_place_handles()
        elif category == "Media":
            return self.db.get_media_handles()
        elif category == "Repository":
            return self.db.get_repository_handles()
        elif category == "Note":
            return self.db.get_note_handles()
        else:
            return None

    def execute_clicked(self, _widget):
        # type: (str) -> None
        class User2:
            """
            Helper class to provide "can_cancel" functionality to
            the progress indicator used by gramps.gen.filters._genericfilter.GenericFilter.apply().
            Replaces the gramps.gui.user.User class for this case.
            Code copied from gramps/gui/user.py.
            """

            def __init__(self, user):
                # type: (User) -> None
                self.parent = user.parent
                self.uistate = user.uistate
                self.parent = user.parent

            def begin_progress(self, title, message, steps):
                # type: (str,str,int) -> None
                # Parameter "can_cancel" added to ProgressMeter creation.
                from gramps.gui.utils import ProgressMeter

                self._progress = ProgressMeter(
                    title, parent=self.parent, can_cancel=True
                )
                if steps > 0:
                    self._progress.set_pass(message, steps, ProgressMeter.MODE_FRACTION)
                else:
                    self._progress.set_pass(message, mode=ProgressMeter.MODE_ACTIVITY)

            def step_progress(self):
                # type: () -> None
                res = self._progress.step()
                if res:
                    self.end_progress()
                    raise StopIteration

            def end_progress(self):
                # type: () -> None
                if self._progress:
                    self._progress.close()
                self._progress = None

        user = User2(self.user)

        # code copied from gramps/gui/editors/filtereditor.py (test_clicked)
        if not self.current_category:
            return
        if not self.current_filtername:
            return
        try:
            self.update_params()
            filter = self.getfilter(self.current_category, self.current_filtername)
            handle_list = filter.apply(self.dbstate.db, id_list=None, user=user)
        except StopIteration:
            return
        except FilterError as msg:
            traceback.print_exc()
            (msg1, msg2) = msg.messages()
            ErrorDialog(msg1, msg2, parent=self.window)
            return
        ShowResults(
            self.dbstate,
            self.uistate,
            [],
            handle_list,
            self.current_filtername,
            self.current_category,
            self.user,
            self.options_class,
            self.name,
        )

    def update(self, current_filtername=None):
        # type: (str) -> None
        if current_filtername:
            self.current_filtername = current_filtername
        self.filterdb.save()
        reload_custom_filters()
        self.uistate.emit("filters-changed", (self.current_category,))

    def selection_callback(self, filterdb, filtername):
        # type: (str,str) -> None
        self.update(filtername)

    # methods copied from gramps/gui/editors/filtereditor.py
    def add_new_filter(self, obj):
        # type: (str) -> None
        self.filterdb = gramps.gen.filters.CustomFilters
        the_filter = GenericFilterFactory(self.current_category)()
        EditFilter(
            self.current_category,
            self.dbstate,
            self.uistate,
            self.track,
            the_filter,
            self.filterdb,
            selection_callback=self.selection_callback,
        )

    def edit_filter(self, obj):
        # type: (str) -> None
        if not self.current_category:
            return
        if not self.current_filtername:
            return
        self.filterdb = gramps.gen.filters.CustomFilters
        the_filter = self.getfilter(self.current_category, self.current_filtername)
        EditFilter(
            self.current_category,
            self.dbstate,
            self.uistate,
            self.track,
            the_filter,
            self.filterdb,
            selection_callback=self.selection_callback,
        )

    def clone_filter(self, obj):  # not used
        # type: (str) -> None
        print("clone_filter")
        if not self.current_category:
            return
        if not self.current_filtername:
            return
        old_filter = self.getfilter(self.current_category, self.current_filtername)
        the_filter = GenericFilterFactory(self.current_category)(old_filter)
        the_filter.set_name("")
        EditFilter(
            self.current_category,
            self.dbstate,
            self.uistate,
            self.track,
            the_filter,
            self.filterdb,
            update=self.update,
        )

    def delete_filter(self, obj):
        # type: (str) -> None
        if not self.current_category:
            return
        if not self.current_filtername:
            return
        gfilter = self.getfilter(self.current_category, self.current_filtername)
        name = gfilter.get_name()
        using_filters = self.check_recursive_filters(self.current_category, name)
        if using_filters:
            QuestionDialog(
                _("Delete Filter?"),
                _(
                    "This filter is currently being used "
                    "as the base for other filters. Deleting "
                    "this filter will result in removing all "
                    "other filters that depend on it:\n"
                    + ", ".join(f.get_name() for f in using_filters)
                ),
                _("Delete Filter"),
                self._do_delete_selected_filter,
                parent=self.dialog,
            )
        else:
            self._do_delete_selected_filter()

    def _find_dependent_filters(self, space, gfilter, filter_set):
        # type: (str,GenericFilter,Set[GenericFilter]) -> None
        """
        This method recursively calls itself to find all filters that
        depend on the given filter, either directly through one of the rules,
        or through the chain of dependencies.

        The filter_set is amended with the found filters.
        """
        # Add itself to the filter_set
        filter_set.add(gfilter)
        name = gfilter.get_name()
        filters = self.filterdb.get_filters(space)
        for the_filter in filters:
            if the_filter.get_name() == name:
                continue
            if the_filter in filter_set:  # prevent infinite recursion
                continue
            for rule in the_filter.get_rules():
                values = list(rule.values())
                if issubclass(rule.__class__, MatchesFilterBase) and (name in values):
                    self._find_dependent_filters(space, the_filter, filter_set)
                    break

    def check_recursive_filters(self, space, name):
        # type: (str,str) -> List[GenericFilter]
        using_filters = []
        for the_filter in self.filterdb.get_filters(space):
            for rule in the_filter.get_rules():
                values = list(rule.values())
                if issubclass(rule.__class__, MatchesFilterBase) and (name in values):
                    using_filters.append(the_filter)
        return using_filters

    def _do_delete_selected_filter(self):
        # type: () -> None
        if not self.current_category:
            return
        if not self.current_filtername:
            return
        gfilter = self.getfilter(self.current_category, self.current_filtername)
        self._do_delete_filter(self.current_category, gfilter)
        self.update()
        self.combo_filters.grab_focus()

    def _do_delete_filter(self, space, gfilter):
        # type: (str,str) -> None
        # Find everything we need to remove
        filter_set = set()  # type: Set[GenericFilter]
        self._find_dependent_filters(space, gfilter, filter_set)

        # Remove what we found
        filters = self.filterdb.get_filters(space)
        list(map(filters.remove, filter_set))

    def update_clicked(self, _widget):
        # type: (str) -> None
        self.update_params()
        self.filterdb.save()

    def close_clicked(self, _widget):
        # type: (str) -> None
        self.uistate.disconnect(self.filters_changed_key)
        self.dbstate.disconnect(self.database_changed_key)
        reload_custom_filters()  # so that our (non-saved) changes will be discarded
        self.close()

    def get_widgets(self, arglist, filtername):
        # type: (List[str],str) -> MyEntry
        # Code copied from gramps/gui/editors/filtereditor.py

        # filterdb = gramps.gen.filters.CustomFilters  # hack so that infamilyrule works

        pos = 0
        tlist = []
        for v in arglist:
            if isinstance(v, tuple):
                # allows filter to create its own GUI element
                l = Gtk.Label(label=v[0], halign=Gtk.Align.END)
            else:
                l = Gtk.Label(label=v, halign=Gtk.Align.END)
            l.show()
            if v == _("Place:"):
                t = MyPlaces([])
            elif v in [_("Reference count:"), _("Number of instances:")]:
                t = MyInteger(0, 999)
            elif v == _("Reference count must be:"):
                t = MyLesserEqualGreater()
            elif v == _("Number must be:"):
                t = MyLesserEqualGreater(2)
            elif v == _("Number of generations:"):
                t = MyInteger(1, 32)
            elif v == _("ID:"):
                t = MyID(self.dbstate, self.uistate, self.track, self.namespace)
            elif v == _("Source ID:"):
                t = MySource(self.dbstate, self.uistate, self.track)
            elif v == _("Filter name:"):
                t = MyFilters(self.filterdb.get_filters(self.namespace), filtername)
            # filters of another namespace, name may be same as caller!
            elif v == _("Person filter name:"):
                t = MyFilters(self.filterdb.get_filters("Person"))
            elif v == _("Event filter name:"):
                t = MyFilters(self.filterdb.get_filters("Event"))
            elif v == _("Source filter name:"):
                t = MyFilters(self.filterdb.get_filters("Source"))
            elif v == _("Repository filter name:"):
                t = MyFilters(self.filterdb.get_filters("Repository"))
            elif v == _("Place filter name:"):
                t = MyFilters(self.filterdb.get_filters("Place"))
            elif v in _name2typeclass:
                additional = None
                if v in (_("Event type:"), _("Personal event:"), _("Family event:")):
                    additional = self.db.get_event_types()
                elif v == _("Personal attribute:"):
                    additional = self.db.get_person_attribute_types()
                elif v == _("Family attribute:"):
                    additional = self.db.get_family_attribute_types()
                elif v == _("Event attribute:"):
                    additional = self.db.get_event_attribute_types()
                elif v == _("Media attribute:"):
                    additional = self.db.get_media_attribute_types()
                elif v == _("Relationship type:"):
                    additional = self.db.get_family_relation_types()
                elif v == _("Note type:"):
                    additional = self.db.get_note_types()
                elif v == _("Name type:"):
                    additional = self.db.get_name_types()
                elif v == _("Surname origin type:"):
                    additional = self.db.get_origin_types()
                elif v == _("Place type:"):
                    additional = sorted(
                        self.db.get_place_types(), key=lambda s: s.lower()
                    )
                t = MySelect(_name2typeclass[v], additional)
            elif v == _("Inclusive:"):
                t = MyBoolean(_("Include selected Gramps ID"))
            elif v == _("Case sensitive:"):
                t = MyBoolean(_("Use exact case of letters"))
            elif v == _("Regular-Expression matching:"):
                t = MyBoolean(_("Use regular expression"))
            elif v == _("Include Family events:"):
                t = MyBoolean(_("Also family events where person is spouse"))
            elif v == _("Primary Role:"):
                t = MyBoolean(_("Only include primary participants"))
            elif v == _("Tag:"):
                taglist = [""]
                taglist = taglist + [
                    tag.get_name() for tag in self.dbstate.db.iter_tags()
                ]
                t = MyList(taglist, taglist)
            elif v == _("Confidence level:"):
                t = MyList(
                    list(map(str, list(range(5)))),
                    [_(conf_strings[i]) for i in range(5)],
                )
            elif v == _("Date:"):
                t = DateEntry(self.uistate, self.track)
            elif v == _("Day of Week:"):
                long_days = displayer.long_days
                days_of_week = long_days[2:] + long_days[1:2]
                t = MyList(list(map(str, range(7))), days_of_week)
            elif v == _("Units:"):
                t = MyList([0, 1, 2], [_("kilometers"), _("miles"), _("degrees")])
            elif isinstance(v, tuple):
                # allow filter to create its own GUI element
                t = v[1](self.db)
            else:
                t = MyEntry()
            t.set_hexpand(True)
            tlist.append(t)
            pos += 1
        return tlist[0]

    class MyGrid(Gtk.Grid):
        """
        Gtk.Grid that is easier to use; just call .add() to add a new item.
        Set argument 'incrow' to False if next item should be on the same row.
        """

        def __init__(self):
            # type: () -> None
            Gtk.Grid.__init__(self)
            self.set_margin_left(10)
            self.set_margin_top(0)
            self.set_margin_right(10)
            self.set_margin_bottom(10)
            self.row = 0
            self.col = 0

        def add(self, widget, incrow=True):
            # type: (str,bool) -> None
            self.attach(widget, self.col, self.row, 1, 1)
            if incrow:
                self.row += 1
                self.col = 0
            else:
                self.col += 1

    def update_params(self, *args):
        # type: (str) -> None
        for filter, invert_checkbox, logical_combo in self.filterparams:
            filter.set_invert(invert_checkbox.get_active())
            filter.set_logical_op(self.ops[logical_combo.widget.get_active()])

        for rule, paramindex, entry in self.entries:
            value = str(entry.get_text())  # type: Any
            rule.list[paramindex] = value
            # print(value, entry)
        for rule, use_regex in self.regexes:
            value = use_regex.get_active()
            rule.use_regex = value
        for oldvalue, entries in self.values.items():
            value = None
            for entry, rule, paramindex in entries:
                if value is None:
                    value = entry.get_text()
                else:
                    rule.list[paramindex] = value
                entry.set_text(value)
        self.on_filter_changed(self.combo_filters, reload=False)

    def getfilter(self, category, filtername):
        # type: (str,str) -> GenericFilter
        filters = self.filterdb.get_filters_dict(category)
        return filters.get(filtername)

    def clean(self, text):
        # type: (str) -> str
        if len(text) > 80:
            text = text[0:77] + "..."
        text = text.replace("<", "&lt;")
        return text

    def addfilter(self, grid, category, filter, level):
        # type: (Gtk.Grid,str,GenericFilter,int) -> None
        """
        Add the GUI widgets for the filter in the supplied Gtk.Grid.
        The grid is already contained in a Gtk.Frame with appropriate label.

        Saves the widget in three arrays (entries, filterparams and regexes).
        """

        if level > 20:
            lbl = Gtk.Label()
            lbl.set_halign(Gtk.Align.START)
            msg = (
                "<span color='red' size='larger'>"
                + _("Too deeply nested filters")
                + "</span>"
            )
            lbl.set_markup(msg)
            grid.add(lbl)
            self.errorMsg.set_markup(msg)
            return

        clsname = filter.__class__.__name__

        invert_checkbox = Gtk.CheckButton("invert")
        invert_checkbox.set_active(filter.get_invert())
        invert_checkbox.set_tooltip_text(
            _("Return values that do not match the filter rules")
        )

        choices = [
            _("All rules must apply"),
            _("At least one rule must apply"),
            _("Exactly one rule must apply"),
        ]
        self.ops = ["and", "or", "one"]
        op = filter.get_logical_op()
        combo = self.MyCombo(choices)
        combo.widget.set_active(self.ops.index(op))
        hbox = Gtk.HBox()
        hbox.add(invert_checkbox)
        if len(filter.get_rules()) > 1:
            hbox.add(combo.widget)
        grid.add(hbox)

        self.filterparams.append((filter, invert_checkbox, combo))

        for rule in filter.get_rules():
            lab = Gtk.Label(" ")  # to separate the frames
            grid.add(lab)

            clsname = rule.__class__.__name__
            lbl = Gtk.Label(str(level) + ". " + clsname)
            lbl.set_halign(Gtk.Align.START)

            frame, grid2 = self.add_frame(
                grid,
                level,
                "<b>"
                + self.clean(_(rule.name))
                + "</b>\n"
                + self.clean(_(rule.description)),
                tooltip=_(rule.name) + "\n\n" + _(rule.description),
            )
            for paramindex, (caption1, value) in enumerate(zip(rule.labels, rule.list)):
                if type(caption1) is tuple:
                    caption = caption1[0]
                else:
                    caption = caption1
                lbl = Gtk.Label(caption)
                lbl.set_halign(Gtk.Align.START)
                self.namespace = category
                entry = self.get_widgets([caption1], filter.get_name())
                entry.set_text(value)
                entry.set_halign(Gtk.Align.START)
                self.entries.append((rule, paramindex, entry))

                # grid2.add(lbl, False)
                if isinstance(entry, MyFilters):
                    grid2.add(lbl)
                else:
                    grid2.add(lbl, False)
                grid2.add(entry)

                if isinstance(
                    entry, MyID
                ):  # link ID fields if they have the same value
                    if value in self.values:
                        entry.set_sensitive(False)
                    self.values[value].append((entry, rule, paramindex))
                    entry.entry.connect("changed", self.update_params)
                if isinstance(entry, MyFilters):
                    entry.connect("changed", self.update_params)
                if self.is_filter_reference(clsname, caption, entry):
                    matchcategory = self.get_matchcategory(clsname, caption, entry)
                    if matchcategory == "":
                        matchcategory = category
                    filtername = rule.list[paramindex]

                    self.add_frame_and_filter(
                        grid2, matchcategory, filtername, "", level
                    )
                else:
                    pass

            if rule.allow_regex:
                use_regex = Gtk.CheckButton(label=_("Use regular expressions"))
                use_regex.set_tooltip_text(regex_tip)
                use_regex.set_active(rule.use_regex)
                grid2.add(use_regex)
                self.regexes.append((rule, use_regex))

    def is_filter_reference(self, clsname, caption, entry):
        if isinstance(entry, MyFilters):
            return True
        if caption.lower().endswith("filter name:"):
            return True
        if clsname.startswith("Matches") and clsname.endswith("Filter"):
            return True  # e.g. MatchesEventFilter
        if clsname.startswith("Is") and clsname.endswith("FilterMatch"):
            return True  # e.g. IsChildOfFilterMatch
        return False

    def get_matchcategory(self, clsname, caption, entry):
        if caption.lower().endswith(" filter name:"):
            return caption.split()[0].capitalize()
        if clsname.startswith("Matches") and clsname.endswith("Filter"):
            return clsname.replace("Matches", "").replace(
                "Filter", ""
            )  # e.g. MatchesEventFilter
        return ""

    def add_frame_and_filter(self, grid, category, filtername, caption, level):
        # type: (Gtk.Grid,str,str,int) -> Gtk.Frame
        """
        Add a new Frame inside grid and a new Grid inside that Frame.
        Call addfilter to add a new frame inside the new grid to represent filter named 'filtername'.
        """
        filter = self.getfilter(category, filtername)
        if filter is None:  # not found for some reason
            lbl = Gtk.Label()
            lbl.set_halign(Gtk.Align.START)
            msg = (
                "<span color='red' size='larger'>"
                + _("Error: filter '%s' not found in namespace '%s'")
                % (filtername, category)
                + "</span>"
            )
            lbl.set_markup(msg)
            grid.add(lbl)
            self.errorMsg.set_markup(msg)
            return
        # caption = "<b>"+self.clean(filtername)+"</b>"
        if filter.comment.strip():
            caption += "\n" + self.clean(filter.comment)

        tooltip = filtername + "\n\n" + filter.comment
        frame, grid2 = self.add_frame(grid, level, caption, tooltip)
        self.addfilter(grid2, category, filter, level + 1)
        return frame

    def add_frame(self, grid, level, caption, tooltip=None):
        # type: (Gtk.Grid,int,str,str) -> Tuple[Gtk.Frame, Gtk.Grid]
        "Add a new Frame inside grid and a new Grid inside that Frame"
        lbl = Gtk.Label()
        lbl.set_halign(Gtk.Align.START)
        lbl.set_markup(caption)
        frame2 = Gtk.Frame()
        frame2.set_label_widget(lbl)
        if self.use_colors:
            frame2.override_background_color(
                Gtk.StateFlags.NORMAL, self.get_color(level)
            )

        if grid:
            grid.add(frame2)
        grid2 = self.MyGrid()
        frame2.add(grid2)
        frame2.set_tooltip_text(tooltip)
        return frame2, grid2

    def update_filter_reference(self, entry, paramindex, rule):
        referenced_filter_name = entry.get_text()
        rule.list[paramindex] = referenced_filter_name
        self.update_params()
        # self.update()
        self.filters_changed(self.current_category)

    def on_filter_changed(self, combo, reload=True):
        # type: (Gtk.ComboBox) -> None
        #         import random
        #         random.shuffle(self.colors)
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        model = combo.get_model()
        try:
            filtername = model[tree_iter][0]
        except:
            traceback.print_exc()
            return

        # load from xml file, any temporary changes are lost
        if reload:
            reload_custom_filters()
        self.filterdb = gramps.gen.filters.CustomFilters

        self.current_filtername = filtername
        if self.frame:
            self.frame.destroy()
        self.entries = []  # type: List[Tuple[Rule,int,Gtk.Entry]]
        self.filterparams = (
            []
        )  # type: List[Tuple[GenericFilter,Gtk.CheckButton,Gtk.ComboBox]]
        self.regexes = []  # type: List[Tuple[Rule,Gtk.CheckButton]]
        self.values = defaultdict(
            list
        )  # type: Dict[str, List[Tuple[Gtk.Entry,Rule,int]]]

        self.config.set("lastfilter.namespace", self.current_category)
        self.config.set("lastfilter.filtername", filtername)
        self.config.save()

        caption = "<b>" + filtername + "</b>"
        self.errorMsg.set_text("")

        frame2 = self.add_frame_and_filter(
            None, self.current_category, filtername, filtername, 0
        )

        self.box.add(frame2)
        self.frame = frame2
        self.dialog.resize(1, 1)  # shrink to minimum size needed
        self.dialog.show_all()

    class MyWidget:
        def __init__(self, widget):
            # type: (Gtk.Widget) -> None
            self.widget = widget

        def set_value(self, text):
            # type: (Any) -> None
            self.widget.set_text(text)

        def get_value(self):
            # type: () -> Any
            return self.widget.get_text()

    class MyCheckBox(MyWidget):
        def __init__(self):
            # type: () -> None
            self.widget = Gtk.CheckButton()

        def set_value(self, value):
            # type: (bool) -> None
            self.widget.set_active(value)

        def get_value(self):
            # type: () -> bool
            return self.widget.get_active()

    class MySpin(MyWidget):
        def __init__(self):
            # type: () -> None
            self.widget = Gtk.SpinButton()
            self.widget.set_numeric(True)
            adjustment = Gtk.Adjustment(upper=100, step_increment=1, page_increment=10)
            self.widget.set_adjustment(adjustment)

        def set_value(self, value):
            # type: (int) -> None
            self.widget.set_value(value)

        def get_value(self):
            # type: () -> int
            return self.widget.get_value_as_int()

    class MyCombo:
        def __init__(self, entries, *, has_entry=False):
            # type: (List[str], bool) -> None
            # Gtk.ComboBoxText.__init__(self)
            self.entries = entries
            if len(entries) > 0 and type(entries[0]) == tuple:
                self.keys = [e[0] for e in entries]
                self.entries = [e[1] for e in entries]
            else:
                self.keys = self.entries
            if has_entry:
                self.widget = Gtk.ComboBoxText.new_with_entry()
            else:
                self.widget = Gtk.ComboBoxText()
                self.widget.set_entry_text_column(0)
            self.fill_combo(self.entries)

        def fill_combo(self, data_list, wrap_width=1):
            # type: (Gtk.ComboBox, List[str], int) -> None
            for data in data_list:
                if data:
                    if type(data) == tuple:
                        self.widget.append(data[0], data[1])
                        self.widget.set_id_column(0)
                        self.widget.set_entry_text_column(1)
                    else:
                        self.widget.append_text(data)
                        self.widget.set_entry_text_column(0)

            self.widget.set_popup_fixed_width(False)
            self.widget.set_wrap_width(wrap_width)

        def set_value(self, value):
            # type: (str) -> None
            if value in self.keys:
                i = self.keys.index(value)
            else:
                i = -1
            self.widget.set_active(i)

        def get_value(self):
            # type: () -> str
            return self.widget.get_active_text()


class Category:
    def __init__(
        self,
        getfunc,  # type: Callable
        commitfunc,  # type: Callable
        get_all_objects_func,  # type: Callable
        objcls,  # type: BaseObject
        objclass,  # type: Optional[str]
        editfunc,  # type: Callable
    ):
        self.getfunc = getfunc
        self.commitfunc = commitfunc
        self.get_all_objects_func = get_all_objects_func
        self.objcls = objcls
        self.objclass = objclass
        self.editfunc = editfunc


CATEGORIES = [
    "People",
    "Families",
    "Events",
    "Places",
    "Citations",
    "Sources",
    "Repositories",
    "Media",
    "Notes",
]


def get_category_info(db, category_name):
    # type: (Any, str) -> Category

    objclass = None
    if category_name == "Person":
        get_all_objects_func = db.get_person_handles
        getfunc = db.get_person_from_handle
        commitfunc = db.commit_person
        editfunc = EditPerson
        objcls = Person
        objclass = "Person"
    if category_name == "Family":
        get_all_objects_func = db.get_family_handles
        getfunc = db.get_family_from_handle
        commitfunc = db.commit_family
        editfunc = EditFamily
        objcls = Family
        objclass = "Family"
    if category_name == "Place":
        get_all_objects_func = db.get_place_handles
        getfunc = db.get_place_from_handle
        commitfunc = db.commit_place
        editfunc = EditPlace
        objcls = Place
        objclass = "Place"
    if category_name == "Event":
        get_all_objects_func = db.get_event_handles
        getfunc = db.get_event_from_handle
        commitfunc = db.commit_event
        editfunc = EditEvent
        objcls = Event
        objclass = "Event"
    if category_name == "Citation":
        get_all_objects_func = db.get_citation_handles
        getfunc = db.get_citation_from_handle
        commitfunc = db.commit_citation
        editfunc = EditCitation
        objcls = Citation
        objclass = "Citation"
    if category_name == "Source":
        get_all_objects_func = db.get_source_handles
        getfunc = db.get_source_from_handle
        commitfunc = db.commit_source
        editfunc = EditSource
        objcls = Source
        objclass = "Source"
    if category_name == "Repository":
        get_all_objects_func = db.get_repository_handles
        getfunc = db.get_repository_from_handle
        commitfunc = db.commit_repository
        editfunc = EditRepository
        objcls = Repository
        objclass = "Repository"
    if category_name == "Note":
        get_all_objects_func = db.get_note_handles
        getfunc = db.get_note_from_handle
        commitfunc = db.commit_note
        editfunc = EditNote
        objcls = Note
        objclass = "Note"
    if category_name == "Media":
        get_all_objects_func = db.get_media_handles
        getfunc = db.get_media_from_handle
        commitfunc = db.commit_media
        editfunc = EditMedia
        objcls = Media
        objclass = "Media"
    return Category(
        getfunc,
        commitfunc,
        get_all_objects_func,
        objcls,
        objclass,
        editfunc,
    )


# -------------------------------------------------------------------------
#
# ShowResults
#
# -------------------------------------------------------------------------
class ShowResults(ManagedWindow):
    """Adapted from gramps/gui/editors/filtereditor.py"""


    
    def __init__(self, dbstate, uistate, track, handle_list, filtname, namespace, user, options_class, name):
        # type: (DbState,DisplayState,list,list,str,str) -> None
        self.filtname = filtname    # set these before invoking ManagedWindow.__init__
        self.namespace = namespace  # so that build_menu_names can see the values
        
        ManagedWindow.__init__(self, uistate, track, self)

        self.dbstate = dbstate
        self.db = dbstate.db
        self.user = user
        self.options_class = options_class
        self.name = name
        
        self.category_info = get_category_info(self.db, namespace)
        glade = Glade(toplevel="test")

        test_title = glade.get_child_object("test_title")
        title = '<a href="#">{namespace}: {filtname}</a>'.format(
            namespace=_(namespace),
            filtname=filtname,
        )
        test_title.set_markup(title)
        test_title2 = glade.get_child_object("test_title2")
        n = len(handle_list)
        title2 = '{n} {objects}'.format(
            objects=_("object") if n == 1 else _("objects"),
            n=n,
        )
        test_title2.set_text(title2)

        test_title.connect("button_press_event", self.invoke_tool) # lambda *x: print("link", x)) 
        
        
        
        


        self.set_window(glade.get_child_object("test"), None, _("Filter Test"))

        render = Gtk.CellRendererText()

        self.treeview = glade.get_child_object("list")
        model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            object,
        )
        self.treeview.set_model(model)

        col = Gtk.TreeViewColumn(_("ID"), render, text=0)
        col.set_clickable(True)
        col.set_resizable(True)
        col.set_sort_column_id(0)
        self.treeview.append_column(col)

        if self.namespace == "Event":
            col = Gtk.TreeViewColumn(_("Type"), render, text=1)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(1)
            self.treeview.append_column(col)

            col = Gtk.TreeViewColumn(_("Description"), render, text=2)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(2)
            self.treeview.append_column(col)
        elif self.namespace == "Citation":
            col = Gtk.TreeViewColumn(_("Page"), render, text=1)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(1)
            self.treeview.append_column(col)

            col = Gtk.TreeViewColumn(_("Source"), render, text=2)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(2)
            self.treeview.append_column(col)
        else:
            col = Gtk.TreeViewColumn(_("Name"), render, text=1)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(1)
            self.treeview.append_column(col)

        if self.namespace == "Person":
            col = Gtk.TreeViewColumn(_("Birth"), render, text=2)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(3)
            self.treeview.append_column(col)

        self.treeview.connect("button-press-event", self.button_press)

        glade.get_child_object("test_close").connect("clicked", self.close)
        glade.get_child_object("open_button").connect("clicked", self.open_object)

        new_list = sorted(
            (self.sort_val_from_handle(h) for h in handle_list),
            key=lambda x: glocale.sort_key(x[0]),
        )

        for s_, handle in new_list:
            gid, name, name2, sortvalue, obj = self.get_obj(handle)
            model.append(row=[gid, name, name2, sortvalue, obj])

        glade.get_child_object("open_button").set_sensitive(len(new_list) > 0)
        self.db_changed_key = self.dbstate.connect("database-changed", self.db_changed)
        self.show()

    def build_menu_names(self, obj):
        # type: (str) -> Tuple[str,str]
        """
        Needed by ManagedWindow to build the Windows menu
        """
        return (
            _("Results"),
            _("Test run result ({}: {})").format(self.namespace, self.filtname),
        )

    def db_changed(self, db):
        self.dbstate.disconnect(self.db_changed_key)
        self.close()

    def find_tool_window(self, tree):
        if isinstance(tree, list):
            for item in tree:
                tool = self.find_tool_window(item)
                if tool: return tool
        elif isinstance(tree, Tool):
            return tree
        else:
            return None

    def invoke_tool(self, _label, _event):
        tool = self.find_tool_window(self.uistate.gwm.window_tree)
        if tool is None:
            tool = Tool(self.dbstate, self.user, self.options_class, self.name)
        tool.current_category = self.namespace
        tool.current_filtername = self.filtname
        i = tool.categories.index(tool.current_category)
        tool.combo_categories.set_active(i)
        tool.populate_filters(tool.current_category)
        tool.dialog.present_with_time(_event.time)
    
    def _select_row_at_coords(self, x, y):
        """
        Select the row at the current cursor position.
        """
        wx, wy = self.treeview.convert_bin_window_to_widget_coords(x, y)
        row = self.treeview.get_dest_row_at_pos(wx, wy)
        if row:
            self.treeview.get_selection().select_path(row[0])

    def button_press(self, _listview, event):
        # type: (Gtk.TreeView, Gtk. Event) -> None
        self._select_row_at_coords(event.x, event.y)
        if not self.db.db_is_open:
            return
        if self.is_right_click(event):  # popup menu code copied from embeddedlists.py
            model, treeiter = self.treeview.get_selection().get_selected()
            if treeiter is None:
                return  # list is empty
            row = list(model[treeiter])
            obj = row[-1]
            self.right_click(obj, event)
            return True
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.open_object(None)

    def is_right_click(self, event):
        """
        Returns True if the event is to open the context menu.
        """
        from gi.repository import Gdk

        if Gdk.Event.triggers_context_menu(event):
            return True

    def right_click(self, obj, event):
        """
        On right click show a popup menu.
        """
        self.__store_menu = Gtk.Menu()  # need to keep reference or menu disappears
        menu = self.__store_menu
        menu.set_reserve_toggle_size(False)

        item = Gtk.MenuItem.new_with_mnemonic("Activate")
        item.connect(
            "activate",
            lambda _menuitem: self.uistate.set_active(obj.handle, self.namespace),
        )
        menu.append(item)
        item.show()

        item = Gtk.MenuItem.new_with_mnemonic("Copy to clipboard")
        item.connect(
            "activate",
            lambda _menuitem: self.copy_to_clipboard(obj.handle, self.namespace),
        )
        menu.append(item)
        item.show()

        menu.popup_at_pointer(event)
        return True

    def open_object(self, _widget):
        # type: (Gtk.Widget) -> None
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter is None:
            return  # list is empty
        row = list(model[treeiter])
        obj = row[-1]
        try:  # may fail if clicked too frequently or window already open
            self.category_info.editfunc(self.dbstate, self.uistate, self.track, obj)
        except WindowActiveError:
            pass
        except:
            traceback.print_exc()

    def copy_to_clipboard(self, handle, namespace):
        # Exploit PageView.copy_to_clipboard.
        # Use 'self' to emulate a PageView object since
        # PageView.copy_to_clipboard only needs an object that contains dbstate and uistate.
        from gramps.gui.views.pageview import PageView

        PageView.copy_to_clipboard(self, namespace, [handle])

    def get_obj(self, handle):
        # type: (str) -> Tuple[str,str,str,Any]
        name2 = ""
        sortvalue = 0
        if self.namespace == "Person":
            person = self.db.get_person_from_handle(handle)
            name = name_displayer.sorted(person)
            gid = person.get_gramps_id()
            obj = person
            event = get_birth_or_fallback(self.db, obj)
            if event and event.date:
                name2 = str(event.date)
                sortvalue = event.date.sortval
            else:
                name2 = ""
                sortvalue = 0

        elif self.namespace == "Family":
            family = self.db.get_family_from_handle(handle)
            name = family_name(family, self.db)
            gid = family.get_gramps_id()
            obj = family
        elif self.namespace == "Event":
            event = self.db.get_event_from_handle(handle)
            name = str(event.get_type())
            name2 = event.get_description()
            gid = event.get_gramps_id()
            obj = event
        elif self.namespace == "Source":
            source = self.db.get_source_from_handle(handle)
            name = source.get_title()
            gid = source.get_gramps_id()
            obj = source
        elif self.namespace == "Citation":
            citation = self.db.get_citation_from_handle(handle)
            src_handle = citation.get_reference_handle()
            source = self.db.get_source_from_handle(src_handle)
            name = citation.get_page()[:30]
            name2 = source.get_title()
            gid = citation.get_gramps_id()
            obj = citation
        elif self.namespace == "Place":
            place = self.db.get_place_from_handle(handle)
            name = place_displayer.display(self.db, place)
            gid = place.get_gramps_id()
            obj = place
        elif self.namespace == "Media":
            obj = self.db.get_media_from_handle(handle)
            name = obj.get_description()
            gid = obj.get_gramps_id()
        elif self.namespace == "Repository":
            repo = self.db.get_repository_from_handle(handle)
            name = repo.get_name()
            gid = repo.get_gramps_id()
            obj = repo
        elif self.namespace == "Note":
            note = self.db.get_note_from_handle(handle)
            name = note.get().replace("\n", " ")
            if len(name) > 80:
                name = name[:80] + "..."
            gid = note.get_gramps_id()
            obj = note
        return (gid, name, name2, sortvalue, obj)

    def sort_val_from_handle(self, handle):
        # type: (str) -> Tuple[str,str]
        if self.namespace == "Person":
            name = self.db.get_person_from_handle(handle).get_primary_name()
            sortname = name_displayer.sort_string(name)
        elif self.namespace == "Family":
            sortname = family_name(self.db.get_family_from_handle(handle), self.db)
        elif self.namespace == "Event":
            sortname = self.db.get_event_from_handle(handle).get_description()
        elif self.namespace == "Source":
            sortname = self.db.get_source_from_handle(handle).get_title()
        elif self.namespace == "Citation":
            sortname = self.db.get_citation_from_handle(handle).get_page()
        elif self.namespace == "Place":
            place = self.db.get_place_from_handle(handle)
            sortname = place_displayer.display(self.db, place)
        elif self.namespace == "Media":
            sortname = self.db.get_media_from_handle(handle).get_description()
        elif self.namespace == "Repository":
            sortname = self.db.get_repository_from_handle(handle).get_name()
        elif self.namespace == "Note":
            gid = self.db.get_note_from_handle(handle).get_gramps_id()
            sortname = gid
        return (sortname, handle)


# ------------------------------------------------------------------------
#
# Options
#
# ------------------------------------------------------------------------
class Options(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        # type: (str,str) -> None
        tool.ToolOptions.__init__(self, name, person_id)

        self.options_dict = {}  # type: Dict[str,Any]
        self.options_help = {}  # type: Dict[str,Any]
