#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021-2023      Kari Kujansuu
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

import csv
import html
import json
import os
import sys
import textwrap
import time
import traceback
import types

from contextlib import contextmanager
from pathlib import Path
from pprint import pprint
from types import SimpleNamespace

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
except:
    TYPE_CHECKING = False

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------

from gi.repository import Gtk, Gdk, GObject, Gio

from gramps.gen.config import config as configman
from gramps.gen.const import GRAMPS_LOCALE as glocale, CUSTOM_FILTERS
from gramps.gen.db.txn import DbTxn
from gramps.gen.dbstate import DbState
from gramps.gen.lib import PrimaryObject

from gramps.gen.filters._genericfilter import GenericFilterFactory
from gramps.gen.filters._filterlist import FilterList
from gramps.gen.filters import reload_custom_filters
from gramps.gen.plug import PluginRegister
from gramps.gen.utils.debug import profile
from gramps.gen.user import User

from gramps.gen.lib import Note

from gramps.gui.displaystate import DisplayState
from gramps.gui.dialog import OkDialog, ErrorDialog
from gramps.gui.editors import EditNote
from gramps.gui.glade import Glade
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gui.views.treemodels.treebasemodel import TreeBaseModel


try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# -------------------------------------------------------------------------
#
# Local modules
#
# -------------------------------------------------------------------------
import supertool_engine as engine
import supertool_utils
from supertool_utils import compile_statements, compile_expression, process_includes

config = configman.register_manager("supertool")
config.register("defaults.encoding", "utf-8")
config.register("defaults.delimiter", "comma")
config.register("defaults.font", "")
config.register("defaults.last_filename", "")
config.register("defaults.include_location", "")
config.register("defaults.last_note", "")

SCRIPTFILE_EXTENSION = ".script"
STEP_INTERVAL = 100   # call step() only every 100 rows

def get_text(textview):
    # type: (Gtk.TextView) -> str 
    buf = textview.get_buffer()
    text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
    return text


def set_text(textview, text):
    # type: (Gtk.TextView, str) -> None 
    textview.get_buffer().set_text(text)


def importfile(fname):  # not used
    # type: (str) -> SimpleNamespace
    dirname = os.path.split(__file__)[0]
    fullname = os.path.join(dirname, fname)
    from types import SimpleNamespace

    code = open(fullname).read()
    globals_dict = {} # type: ignore
    exec(code, globals_dict)
    return SimpleNamespace(**globals_dict)


class NoteDialog(Gtk.Dialog):
    # signals:
    CANCEL = 1
    
    def __init__(self, dbstate, get_notes, selected_gramps_id, current_category):
        # type: (DbState, Callable, Optional[str], str) -> None
        Gtk.Dialog.__init__(self)
        self.dbstate = dbstate
        self.get_notes = get_notes
        self.last_note = None
        self.selected_gramps_id = selected_gramps_id
        self.current_category = current_category

        c = self.get_content_area()
        lbl = Gtk.Label()
        lbl.set_markup("<b>Notes of type 'SuperTool Script'</b>")
        
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(600, 300)
        sw.set_vexpand(True)

        listview = Gtk.TreeView()
        liststore = Gtk.ListStore(str,str,str,str)
        listview.set_model(liststore)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("ID", renderer, text=0, weight=1)
        listview.append_column(column)
        column = Gtk.TreeViewColumn("Category", renderer, text=1, weight=1)
        listview.append_column(column)
        column = Gtk.TreeViewColumn("Title", renderer, text=2, weight=1)
        listview.append_column(column)
        listview.connect("button-press-event", self.button_press)

        self.cb_category = Gtk.CheckButton("Show only category '{}'".format(current_category))
        self.cb_category.set_active(True)
        self.cb_category.connect("toggled", self.list_notes)

        sw.add(listview)
        c.add(lbl)
        c.add(sw)
        c.add(self.cb_category)

        self.listview = listview
        self.liststore = liststore

        self.list_notes(None)
        
        self.show_all()
        
    def button_press(self, treeview, event):
        # type: (Gtk.TreeView, Gdk.Event) -> bool
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            model, treeiter = self.listview.get_selection().get_selected()
            if treeiter is None:
                return False
            row = list(model[treeiter])
            self.emit("response", self.LOAD_NOTE)
            return True
        return False

    def list_notes(self, _widget):
        # type: (Gtk.Widget) -> None
        self.liststore.clear()
        for note, data in self.get_notes():
            title = data["title"]
            category = data["category"]
            if self.cb_category.get_active() and category != self.current_category:
                continue
            treeiter  = self.liststore.append([note.gramps_id, category, title, note.get_handle()])
            if self.selected_gramps_id is None:
                self.selected_gramps_id = note.gramps_id # select first one by default
            if note.gramps_id == self.selected_gramps_id:
                self.listview.get_selection().select_iter(treeiter)
    
        
    def get_note(self):
        # type: () -> Note
        model, iter_ = self.listview.get_selection().get_selected()
        if iter_ is None:
            return None
        row = model[iter_]
        notehandle = row[3]
        note = self.dbstate.db.get_note_from_handle(notehandle)
        return note


class NoteChooserDialog(NoteDialog):
    LOAD_NOTE = 2
    EDIT_NOTE = 3
    def __init__(self, dbstate, get_notes, selected_gramps_id, category_name):
        # type: (DbState, Callable, Optional[str], str) -> None
        NoteDialog.__init__(self, dbstate, get_notes, selected_gramps_id, category_name)
        self.add_button("Load",  NoteChooserDialog.LOAD_NOTE)
        self.add_button("Edit",  NoteChooserDialog.EDIT_NOTE)
        self.add_button("Cancel",  NoteChooserDialog.CANCEL)
        self.set_default_response(NoteChooserDialog.LOAD_NOTE)

class NoteSaveDialog(NoteDialog):
    SAVE_NOTE = 3
    NEW_NOTE = 4
    def __init__(self, dbstate, get_notes, selected_gramps_id, category_name):
        # type: (DbState, Callable, Optional[str], str) -> None
        NoteDialog.__init__(self, dbstate, get_notes, selected_gramps_id, category_name)
        self.add_button("Overwrite",  NoteSaveDialog.SAVE_NOTE)
        self.add_button("New",  NoteSaveDialog.NEW_NOTE)
        self.add_button("Cancel",  NoteSaveDialog.CANCEL)

class ScriptOpenFileChooserDialog(Gtk.FileChooserDialog):
    def __init__(self, uistate):
        # type: (DisplayState) -> None
        Gtk.FileChooserDialog.__init__(
            self,
            title="Load query from a .script file",
            transient_for=uistate.window,
            action=Gtk.FileChooserAction.OPEN,
        )

        self.add_buttons(
            _("_Cancel"), Gtk.ResponseType.CANCEL, _("Load"), Gtk.ResponseType.OK
        )

        filter_scriptfile = Gtk.FileFilter()
        filter_scriptfile.set_name("Script files")
        filter_scriptfile.add_pattern("*" + SCRIPTFILE_EXTENSION)
        self.add_filter(filter_scriptfile)

        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        self.add_filter(filter_json)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*.*")
        self.add_filter(filter_all)


class ScriptSaveFileChooserDialog(Gtk.FileChooserDialog):
    def __init__(self, uistate):
        # type: (DisplayState) -> None
        Gtk.FileChooserDialog.__init__(
            self,
            title="Save query to a .script file",
            transient_for=uistate.window,
            action=Gtk.FileChooserAction.SAVE,
        )

        self.add_buttons(
            _("_Cancel"), Gtk.ResponseType.CANCEL, _("Save"), Gtk.ResponseType.OK
        )

        filter_scriptfile = Gtk.FileFilter()
        filter_scriptfile.set_name("Script files")
        filter_scriptfile.add_pattern("*" + SCRIPTFILE_EXTENSION)
        self.add_filter(filter_scriptfile)


class CsvFileChooserDialog(Gtk.FileChooserDialog):
    def __init__(self, uistate):
        # type: (DisplayState) -> None
        Gtk.FileChooserDialog.__init__(
            self,
            title="Download results as a CSV file",
            transient_for=uistate.window,
            action=Gtk.FileChooserAction.SAVE,
        )

        self.add_buttons(
            _("_Cancel"), Gtk.ResponseType.CANCEL, _("Save"), Gtk.ResponseType.OK
        )

        box = Gtk.VBox()
        box1 = Gtk.HBox()
        box2 = Gtk.HBox()

        config.load()
        encoding = config.get("defaults.encoding")
        delimiter = config.get("defaults.delimiter")

        self.cb_utf8 = Gtk.RadioButton.new_with_label_from_widget(None, "UTF-8")
        self.cb_iso8859_1 = Gtk.RadioButton.new_with_label_from_widget(
            self.cb_utf8, "ISO8859-1"
        )
        if encoding == "iso8859-1":
            self.cb_iso8859_1.set_active(True)

        box1.add(Gtk.Label("Encoding:"))
        box1.add(self.cb_utf8)
        box1.add(self.cb_iso8859_1)
        frame1 = Gtk.Frame()
        frame1.add(box1)

        self.cb_comma = Gtk.RadioButton.new_with_label_from_widget(None, "comma")
        self.cb_semicolon = Gtk.RadioButton.new_with_label_from_widget(
            self.cb_comma, "semicolon"
        )
        if delimiter == ";":
            self.cb_semicolon.set_active(True)

        box2.add(Gtk.Label("Delimiter:"))
        box2.add(self.cb_comma)
        box2.add(self.cb_semicolon)
        frame2 = Gtk.Frame()
        frame2.add(box2)
        box.set_spacing(5)
        box.add(frame1)
        box.add(frame2)
        box.show_all()
        self.set_extra_widget(box)
        self.set_do_overwrite_confirmation(True)

        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        self.add_filter(filter_csv)

class HelpWindow(Gtk.Window):
    def __init__(self, uistate, help_notebook):
        # type: (DisplayState, Gtk.Notenook) -> None
        Gtk.Window.__init__(self, title="Help Window")
        self.set_keep_above(True)
        self.box = Gtk.VBox(spacing=6)
        self.add(self.box)

        readme_url = "https://github.com/Taapeli/isotammi-addons/blob/master/source/SuperTool/README.md"

        label = Gtk.Label()
        markup = '<a href="{url}">{title}</a>'.format(
            url=readme_url, title="Open README in a browser"
        )
        label.set_markup(markup)
        
        self.box.pack_start(label, False, False, 0)
        self.box.pack_start(Gtk.Label("Available properties"), False, False, 0)
        self.box.pack_start(help_notebook, True, True, 0)



class DescriptionDialog(Gtk.Dialog):
    def __init__(self, parent):
        # type: (Gtk.Widget) -> None
        Gtk.Dialog.__init__(self, title="Description", transient_for=parent)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.set_keep_above(True)
        self.box = Gtk.VBox(spacing=6)
        self.get_content_area().add(self.box)

        textview = Gtk.TextView()
        self.textbuffer = textview.get_buffer()
        textview.set_size_request(400, 200)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.box.pack_start(textview, False, False, 0)
        self.show_all()
        
    def get_description(self):
        # type: () -> str
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        return self.textbuffer.get_text(start, end, False)

    def set_description(self, description):
        # type: (str) -> None
        self.textbuffer.set_text(description)


class Query:
    ESCAPE = "\\"  # one backslash

    def __init__(self):
        # type: () -> None
        self.category = ""
        self.title = ""
        self.initial_statements = ""
        self.statements = ""
        self.filter = ""
        self.expressions = ""
        self.scope = "selected"
        self.unwind_lists = False
        self.commit_changes = False
        self.summary_only = False
        self.filename = None    # type: Optional[str]
        self.dirname = None     # type: Optional[str]
        self.description = ""

    def initialize(self):
        # type: () -> None
        self.initial_statements_with_includes, self.initial_statements_files = process_includes(self.initial_statements, self.dirname)
        self.statements_with_includes, self.statements_files = process_includes(self.statements, self.dirname)

        self.initial_statements_compiled = compile_statements(
            self.initial_statements_with_includes, "initial_statements"
        )
        self.statements_compiled = compile_statements(self.statements_with_includes, "statements")
        self.filter_compiled = compile_expression(self.filter, "filter")
        self.expressions_compiled = compile_expression(self.expressions, "expressions")

    def get_filename(self, files, linenum):
        # type: (List[Tuple[str,int,int]], int) -> Tuple[str,int]
        for fname,startline,endline in files:
            if startline <= linenum <= endline:
                return fname, (linenum-startline+1)
        return "", linenum

    @staticmethod
    def text_to_query(text):
        # type: (str) -> Query
        return Query.dict_to_query(Query.text_to_dict(text))

    @staticmethod
    def dict_to_query(data):
        # type: (Dict[str,str]) -> Query
        query = Query()
        query.title = data.get("title", "")
        query.category = data.get("category", "")
        query.dirname = data.get("dirname", "")
        query.initial_statements = data.get("initial_statements", "")
        query.statements = data.get("statements", "")
        query.filter = data.get("filter", "")
        query.expressions = data.get("expressions", "")
        query.scope = data.get("scope", "selected")
        query.description = data.get("description", "")
    
        unwind_lists = data.get("unwind_lists", "")
        commit_changes = data.get("commit_changes", "")
        summary_only = data.get("summary_only", "")
        query.unwind_lists = unwind_lists == "True"
        query.commit_changes = commit_changes == "True"
        query.summary_only = summary_only == "True"
        return query
    
    @staticmethod
    def text_to_dict(text):
        # type: (str) -> Dict[str,str]
        data = {}
        key = None
        value = ""
        for line in text.splitlines(keepends=True):
            if line.startswith("["):
                if key:
                    data[key] = value.rstrip()
                key = line.strip()[1:-1]
                value = ""
            elif line.startswith(Query.ESCAPE):
                value += line[1:]
            else:
                value += line
        if key:
            data[key] = value.rstrip()
        return data

    def to_text(self):
        # type: () -> str
        return Query.dict_to_text(self.to_dict())

    def to_dict(self):
        # type: () -> Dict[str,str]
        data = {}
        data["title"] = self.title
        data["description"] = self.description
        data["category"] = self.category
        data["initial_statements"] = self.initial_statements
        data["statements"] = self.statements
        data["filter"] = self.filter
        data["expressions"] = self.expressions

        data["scope"] = self.scope

        data["unwind_lists"] = str(self.unwind_lists)
        data["commit_changes"] = str(self.commit_changes)
        data["summary_only"] = str(self.summary_only)
        return data
    
    @staticmethod
    def dict_to_text(data):
        # type: (Dict[str,str]) -> str
        lines = []
        lines.append("[Gramps SuperTool script file]")
        lines.append("version=1")
        lines.append("")
        for key, value in data.items():
            lines.append("[" + key + "]")
            for line in value.splitlines():
                if line.startswith("[") or line.startswith(Query.ESCAPE):
                    line = Query.ESCAPE + line
                lines.append(line)
            lines.append("")  # empty line
        return "\n".join(lines)

    def clone(self):
        # type: () -> Query
        data = self.to_dict()
        return Query.dict_to_query(data)
    
    def __eq__(self, other):
        # type: (Any) -> bool
        my_data = self.to_dict()
        other_data = other.to_dict()
        del my_data["category"]
        del other_data["category"]
        return my_data == other_data

class ScriptFile:
    # when saving, lines starting with [ or \ are prefixed with a \
    ESCAPE = "\\"  # one backslash

    def load(self, filename, loadtitle=True):
        # type: (str, bool) -> Query
        if filename.endswith(".json"):
            data = self.__readdata_json(filename)
        else:
            data = self.__readdata(filename)
        query = Query.dict_to_query(data)
        query.filename = filename
        if not query.title and loadtitle:
            name = os.path.split(filename)[1]
            query.title = name.replace(SCRIPTFILE_EXTENSION, "")
        return query

    def save(self, filename, query, save_dirname=False):
        # type: (str, Query, bool) -> None
        data = {}
        data["title"] = query.title
        data["description"] = query.description
        data["category"] = query.category
        data["initial_statements"] = query.initial_statements
        data["statements"] = query.statements
        data["filter"] = query.filter
        data["expressions"] = query.expressions

        data["scope"] = query.scope

        data["unwind_lists"] = str(query.unwind_lists)
        data["commit_changes"] = str(query.commit_changes)
        data["summary_only"] = str(query.summary_only)
        if save_dirname and query.dirname:
            data["dirname"] = query.dirname
        try:
            self.__writedata(filename, data)
        except Exception as e:
            msg = traceback.format_exc()
            ErrorDialog("Saving the file failed", msg)

    def __writedata(self, filename, data):
        # type: (str, Dict[str,str]) -> None
        # open(filename, "w").write(json.dumps(data, indent=4))
        with open(filename, "wt", encoding='utf-8') as f:
            print("[Gramps SuperTool script file]", file=f)
            print("version=1", file=f)
            print("", file=f)
            for key, value in data.items():
                print("[" + key + "]", file=f)
                lines = value.splitlines()
                for line in lines:
                    if line.startswith("[") or line.startswith(self.ESCAPE):
                        line = self.ESCAPE + line
                    print(line, file=f)
                print(file=f)  # empty line

    def __readdata(self, filename):
        # type: (str) -> Dict[str,str]
        try:
            try:
                return Query.text_to_dict(open(filename, 'rt', encoding='utf-8').read())
            except UnicodeError: 
                # script files should be in utf-8 but if that fails then try the default encoding
                return Query.text_to_dict(open(filename, 'rt').read())
        except (FileNotFoundError, UnicodeError):
            return {}
        except:
            msg = traceback.format_exc()
            ErrorDialog("Reading the file failed", msg)
            return {}

    def __readdata_json(self, filename):
        # type: (str) -> Dict[str,str]
        try:
            data = open(filename, 'rt', encoding='utf-8').read()
            return json.loads(data)
        except FileNotFoundError:
            return {}
        except:
            traceback.print_exc()
            return {}

class Row:
    def __init__(self, row, gramps_id, category, handle):
        # type: (List, Optional[str], Optional[str], Optional[str]) -> None
        self.row = []
        for v in row:
            if type(v) in {int, str, float}:
                value = v
            else:
                value = str(v)
            self.row.append(value)

        self.gramps_id = gramps_id
        self.category = category
        self.handle = handle
        
class Result:
    def __init__(self):
        # type: () -> None
        self.rows = []  # type: List[Row]
        self.coltypes = []  # type: List[Any]
        self.headers = []   # type: List[str]
        self.max = 0
        self.read_limit = 0
    def add_row(self, row, gramps_id=None,category=None, handle=None):
        # type: (List, str, str, str) -> None
        self.rows.append(Row(row,gramps_id, category, handle))
    def fetch_rows(self):
        # type: () -> Iterator[List[Optional[str]]]
        for row in self.rows:
            yield [row.gramps_id] + row.row + [row.category,row.handle]
        self.rows = []
    def set_coltypes(self, coltypes):
        # type: (List[Any]) -> None
        self.coltypes = [str] + coltypes # add str for IDs
    def get_coltypes(self):
        # type: (Any) -> List[Any]
        return  self.coltypes 
    def set_headers(self, headers):
        # type: (List[str]) -> None
        self.headers = ["ID"] + headers
    def get_headers(self):
        # type: (Any) -> List[str]
        return self.headers 
    def set_max(self, maxcount=0, read_limit=0):
        # type: (int, int) -> None
        self.max = maxcount             # max number of object to display
        self.read_limit = read_limit    # max number of objects to retrieve

class GrampsEngine:
    def __init__(
        self,
        dbstate,
        user,
        category,
        selected_handles,
        query,
        step=None,
        env=None,
        raw_values=False,
    ):
        # type: (DbState, User, supertool_utils.Category, List[str], Query, Callable, Any, bool) -> None
        self.dbstate = dbstate
        self.db = dbstate.db
        self.user = user
        self.uistate = user.uistate
        self.category = category
        self.selected_handles = selected_handles
        self.total_objects = len(self.selected_handles)
        self.query = query
        self.step = step
        if env is None: 
            env = {}
        self.env = env
        self.raw_values = raw_values
        self.query.initialize()

    def generate_rows(self, res):
        # type: (Tuple[Any,...]) -> Iterator[List[Any]]
        def cast(value):
            # type: (Any) -> Any
            if self.raw_values: return value
            if type(value) in {int, str, float}:
                return value
            else:
                return str(value)

        if not res:
            yield []
            return
        value = res[0]
        for values in self.generate_rows(res[1:]):
            if type(value) is types.GeneratorType:
                value = list(value)
            if self.query.unwind_lists and type(value) is list:
                for v in value:
                    yield [cast(v)] + values
            else:
                yield [cast(value)] + values

    def evaluate_condition(self, obj, cond, env):
        # type: (Any,str,Dict[str,Any]) -> Tuple[bool, Dict[str,Any]]
        return self.category.execute_func(self.dbstate, obj, cond, env)

    def generate_values(self, env, result):
        # type: (Dict[str,Any],Result) -> Iterator[Tuple[Any,Dict[str,Any],List[Any]]]
        for n,handle in enumerate(self.selected_handles):
            if result.read_limit and n >= result.read_limit:
                return

            if self.step and n % STEP_INTERVAL == 0:
                if self.step():  # user clicked 'Cancel', stop
                    return

            obj = self.category.getfunc(handle)
            obj.commit_ok = True
            try:
                if self.query.statements_compiled:
                    value, env = self.category.execute_func(
                        self.dbstate,
                        obj,
                        self.query.statements_compiled,
                        env,
                        "exec",
                    )
                if self.query.filter_compiled:
                    ok, env = self.evaluate_condition(obj, self.query.filter_compiled, env)
                    if not ok:
                        continue
    
                if self.query.commit_changes and obj.commit_ok:
                    self.category.commitfunc(obj, self.trans)
    
                for values in result.fetch_rows():
                    yield None, env, values
                    
                if result.max and self.object_count >= result.max:
                    return
                self.object_count += 1

                if self.query.summary_only:
                    continue
                
                if self.query.expressions_compiled:
                    res, env = self.category.execute_func(
                        self.dbstate,
                        obj,
                        self.query.expressions_compiled,
                        env,
                    )
                    if type(res) != tuple:
                        res = (res,)
                    for values in self.generate_rows(res):
                        yield obj, env, [obj.gramps_id] + values + [self.category.category_name, handle]
            except Exception as e:
                e.gramps_id = obj.gramps_id # type: ignore
                raise e
            
    def get_values(self, trans, result):
        # type: (DbTxn, Result) -> Generator
        self.trans = trans

        #         if not self.category.execute_func:
        #             return
        self.object_count = 0
        env = supertool_utils.get_globals()  # type: Dict[str,Any]
        env["trans"] = trans
        env["user"] = self.user
        env["uistate"] = self.uistate
        env["dbstate"] = self.dbstate
        env["db"] = self.db
        env["result"] = result
        env["category"] = self.category.category_name
        env["namespace"] = self.category.objclass
        env["supertool_run"] = (lambda category=self.category.category_name, **kwargs: 
                                    supertool_utils.supertool_execute(category=category, 
                                              dbstate=self.dbstate, 
                                              trans=trans, 
                                              **kwargs))
        env["step"] = self.step
    

        env.update(self.env)

        env["active_person"] = None
        if self.uistate:
            handle = self.uistate.get_active('Person')
            if handle:
                env["active_person"] = engine.PersonProxy(self.db, handle)

        if self.query.initial_statements_compiled:
            value, env = self.category.execute_func(
                self.dbstate, None, self.query.initial_statements_compiled, env, "exec"
            )
            yield from result.fetch_rows()

        for obj, env, values in self.generate_values(env, result):
            if not self.query.summary_only:
                #yield from result.fetch_rows()
                yield values
        #yield from result.fetch_rows()

        if self.query.summary_only:
            if self.query.expressions_compiled:
                res, env = self.category.execute_func(
                    self.dbstate, None, self.query.expressions_compiled, env
                )
                if type(res) != tuple:
                    res = (res,)
                for values in self.generate_rows(res):
                    yield [None] + values + [None, None]


class SuperTool(ManagedWindow):
    def __init__(self, user, dbstate, plugindata):
        # type: (User, DbState, Any) -> None
        ManagedWindow.__init__(self, user.uistate, [], self.__class__, modal=False)
        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        self.plugindata = plugindata
        self.csv_filename = ""
        self.last_filename = None
        self.getfunc = None
        self.execute_func = None
        self.editfunc = None
        self.query = Query()
        self.last_note = None
        self.ignore_changes = True
        self.saved_query = None # type: Optional[Query]
        self.listview = None  # type: Optional[Gtk.TreeView]   
        self.init()

    def build_menu_names(self, obj): 
        # type: (Any) -> Tuple[str,str]
        """
        Needed by ManagedWindow to build the Windows menu
        """
        return ('SuperTool','SuperTool')

    def build_help(self):  # temporary helper; not used
        # type: () -> None
        self.help_notebook = Gtk.Notebook()
        page = 0
        data = {} # type: Dict[str,Any]
        for cat_name in supertool_utils.get_categories():
            print(cat_name)
            data[cat_name] = []
            info = supertool_utils.get_category_info(self.db, cat_name)
            if not info.objclass:
                continue
            box = Gtk.VBox()
            box.set_border_width(10)
            grid = Gtk.Grid()
            row = 0
            col = 0
            for name in sorted(self.get_attributes(info.objcls, info.proxyclass)):
                print("-", name)
                label = Gtk.Label(label=name)
                label.set_halign(Gtk.Align.START)
                # box.add(label)
                grid.attach(label, col, row, 1, 1)

                label = Gtk.Label(label="description")
                label.set_halign(Gtk.Align.START)
                # box.add(label)
                grid.attach(label, col + 1, row, 1, 1)
                data[cat_name].append((name, ""))
                row += 1
            self.help_notebook.append_page(grid, Gtk.Label(label=info.objclass))
            grid.show()
            if cat_name == self.category_name:
                self.help_notebook.set_current_page(page)
            page += 1
        self.help_loaded = True
        print(json.dumps(data, indent=4))

    def build_listview(self, values, result):
        # type: (Tuple[Union[int,str,float],...], Result) -> None
        self.listview = Gtk.TreeView()
        numcols = len(values)
        renderer = Gtk.CellRendererText()

        coltypes = result.get_coltypes()  # type: List[Union[Type[int],Type[str],Type[float]]]
        if not coltypes:
            coltypes = [str] # for ID
            for colnum in range(1, numcols - 2): # exclude ID, category name and handle 
                coltype = type(values[colnum])
                if coltype in {int, str, float}:
                    coltypes.append(coltype)
                else:
                    coltypes.append(str)
        coltypes.append(str)  # for category name
        coltypes.append(str)  # for handle

        headers = result.get_headers() # type List[str]
        for colnum in range(numcols - 2):
            if headers:
                title = headers[colnum]
            else:
                if colnum == 0:
                    title = "ID"
                else:
                    title = "Value %s" % colnum
            col = Gtk.TreeViewColumn(title, renderer, text=colnum)
            col.set_clickable(True)
            col.set_resizable(True)
            col.set_sort_column_id(colnum)
            self.listview.append_column(col)

        self.output_window.set_size_request(600, 400)
        self.output_window.add(self.listview)

        self.store = Gtk.ListStore(*coltypes)
        self.listview.set_model(self.store)
        self.listview.connect("button-press-event", self.button_press)
        self.listview.show()

    def button_press(self, treeview, event):
        # type: (Gtk.TreeView, Gtk.Event) -> bool
        if not self.db.db_is_open:
            return True
        try:  # may fail if clicked too frequently
            if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
                model, treeiter = self.listview.get_selection().get_selected() # type: ignore
                row = list(model[treeiter])
                category_name = row[-2]
                handle = row[-1]
                if category_name:
                    category = supertool_utils.get_category_info(self.db, category_name)
                else:
                    category = self.category                
                obj = category.getfunc(handle)
                category.editfunc(self.dbstate, self.uistate, [], obj)
                return True
        except:
            traceback.print_exc()
        return False

    def cancel_settings(self, _widget):
        # type: (Gtk.Widget) -> None
        self.settings.toplevel.hide() # type: ignore

    def check_category(self):
        # type: () -> None
        category_ok = self.category.objclass is not None
        if category_ok:
            self.label_filter.show()
            self.label_statements.show()
            self.statements.show()
            self.filter.show()
            self.save_as_filter_menu_item.set_sensitive(True)             
            self.save_as_filter_menu_item.set_tooltip_text("Save the filter as a custom filter")        
        else:
            self.label_filter.hide()
            self.label_statements.hide()
            self.statements.hide()
            self.filter.hide()
            self.save_as_filter_menu_item.set_sensitive(False)        
            self.save_as_filter_menu_item.set_tooltip_text("Save as filter not available in this category")        
                 
            self.summary_checkbox.set_active(True)

        self.all_objects.set_sensitive(category_ok)
        self.filtered_objects.set_sensitive(category_ok)
        self.selected_objects.set_sensitive(category_ok)

        self.summary_checkbox.set_sensitive(category_ok)

    def clear(self, _widget):
        # type: (Any) -> None
        self.title.set_text("")
        set_text(self.initial_statements, "")
        set_text(self.statements, "")
        set_text(self.filter, "")
        set_text(self.expressions, "")
        self.selected_objects.set_active(True)
        self.unwind_lists.set_active(False)
        self.commit_checkbox.set_active(False)
        self.summary_checkbox.set_active(False)
        self.query = Query()
        if self.desc_win:
            self.desc_win.destroy()
            self.desc_win = None # type: Gtk.Window
        self.window.set_title("SuperTool")

    def close(self, *args):
        # type: (Any) -> None
        self.exit(None) 
        super().close(*args)
        
    def content_changed(self, _widget):
        # type: (Gtk.Widget) -> None
        if self.ignore_changes: return
        #print("content_changed")
        query = self.save_to_query()        
        modified = (query != self.saved_query)
        self.set_window_title(modified=modified)
    
    def copy(self, _widget):
        # type: (Gtk.Widget) -> None
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        import io

        stringio = io.StringIO()
        writer = csv.writer(stringio)
        for row in self.store:
            writer.writerow(row[0:-1])  # don't write the handle
        clipboard.set_text(stringio.getvalue(), -1)
        OkDialog("Info", "Result list copied to clipboard")

   
    def create_gui(self):
        # type: () -> Gtk.Widget
        glade = Glade(
            toplevel="main", also_load=["help_window", "adjustment1", "save-as"]
        )
        glade.set_translation_domain(None)

        self.title = glade.get_child_object("title")
        self.version = glade.get_child_object("version")
        self.version.set_text("v" + self.plugindata.version)

        self.label_filter = glade.get_child_object("label_filter")
        self.label_statements = glade.get_child_object("label_statements")

        self.initial_statements = glade.get_child_object("initial_statements")
        self.statements = glade.get_child_object("statements")
        self.filter = glade.get_child_object("filter")
        self.expressions = glade.get_child_object("expressions")

        self.all_objects = glade.get_child_object("all_objects")
        self.filtered_objects = glade.get_child_object("filtered_objects")
        self.selected_objects = glade.get_child_object("selected_objects")

        self.unwind_lists = glade.get_child_object("unwind_lists")
        self.commit_checkbox = glade.get_child_object("commit_checkbox")
        self.summary_checkbox = glade.get_child_object("summary_checkbox")

        self.btn_execute = glade.get_child_object("btn_execute")
        self.btn_csv = glade.get_child_object("btn_csv")
        self.btn_copy = glade.get_child_object("btn_copy")

        self.attributes_list = glade.get_child_object("attributes_list")

        self.statusmsg = glade.get_child_object("statusmsg")
        self.errormsg = self.statusmsg

        self.output_window = glade.get_child_object("output_window")
        self.help_window = glade.get_object("help_window")
        self.help_notebook = glade.get_object("help_notebook")
        self.help_win = None # type: Gtk.Window
        self.desc_win = None

        self.save_as_filter_menu_item = glade.get_object("save_as_filter") # type: Gtk.CheckButton

        self.selected_objects.set_active(True)
        self.btn_execute.connect("clicked", self.execute)
        self.btn_csv.connect("clicked", self.download)
        self.btn_copy.connect("clicked", self.copy)

        glade.connect_signals(
            {
                "new": self.clear,
                "load": self.load,
                "load_from_note": self.load_from_note,
                "save_in_note": self.save_in_note,
                "save": self.save,
                "save_as_filter": self.save_as_filter,
                "settings": self.settings_dialog,
                "help": self.help,
                "close": self.exit,
                "about": self.show_about_dialog,
                "show-description": self.show_description,
            }
        )

        self.settings = Glade(toplevel="settings")
        self.btn_font = glade.get_child_object("btn_font", self.settings.toplevel)
        self.btn_font.connect("font-set", self.set_font)
        self.settings.connect_signals(
            {
                "ok": self.save_settings,
                "cancel": self.cancel_settings,
                # "close"  : self.close_settings,
            }
        )

        self.about_dialog = Glade(toplevel="about").toplevel
        self.about_dialog.set_version(self.plugindata.version)

        TOOL_DIR = "supertool"
        from gramps.gen.const import USER_HOME

        userdir = os.path.join(USER_HOME, TOOL_DIR)
        include_location_dialog = glade.get_child_object(
            "include_location", self.settings.toplevel
        )
        include_location_dialog.add_shortcut_folder(userdir)

        self.btn_csv.hide()
        self.listview = None
        
        ver = (Gtk.get_major_version(), Gtk.get_minor_version())
        if ver >= (3, 22):
            self.initial_statements_window = glade.get_child_object(
                "initial_statements_window"
            )
            self.statements_window = glade.get_child_object("statements_window")
            # self.initial_statements_window.set_max_content_height(200)
            self.initial_statements_window.set_propagate_natural_height(True)
            self.statements_window.set_propagate_natural_height(True)
            # self.statements_window.set_max_content_height(200)

        self.title.connect("changed",self.content_changed)
        self.initial_statements.get_buffer().connect("changed", self.content_changed)
        self.statements.get_buffer().connect("changed", self.content_changed)
        self.filter.get_buffer().connect("changed", self.content_changed)
        self.expressions.get_buffer().connect("changed", self.content_changed)
        self.all_objects.connect("toggled", self.content_changed)
        self.filtered_objects.connect("toggled", self.content_changed)
        self.selected_objects.connect("toggled", self.content_changed)
        self.unwind_lists.connect("toggled", self.content_changed)
        self.commit_checkbox.connect("toggled", self.content_changed)
        self.summary_checkbox.connect("toggled", self.content_changed)
        
        return glade.toplevel

    def db_changed(self, db):
        # type: (Any) -> None
        self.db = self.dbstate.db
        if db.db_is_open:
            self.btn_execute.set_sensitive(True)
        self.statusmsg.set_text("")
        self.select_category()

    def db_closed(self):
        # type: () -> None
        if self.listview:
            self.output_window.remove(self.listview)
        self.listview = None
        self.btn_execute.set_sensitive(False)

    def download(self, _widget):
        # type: (Gtk.Widget) -> None
        choose_file_dialog = CsvFileChooserDialog(self.uistate)
        title = self.title.get_text().strip()
        if title:
            fname = title + ".csv"
        else:
            fname = self.category_name + ".csv"

        choose_file_dialog.set_current_name(fname)
        if self.csv_filename:
            if self.title.get_text():
                dirname = os.path.split(self.csv_filename)[0]
                self.csv_filename = os.path.join(dirname, fname)
            choose_file_dialog.set_filename(self.csv_filename)

        while True:
            response = choose_file_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                break
            elif response == Gtk.ResponseType.DELETE_EVENT:
                break
            elif response == Gtk.ResponseType.OK:
                self.csv_filename = choose_file_dialog.get_filename()
                delimiter = ","
                if choose_file_dialog.cb_comma.get_active():
                    delimiter = ","
                if choose_file_dialog.cb_semicolon.get_active():
                    delimiter = ";"
                encoding = "utf-8"
                if choose_file_dialog.cb_utf8.get_active():
                    encoding = "utf-8"
                if choose_file_dialog.cb_iso8859_1.get_active():
                    encoding = "iso8859-1"

                config.set("defaults.encoding", encoding)
                config.set("defaults.delimiter", delimiter)
                config.save()

                #assert self.csv_filename is not None  # for mypy
                try:
                    writer = csv.writer(
                        open(self.csv_filename, "w", encoding=encoding, newline=""),
                        delimiter=delimiter,
                    )
                    for row in self.store:
                        writer.writerow(row[0:-1])  # don't write the handle
                except Exception as e:
                    msg = traceback.format_exc()
                    ErrorDialog("Saving the file failed", msg)

                break

        choose_file_dialog.destroy()

    def execute(self, _widget):
        # type: (Gtk.Widget) -> None

        self.statusmsg.set_text("")
        self.output_window.hide()
        self.btn_csv.hide()
        self.btn_copy.hide()
        self.trans = None
        if not self.uistate.viewmanager.active_page:
            return
        query = self.saveconfig()
        try:
            self.commit_changes = self.commit_checkbox.get_active()
            txtitle = "Executing SuperTool"
            if self.title.get_text():
                txtitle += " ({})".format(self.title.get_text())

            with DbTxn(txtitle, self.dbstate.db) as self.trans:
                self.execute1(query)
                # profile(self.__execute1, query)
        except Exception as e:
            traceback.print_exc()
            if isinstance(e, engine.SupertoolException):
                self.set_error(str(e))
                return
            lines = traceback.format_exc().splitlines()
            source = None
            src = ""
            fname = ""
            linenum2 = 0
            if len(lines) >= 3 and lines[-2].strip() == "^":
                msglines = lines[-3:]
            elif len(lines) >= 2:
                import re
                m = re.match(r'\s+File "(.+)", line (\d+)', lines[-2])
                if m:
                    src = m.group(1)
                    linenum = int(m.group(2))
                    linenum2 = linenum
                    if src == "initial_statements":
                        source = query.initial_statements_with_includes
                        fname, linenum2 = query.get_filename(query.initial_statements_files, linenum)
                    elif src == "statements":
                        source = query.statements_with_includes
                        fname, linenum2 = query.get_filename(query.statements_files, linenum)
                    elif src == "filter":
                        source = query.filter
                    elif src == "expressions":
                        source = query.expressions
                msglines = [lines[-1]]
            elif len(lines) >= 1:
                msglines = [lines[-1]]
            errortext = "\n".join(msglines)
            context = ""
            codeline = ""
            if hasattr(e, "gramps_id"):
                context = "While processing " + e.gramps_id
            if source:
                codeline = source.splitlines()[linenum-1]
            self.set_error(errortext, context, codeline, src, fname, linenum=linenum2)

    def execute1(self, query):
        # type: (Query) -> None

        def store_handle(model, path, iter, *data):
            # type: (TreeBaseModel, Any, Any, Any) -> None 
            "Auxiliary function for treemodels...."
            handle = model.get_handle_from_iter(iter)
            if handle: selected_handles.append(handle)
        
        self.errormsg.set_text("")
        t1 = time.time()

        #         if not self.category.execute_func:
        #             return
        if self.listview:
            self.output_window.remove(self.listview)
        self.listview = None
        n = 0
        
        if TYPE_CHECKING:
            selected_handles: List[str]
        if self.category.objclass:
            if self.selected_objects.get_active():
                selected_handles = (
                    self.uistate.viewmanager.active_page.selected_handles()
                )
            elif self.all_objects.get_active():
                selected_handles = self.category.get_all_objects_func()
            elif self.filtered_objects.get_active():
                selected_handles = []  # ???
                store = self.uistate.viewmanager.active_page.model
                for row in store:
                    handle = store.get_handle_from_iter(row.iter)
                    if handle: selected_handles.append(handle)
                if isinstance(store, TreeBaseModel):
                    store.foreach(store_handle)                               
        else:
            selected_handles = []

        result = Result()

        count = len(selected_handles) // STEP_INTERVAL
        with self.progress(
            "SuperTool", "Executing " + self.title.get_text(), count
        ) as step:
            gramps_engine = GrampsEngine(
                self.dbstate,
                self.user,
                self.category,
                selected_handles,
                query,
                step,
            )
            for values in gramps_engine.get_values(self.trans, result):
                if not self.listview:
                    # can build this only after the column types are known
                    # (we assume the types are the same for all rows)
                    self.build_listview(values, result)

                self.store.append(values)
                n += 1
        t2 = time.time()

        msg = "Objects: {}/{}; rows: {} ({:.2f}s)".format(
            gramps_engine.object_count, gramps_engine.total_objects, n, t2 - t1
        )
        # print(msg)
        self.statusmsg.set_text(msg)
        if n > 0:
            self.btn_csv.show()
            self.btn_copy.show()
        else:
            self.btn_csv.hide()
            self.btn_copy.hide()
        self.output_window.show()

        
    def exit(self, _widget):
        # type: (Gtk.WIdget) -> None
        self.saveconfig()

        self.dbstate.disconnect(self.database_changed_key)
        self.dbstate.disconnect(self.no_database_key)
        self.uistate.viewmanager.notebook.disconnect(self.switch_page_key)

        if self.help_win:
            self.help_win.close()
        if self.desc_win:
            self.desc_win.destroy()
        if _widget:
            self.close()
                

    def get_attributes(self, objclass, proxyclass):
        # type: (PrimaryObject, Type[engine.Proxy]) -> Iterator[str]
        obj = objclass()
        for name in dir(obj):
            if name.startswith("_"):
                continue
            attr = getattr(obj, name)
            #             if type(attr) == types.FunctionType: continue
            if type(attr) == types.MethodType:
                continue
        from unittest import mock

        db = mock.Mock()
        obj = mock.Mock()
        p = proxyclass(db, obj.handle, obj)

        for name in dir(proxyclass) + list(
            p.__dict__.keys()
        ):  # this contains the @property methods
            if name.startswith("_"):
                continue
            yield name

    def get_configfile(self):
        # type: () -> str
        return __file__[:-3] + "-" + self.category_name + SCRIPTFILE_EXTENSION

    def help(self, _widget):
        # type: (Gtk.WIdget) -> None
        self.load_help()
        self.help_win = HelpWindow(self.uistate, self.help_notebook)
        font_description = self.btn_font.get_font_desc()
        self.help_win.modify_font(font_description)
        self.help_win.show_all()

    def init(self):
        # type: () -> None
        window = self.create_gui()
        self.set_window(window, None, _("SuperTool"))
        self.select_category()
        self.loadconfig()
        self.no_database_key = self.dbstate.connect("no-database", self.db_closed)
        self.database_changed_key = self.dbstate.connect("database-changed", self.db_changed)
        self.switch_page_key = self.uistate.viewmanager.notebook.connect("switch-page", self.pageswitch)
        self.help_loaded = False

        config.load()
        font = config.get("defaults.font")
        if font:
            self.btn_font.set_font(font)
            font_description = self.btn_font.get_font_desc()
            self.window.modify_font(font_description)

        css = b"* {background: #00aa00; color: white}"
        p = Gtk.CssProvider()
        try:
            p.load_from_data(css)
            self.btn_execute.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except:
            pass
        
        self.last_filename = config.get("defaults.last_filename")
        self.show()
        self.check_category()

    def load(self, _widget):
        # type: (Gtk.Widget) -> None
        choose_file_dialog = ScriptOpenFileChooserDialog(self.uistate)
        if self.last_filename:
            choose_file_dialog.set_filename(self.last_filename)

        while True:
            response = choose_file_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                break
            elif response == Gtk.ResponseType.DELETE_EVENT:
                break
            elif response == Gtk.ResponseType.OK:
                filename = choose_file_dialog.get_filename()
                self.loadstate(filename)
                basename = os.path.basename(filename)
                self.window.set_title(basename + " - SuperTool")
                
                self.last_filename = filename
                config.set("defaults.last_filename", filename)
                config.save()
                break

        choose_file_dialog.destroy()

    def load_from_note(self, _widget):
        # type: (Gtk.Widget) -> None
        choose_note_dialog: NoteChooserDialog
        def handle_response(_dialog, response):
            # type: (Gtk.Dialog, int) -> None
            if response == NoteChooserDialog.LOAD_NOTE:
                note = choose_note_dialog.get_note()
                if note is None:
                    return
                self.loadstate_from_note(note.get())
                self.last_note = note.gramps_id
                config.set("defaults.last_note", note.gramps_id)
                config.save()
            if response == NoteChooserDialog.EDIT_NOTE:
                note = choose_note_dialog.get_note()
                if note is None:
                    return
                def callback(*args):
                    # type: (Any) -> None
                    choose_note_dialog.list_notes(_widget) # refresh list
                choose_note_dialog.selected_gramps_id = note.gramps_id                    
                EditNote(self.dbstate, self.uistate, [], note, callback)
                return  # keep the dialog open

            choose_note_dialog.destroy()
            
        choose_note_dialog = NoteChooserDialog(self.dbstate, self.get_notes, self.last_note, self.category_name)
        choose_note_dialog.connect("response", handle_response)

    def get_notes(self):
        # type: () -> Iterator[Tuple[Note,Dict]]
        for note in self.db.iter_notes():
            if note.get_type() == "SuperTool Script":
                data  = Query.text_to_dict(note.get())
                yield (note, data)
            

    def load_help(self):
        # type: () -> None
        dirname = os.path.split(__file__)[0]
        fname = os.path.join(dirname, "helptext.json")
        data = json.loads(open(fname).read())
        self.help_notebook = Gtk.Notebook()
        page = 0
        #for cat_name in ["global"] + supertool_utils.get_categories():
        for tabnum, cat_name in enumerate(data):
            grid = Gtk.Grid()
            grid.set_column_spacing(10)
            row = 0
            col = 0
            for x in data[cat_name]:
                name = x[0]
                desc = x[1]
                label = Gtk.Label(label=name)
                label.set_halign(Gtk.Align.START)
                if len(x) > 2:
                    url = x[2]
                    if url:
                        if len(x) > 3:
                            title = x[3]
                            markup = '<a href="{url}" title="{title}">{name}</a>'.format(
                                url=html.escape(url), name=html.escape(name), title=html.escape(title), 
                            )
                        else:
                            markup = '<a href="{url}">{name}</a>'.format(
                                url=html.escape(url), name=html.escape(name), 
                            )
                        label.set_markup(markup)
                    elif len(x) > 3:
                        label.set_tooltip_text(x[3])
                grid.attach(label, col, row, 1, 1)

                label = Gtk.Label(label=desc)
                label.set_halign(Gtk.Align.START)
                #label.set_line_wrap(True)
                #label.set_size_request(500, -1)
                #label.set_max_width_chars(100)
                
                #label.set_size_request(250, -1) # 250 or whatever width you want. -1 to keep height automatic

                #table = Gtk.Table(1, 1, False)
                #table.attach(label, 0, 1, 0, 1, Gtk.AttachOptions.SHRINK | Gtk.AttachOptions.FILL)
                
                grid.attach(label, col + 1, row, 1, 1)
                
                    
                row += 1
            self.help_notebook.append_page(grid, Gtk.Label(label=cat_name))
            grid.show()
            if cat_name == self.category_name:
                self.help_notebook.set_current_page(page)
            page += 1

    def loadconfig(self):
        # type: () -> None
        self.loadstate(self.get_configfile(), loadtitle=False, set_dirname=False)

    def loadstate(self, filename, loadtitle=True, set_dirname=True):
        # type: (str, bool, bool) -> None
        scriptfile = ScriptFile()
        self.query = scriptfile.load(filename)
        query = self.query
        if set_dirname:
            query.dirname = os.path.split(filename)[0]
        if not query.title and loadtitle:
            name = os.path.split(filename)[1]
            query.title = name.replace(SCRIPTFILE_EXTENSION, "")
        self.loadstate_from_query(query)


    def loadstate_from_note(self, notetext):
        # type: (str) -> None
        self.query = Query.text_to_query(notetext)
        self.loadstate_from_query(self.query)


    
    def loadstate_from_query(self, query):
        # type: (Query) -> None
        if self.desc_win:
            print("closing")
            self.desc_win.destroy()
            self.desc_win = None
        
        if query.category and query.category != self.category_name:
            msg = "Warning: saved query is for category '{}'. Current category is '{}'."
            msg = msg.format(query.category, self.category_name)
            OkDialog(
                _("Warning"),
                msg,
                parent=self.uistate.window,
            )

        self.ignore_changes = True
        self.title.set_text(query.title)

        set_text(self.expressions, query.expressions)
        set_text(self.filter, query.filter)
        set_text(self.statements, query.statements)
        set_text(self.initial_statements, query.initial_statements)
        scope = query.scope
        self.all_objects.set_active(scope == "all")
        self.filtered_objects.set_active(scope == "filtered_")
        self.selected_objects.set_active(scope == "selected")

        self.unwind_lists.set_active(query.unwind_lists)
        self.commit_checkbox.set_active(query.commit_changes)
        self.summary_checkbox.set_active(query.summary_only)
        self.set_window_title(modified=False)
        self.saved_query = query.clone()
        self.ignore_changes = False

    def makefilter(
        self, category, filtername, filtertext, initial_statements, statements
    ):
        # type: (supertool_utils.Category, str, str, str, str) -> None
        the_filter = GenericFilterFactory(category.objclass)()
        rule = category.filterrule([filtertext, initial_statements, statements])
        if not filtername:
            OkDialog(
                _("Error"), "Please supply a title/name", parent=self.uistate.window
            )
            return
        if not filtertext:
            OkDialog(
                _("Error"),
                "Please supply a filtering condition",
                parent=self.uistate.window,
            )
            return
        the_filter.add_rule(rule)
        the_filter.set_name(filtername)
        filterdb = FilterList(CUSTOM_FILTERS)
        filterdb.load()
        filters = filterdb.get_filters_dict(category.objclass)
        if filtername in filters:
            msg = "Filter '{}' already exists; choose another name".format(filtername)
            OkDialog(_("Error"), msg, parent=self.uistate.window)
            return
        filterdb.add(category.objclass, the_filter)
        # print("added filter", the_filter)
        filterdb.save()
        reload_custom_filters()
        self.uistate.emit("filters-changed", (category.objclass,))

        msg = "Created filter {0}".format(filtername)
        OkDialog(_("Done"), msg, parent=self.uistate.window)


    def pageswitch(self, *args):
        # type: (Any) -> None
        self.saveconfig()
        self.select_category()
        self.loadconfig()
        if self.listview:
            self.output_window.remove(self.listview)
            self.btn_csv.hide()
            self.btn_copy.hide()
        self.statusmsg.set_text("")
        self.check_category()
        if self.desc_win:
            self.desc_win.destroy()
            self.desc_win = None

    @contextmanager
    def progress(self, title1, title2, count):
        # type: (str, str, int) -> Iterator[Callable]
        self._progress = ProgressMeter(title1, can_cancel=True)
        self._progress.set_pass(title2, count, ProgressMeter.MODE_FRACTION)
        try:
            yield self._progress.step
        finally:
            self._progress.close()

    def save(self, _widget):
        # type: (Gtk.Widget) -> None
        choose_file_dialog = ScriptSaveFileChooserDialog(self.uistate)
        title = self.title.get_text().strip()
        if title:
            fname = title + SCRIPTFILE_EXTENSION
        else:
            fname = self.category_name + "-query" + SCRIPTFILE_EXTENSION
        choose_file_dialog.set_current_name(fname)
        choose_file_dialog.set_do_overwrite_confirmation(True)
        if self.last_filename:
            if self.title.get_text():
                dirname = os.path.split(self.last_filename)[0]
                self.last_filename = os.path.join(dirname, fname)
            choose_file_dialog.set_filename(self.last_filename)

        while True:
            response = choose_file_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                break
            elif response == Gtk.ResponseType.DELETE_EVENT:
                break
            elif response == Gtk.ResponseType.OK:
                filename = choose_file_dialog.get_filename()
                self.savestate(filename)
                self.last_filename = filename
                config.set("defaults.last_filename", filename)
                config.save()
                self.set_window_title(modified=False)
                break

        choose_file_dialog.destroy()

    def save_in_note(self, _widget):
        # type: (Gtk.Widget) -> None
        choose_note_dialog: NoteSaveDialog
        def handle_response(dialog, response):
            # type: (Gtk.Dialog, int) -> None
            if response == NoteSaveDialog.CANCEL:
                choose_note_dialog.destroy()
                return
            with DbTxn("Saving as Note", self.dbstate.db) as trans:
                if response == NoteSaveDialog.SAVE_NOTE:
                    note = dialog.get_note()
                    if note is None:
                        return
                    self.savestate_to_note(note)
                    self.dbstate.db.commit_note(note, trans)
                if response == NoteSaveDialog.NEW_NOTE:
                    note = Note()
                    note.set_type("SuperTool Script")
                    self.savestate_to_note(note)
                    self.dbstate.db.add_note(note, trans)
                    OkDialog("Done", "Saved as note {}".format(note.gramps_id))
            choose_note_dialog.destroy()
            
        choose_note_dialog = NoteSaveDialog(self.dbstate, self.get_notes, self.last_note, self.category_name)
        choose_note_dialog.connect("response", handle_response)
        

    def save_as_filter(self, obj):
        # type: (Gtk.Widget) -> None
        filtername = self.title.get_text().strip()
        filtertext = get_text(self.filter).strip()
        initial_statements = get_text(self.initial_statements).strip()
        initial_statements = initial_statements.replace("\n", "<br>")

        statements = get_text(self.statements).strip()
        statements = statements.replace("\n", "<br>")
        self.makefilter(
            self.category, filtername, filtertext, initial_statements, statements
        )

    def save_settings(self, _widget):
        # type: (Gtk.Widget) -> None
        loc_entry = self.settings.get_child_object("include_location")
        loc = loc_entry.get_filename()
        config.set("defaults.include_location", loc)
        config.save()
        self.settings.toplevel.hide()

    def saveconfig(self):
        # type: () -> Query
        return self.savestate(self.get_configfile(), save_dirname=True)

    def save_to_query(self):  # save UI data in a Query
        # type: () -> Query
        query = self.query
        query.category = self.category_name
        query.title = self.title.get_text()
        if self.selected_objects.get_active():
            scope = "selected"
        elif self.all_objects.get_active():
            scope = "all"
        elif self.filtered_objects.get_active():
            scope = "filtered"
        query.scope = scope
        query.expressions = get_text(self.expressions)
        query.filter = get_text(self.filter)
        query.statements = get_text(self.statements)
        query.initial_statements = get_text(self.initial_statements)

        query.unwind_lists = self.unwind_lists.get_active()
        query.commit_changes = self.commit_checkbox.get_active()
        query.summary_only = self.summary_checkbox.get_active()
        return query
    
    def savestate(self, filename, save_dirname=False):
        # type: (str, bool) -> Query
        query = self.save_to_query()
        scriptfile = ScriptFile()
        scriptfile.save(filename, query, save_dirname)
        return query

    def savestate_to_note(self, note):
        # type: (Note) -> Query
        query = self.save_to_query()
        text = query.to_text()
        note.set(text)
        return query

    def select_category(self):
        # type: () -> None
        self.execute_func = None
        if self.uistate.viewmanager.active_page is None: return
        if not self.db.is_open(): return
        self.category_name = self.uistate.viewmanager.active_page.get_category()
        self.category = supertool_utils.get_category_info(self.db, self.category_name)
        
    def set_error(self, msg, context="", codeline="", src="", fname="", linenum=0):
        # type: (str, str, str, str, str, int) -> None
        msg = html.escape(msg)
        codeline = html.escape(codeline)
        s = "<span font_family='monospace' color='red' size='larger'>{msg}</span>"
        if context:
            s += "\n<span font_family='sans-serif'>{context}</span>"
        if src:
            s += "\nIn <span font_family='serif' background='white'>{src}</span>"
        if fname:
            s += "\nIn <span font_family='serif' background='white'>{fname}</span>"
        if linenum:
            s += "\nOn line {linenum}"
        if codeline:
            s += "\n<span font_family='monospace' background='white'>{codeline}</span>"
            
        s = s.format(
                msg=msg.replace("<", "&lt;"),
                context=context.replace("<", "&lt;"),
                src=src.replace("<", "&lt;"),
                fname=fname.replace("<", "&lt;"),
                linenum=linenum,
                codeline=codeline.replace("<", "&lt;"),
        )
        self.errormsg.set_markup(s)

    def set_font(self, widget):
        # type: (Gtk.Widget) -> None
        font = widget.get_font()
        font_description = widget.get_font_desc()
        self.window.modify_font(font_description)
        config.set("defaults.font", font)
        config.save()

    def set_window_title(self, modified):
        # type: (bool) -> None
        title = self.window.get_title()
        if modified:
            if not title.startswith("* "):
                self.window.set_title("* " + title)
        else:
            if title.startswith("* "):
                self.window.set_title(title[2:])
    
    def settings_dialog(self, _widget):
        # type: (Gtk.Widget) -> None
        dialog = self.settings.toplevel
        config.load()
        loc = config.get("defaults.include_location")
        loc_entry = self.settings.get_child_object("include_location")
        loc_entry.set_filename(loc)
        dialog.run()
        self.settings.toplevel.hide()

    def show_about_dialog(self, _widget):
        # type: (Gtk.Widget) -> None
        rsp = self.about_dialog.run()
        self.about_dialog.hide()

    def show_description(self, _widget, _event):
        # type: (Gtk.Widget, Gtk.Event) -> None
    
        def handle_response(dialog, response):
            # type: (Gtk.Dialog, int) -> None
            if response == Gtk.ResponseType.OK:
                # save description in current query
                self.query.description = dialog.get_description()
                self.content_changed(None)
                
            dialog.destroy()
            self.desc_win = None
        
        if self.desc_win:
            self.desc_win.destroy()
        self.desc_win =  DescriptionDialog(parent=self.uistate.window)
        dialog = self.desc_win
        dialog.set_description(self.query.description)
        dialog.connect("response", handle_response)

    

# -------------------------------------------------------------------------
#
# Tool
#
# -------------------------------------------------------------------------
class Tool(tool.Tool):
    def __init__(self, dbstate, user, options_class, name, callback=None):
        # type: (Any, Any, Any, str, Callable) -> None
        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        tool.Tool.__init__(self, dbstate, options_class, name)
        pd = self.get_plugindata(name)
        if not self.uistate:  # CLI mode
            print()
            print("SuperTool v" + pd.version)
            do_profile = self.options.handler.options_dict.get("profile")
            if do_profile:
                profile(self.run_cli)
            else:
                self.run_cli()
            return
        self.run(pd)

    def get_plugindata(self, plugin_id):
        # type: (str) -> Any
        preg = PluginRegister.get_instance()
        return preg.get_plugin(plugin_id)
    
    def run_cli(self):
        # type: () -> None
        script_filename = self.options.handler.options_dict["script"]
        if not script_filename:
            print("No script_filename")
            return
        if not os.path.exists(script_filename):
            print("Script file '{}' does not exist".format(script_filename))
            return
        output_param = self.options.handler.options_dict.get("output")
        if output_param.endswith(":a"):
            output_filename = output_param[:-2]
            open_mode = "a"
        else:
            output_filename = output_param
            open_mode = "w"
        # print("script_filename:", script_filename)
        scriptfile = ScriptFile()
        # print("scriptfile:", scriptfile)
        query = scriptfile.load(script_filename)
        query.dirname = str(Path(script_filename).parent)
        # print("query:", query)
        # print(self.options.handler.options_dict)
        category_name = self.options.handler.options_dict.get("category")
        if not category_name:
            category_name = query.category
        if not category_name:
            print("No category name specified")
            return
        print("category_name:", category_name)
        t1 = time.time()
        category = supertool_utils.get_category_info(self.db, category_name)
        if category.objclass:
            selected_handles = category.get_all_objects_func()
        else:
            selected_handles = []

        args = self.options.handler.options_dict["args"]
        gramps_engine = GrampsEngine(
            self.dbstate,
            self.user,
            category,
            selected_handles,
            query,
            env={"args":args, "category":category_name, "namespace":category.objclass}
        )
        result = Result()
        if output_filename:
            f = csv.writer(open(output_filename, open_mode, encoding='utf-8'))
        with DbTxn("Generating values", self.db) as trans:
            for values in gramps_engine.get_values(trans, result):
                if output_filename:
                    f.writerow(values)
                else:
                    print(json.dumps(values))
        t2 = time.time()

        msg = "Objects: {}/{} ({:.2f}s)".format(
            gramps_engine.object_count, gramps_engine.total_objects, t2 - t1
        )
        print(msg)

    def run(self, plugindata):
        # type: (Any) -> None
        m = SuperTool(self.user, self.dbstate, plugindata)


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
        # type: (str, str) -> None
        tool.ToolOptions.__init__(self, name, person_id)
        #print("person_id:", person_id)

        self.options_dict = dict(
            script="",
            output="",
            category="",
            args="",
            profile=0,
        )
        self.options_help = dict(
            script=(
                "=str",
                "Script file name",
                "A {} file name".format(SCRIPTFILE_EXTENSION),
            ),
            output=("=str", "Output CSV file name (optional)", "a CSV file name"),
            category=(
                "=str",
                "Object category (optional)",
                [
                    "People",
                    "Families",
                    "Events",
                    "Places",
                    "Citations",
                    "Sources",
                    "Repositories",
                    "Notes",
                ],
                False,
            ),
            args=("=str", "Any string argument", "string"),
            profile=("=0/1", "Display profiling information after execution", 
                     [
                         "0 - do not use profiling",
                         "1 - use profiling"
                     ], False)
        )
