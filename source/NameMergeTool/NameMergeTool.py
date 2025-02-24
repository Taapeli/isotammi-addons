#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020 Kari Kujansuu
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

from collections import defaultdict
from enum import Enum, auto
import os
import traceback

# from dataclasses import dataclass

from gi.repository import Gtk, Gdk

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.db import DbTxn
from gramps.gen.db import DbReadBase
from gramps.gen.dbstate import DbState
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import Name
from gramps.gen.lib import Person
from gramps.gen.user import User

from gramps.gui.dbguielement import DbGUIElement
from gramps.gui.glade import Glade
from gramps.gui.dialog import OkDialog
from gramps.gui.displaystate import DisplayState
from gramps.gui.editors import EditPerson
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.plug import tool


try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

do_logging = False
do_trace = True
tracefile = __file__ + ".trace.txt"

MAIN = "main"
PLIST = "plist"
SLIST = "slist"
TREEVIEW = "treeview"
SEARCHTEXT = "searchtext"
FINDBUTTON = "find-button"
MERGEBUTTON = "merge-button"
RESETBUTTON = "reset-button"
OPENBUTTON = "open-button"
CLOSEBUTTON = "close-button"

from gramps.gen.config import config as configman

config = configman.register_manager("name_merge_tool")
config.register("defaults.set_gender", "1")
config.register("defaults.save_original_names", "0")


class Nametype(Enum):
    FIRSTNAME = auto()
    PATRONYME = auto()
    SURNAME = auto()


try:
    from typing import List, Tuple, Optional, Any, Callable, Union

    Pinfo = List[Tuple[str, str, str]]  # pname,handle,grampsid
    Nameinfo = List[Tuple[Tuple[str, int], Pinfo]]  # (name,gender),[plinfo...]
except:
    pass

# @dataclass
class Row:
    def __init__(self, name, gender, count, rownum, deleted, plist):
        # type: (Row, str, str, int, int, bool, Pinfo) -> None
        self.name = name
        self.gender = gender
        self.count = count
        self.rownum = rownum
        self.deleted = deleted
        self.plist = plist


def gender_string_to_code(gender_string):
    # type: (Optional[str]) -> int
    if gender_string == "MALE":
        return Person.MALE
    if gender_string == "FEMALE":
        return Person.FEMALE
    if gender_string == "UNKNOWN":
        return Person.UNKNOWN
    return -1


def fetch_names(db):
    # type: (DbReadBase) -> Tuple[Nameinfo,Nameinfo,Nameinfo]
    n = 0
    firstnameset = defaultdict(list)
    suffixset = defaultdict(list)
    surnameset = defaultdict(list)
    for person_handle in db.get_person_handles():  # type: str
        person = db.get_person_from_handle(person_handle)
        names = person_names(person)
        gender = person.get_gender()  # type: int
        pname = name_displayer.display(person)  # type: str
        for index, name in enumerate(names):
            if name.get_type() == "Original": continue
            firstnames = name.get_first_name()  # type: str
            surnames = name.get_surname_list()
            if len(surnames) > 1:
                print()
                print("Monta sukunimeä:", pname)
            firstnames = firstnames.replace(".", ". ")
            for firstname in firstnames.split():
                firstnameset[(firstname, gender)].append(
                    (pname, person_handle, person.gramps_id)
                )
                n += 1
            suffix = name.get_suffix()  # type: str
            if suffix:
                suffixset[(suffix, gender)].append(
                    (pname, person_handle, person.gramps_id)
                )
            for surname in surnames:
                sname = surname.get_surname()
                if sname:
                    surnameset[(sname, -1)].append(
                        (pname, person_handle, person.gramps_id)
                    )
    print(n, "names")

    import locale
    def sortfunc_fi(nametuple):
        return locale.strxfrm(nametuple[0][0].lower().replace("w", "v"))
    def sortfunc_other(nametuple):
        return locale.strxfrm(nametuple[0][0].lower())
    
    lang = locale.getlocale(locale.LC_COLLATE)[0].split("_")[0]
    if lang in ["fi", "sv"]:
        sortfunc = sortfunc_fi
    else:
        sortfunc = sortfunc_other
 
    firstnamelist = sorted(firstnameset.items(), key=sortfunc)
    suffixlist = sorted(suffixset.items(), key=sortfunc)
    surnamelist = sorted(surnameset.items(), key=sortfunc)
    return firstnamelist, suffixlist, surnamelist


lastmod = 0.0

# -------------------------------------------------------------------------
#
# Tool
#
# -------------------------------------------------------------------------
class Tool(tool.Tool):
    def __init__(
        self,
        dbstate,  # type: DbState
        user,  # type: User
        options_class,  # type: tool.ToolOptions
        name,  # type: str
        callback=None,  # type: Callable
    ):
        # type: (...) -> None

        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        tool.Tool.__init__(self, dbstate, options_class, name)
        if not self.check_filechange():
            return
        try:
            self.run()
        except:
            traceback.print_exc()

    def check_filechange(self):
        # type: () -> bool
        global lastmod
        modtime = os.stat(__file__).st_mtime
        if lastmod and lastmod < modtime:
            OkDialog("File changed", "Please reload")
            return False
        lastmod = modtime
        return True

    def run(self):
        # type: () -> None
        firstnamelist, suffixlist, surnamelist = fetch_names(self.db)
        try:
            d = NameDialog(
                self.uistate, self.dbstate, firstnamelist, suffixlist, surnamelist
            )
        except:
            traceback.print_exc()


def person_names(person):
    # type: (Person) -> List[Name]
    return [person.get_primary_name()] + person.get_alternate_names()


class MyTreeView(Gtk.TreeView):
    def __init__(self):
        # type: () -> None
        Gtk.TreeView.__init__(self)

        # renderer = Gtk.CellRendererText()
        # col = Gtk.TreeViewColumn('Text2',renderer, text=1)
        # self.append_column(col)


class MyListModel(Gtk.ListStore):
    def __init__(self, treeview, columns, event_func):
        # type: (MyTreeView, List[Tuple[str, int, int]], Callable) -> None
        Gtk.ListStore.__init__(self, str, str, int, int)  # name, gender, count, rownum
        self.event_func = event_func
        treeview.set_model(self)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        renderer = Gtk.CellRendererText()
        for (title, colnum, width) in columns:
            col = Gtk.TreeViewColumn(title, renderer, text=colnum)
            col.set_clickable(True)
            # col.set_sort_column_id(colnum)
            col.set_resizable(True)
            treeview.append_column(col)
        # treeview.connect('button-press-event', self.__button_press)

    def add(self, row):
        # type: (List[Union[int, str]]) -> None
        node = self.append()
        for col, value in enumerate(row):
            self.set_value(node, col, value)

    def __button_press(self, obj, event):
        # type: (Any, Any) -> bool
        """
        Called when a button press is executed
        """
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.event_func(obj)
            return True
        return False


class NameDialog(ManagedWindow, DbGUIElement):
    def __init__(
        self,
        uistate,  # type: DisplayState
        dbstate,  # type: DbState
        firstnamelist,  # type: List[Tuple[Tuple[str, int], List[Tuple[str, str, str]]]]
        suffixlist,  # type: List[Tuple[Tuple[str, int], List[Tuple[str, str, str]]]]
        surnamelist,  # type: List[Tuple[Tuple[str, int], List[Tuple[str, str, str]]]]
    ):
        # type: (...) -> None
        self.uistate = uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        self.firstnamelist = firstnamelist
        self.suffixlist = suffixlist
        self.surnamelist = surnamelist
        self.names = firstnamelist
        self.nametype: Nametype = Nametype.FIRSTNAME
        self.rows: List[Row] = []
        self.personlist = None  # type: Optional[Personlist]
        # print(names)

        ManagedWindow.__init__(self, self.uistate, [], self.__class__, modal=False)
        # the self.top.run() below makes Gtk make it modal, so any change to
        # the previous line's "modal" would require that line to be changed
        DbGUIElement.__init__(self, dbstate.db)

        

        try:
            self.draw_window()
            config.load()
            self.set_gender.set_active(
                config.get("defaults.set_gender") == "1"
            )
            self.save_original_names.set_active(
                config.get("defaults.save_original_names") == "1"
            )
            ok = True
        except:
            traceback.print_exc()
            OkDialog("Error occurred", traceback.format_exc() + "\n\nRestart Gramps.")
            ok = False
        self.set_window(self.top, None, _("Name merge tool"))
        self.setup_configs("interface.namemerge", 920, 680)
        if ok:
            self.reset(None)
            self.show()

    # see ManagedWindow.clean_up
    def clean_up(self):
        # type: () -> None
        if self.personlist:
            self.personlist.close()
        self.callman.disconnect_all()
        print("done")

    def draw_window(self):
        # type: () -> Gtk.Window
        """Draw the dialog box."""
        glade = Glade(toplevel=MAIN)
        self.glade = glade
        self.top = glade.toplevel
        self.personlist = None

        # None.x

        columns = [
            (_("Name"), 0, 200),
            (_("Gender"), 1, 20),
            (_("Count"), 2, 20),
        ]
        #                   ('',-1,0)]
        self.nameview = MyTreeView()
        self.namemodel = MyListModel(
            self.nameview, columns, event_func=self.cb_double_click
        )
        self.init()

        find = glade.get_child_object(FINDBUTTON)
        find.connect("clicked", self.find)

        reset = glade.get_child_object(RESETBUTTON)
        reset.connect("clicked", self.reset)

        self.searchtext = glade.get_child_object(SEARCHTEXT)

        slist = glade.get_child_object(SLIST)  # GetkScrolledWindow
        slist.add(self.nameview)

        merge_button = glade.get_child_object(MERGEBUTTON)
        merge_button.connect("clicked", self.merge)

        # colorh = "#cc6666"
        colorh = "#22dd22"
        color = Gdk.RGBA()
        color.parse(colorh)
        color.to_string()
        merge_button.override_background_color(Gtk.StateFlags.NORMAL, color)

        self.nametype_firstname = glade.get_child_object("nametype_firstname")
        self.nametype_firstname.connect("clicked", self.change_nametype)

        self.nametype_patronyme = glade.get_child_object("nametype_patronyme")
        self.nametype_patronyme.connect("clicked", self.change_nametype)

        self.nametype_surname = glade.get_child_object("nametype_surname")
        self.nametype_surname.connect("clicked", self.change_nametype)

        self.gender_male = glade.get_child_object("gender_male")
        self.gender_male.connect("clicked", self.find)

        self.gender_female = glade.get_child_object("gender_female")
        self.gender_female.connect("clicked", self.find)

        self.gender_unknown = glade.get_child_object("gender_unknown")
        self.gender_unknown.connect("clicked", self.find)

        self.set_gender = glade.get_child_object("set_gender")
        # self.set_gender.connect('clicked', self.find)

        self.save_original_names = glade.get_child_object("save_original_names")

        refresh_button = glade.get_child_object("refresh_button")
        refresh_button.connect("clicked", self.refresh)

        self.lbl_namecount = glade.get_child_object("lbl_namecount")
        self.lbl_personcount = glade.get_child_object("lbl_personcount")

        self.top.connect("key-press-event", self.keypress)

        self.treeview = self.glade.get_child_object(TREEVIEW)

        renderer = Gtk.CellRendererText()
        columns = [("Id", 0, 50), ("Nimi", 1, 300)]
        for (title, colnum, width) in columns:
            col = Gtk.TreeViewColumn(title, renderer, text=colnum, weight_set=True)
            col.set_clickable(True)
            col.set_sort_column_id(colnum)
            col.set_resizable(True)
            self.treeview.append_column(col)
        store = Gtk.ListStore(str, str, str)
        self.treeview.set_model(store)

        select = self.nameview.get_selection()
        select.connect("changed", self.on_tree_selection_changed)

        self.open_button = glade.get_child_object(
            OPENBUTTON
        )  # cannot use id 'open_button'!!???
        self.open_button.connect("clicked", self.__open_selected)
        self.open_button.set_sensitive(False)

        self.treeview.connect("button-press-event", self.__button_press)
        self.treeview.connect("button-release-event", self.__button_press)
        select = self.treeview.get_selection()
        select.connect("changed", self.on_personlist_selection_changed)

        return self.top

    def keypress(self, obj, event):
        # type: (Gtk.Widget, Gdk.Event) -> None
        if event.keyval == Gdk.KEY_Escape:
            self.close()

    def change_nametype(self, obj):
        # type: (Gtk.Widget) -> None
        if self.nametype_firstname.get_active() and self.nametype != Nametype.FIRSTNAME:
            self.names = self.firstnamelist
            self.nametype = Nametype.FIRSTNAME
            self.gender_male.set_sensitive(True)
            self.gender_female.set_sensitive(True)
            self.gender_unknown.set_sensitive(True)
            self.set_gender.set_sensitive(True)
            self.init()
            self.reset(None)
        if self.nametype_patronyme.get_active() and self.nametype != Nametype.PATRONYME:
            self.names = self.suffixlist
            self.nametype = Nametype.PATRONYME
            self.gender_male.set_sensitive(True)
            self.gender_female.set_sensitive(True)
            self.gender_unknown.set_sensitive(True)
            self.set_gender.set_sensitive(True)
            self.init()
            self.reset(None)
        if self.nametype_surname.get_active() and self.nametype != Nametype.SURNAME:
            self.names = self.surnamelist
            self.nametype = Nametype.SURNAME
            self.gender_male.set_sensitive(False)
            self.gender_female.set_sensitive(False)
            self.gender_unknown.set_sensitive(False)
            self.set_gender.set_sensitive(False)
            self.init()
            self.reset(None)

    def on_tree_selection_changed(self, selection):
        # type: (Gtk.TreeSelection) -> None
        self.selection = selection
        (model, rows) = selection.get_selected_rows()
        store = Gtk.ListStore(str, str, str)

        plist2 = []
        for row in rows:
            ref = Gtk.TreeRowReference(model, row)
            rownum = model.get_value(model.get_iter(ref.get_path()), 3)
            plist = self.rows[rownum].plist
            plist2.extend(plist)

        for pname, handle, grampsid in sorted(plist2):
            store.append([grampsid, pname, handle])
        self.treeview.set_model(store)

    def cb_double_click(self, treeview):
        # type: (Gtk.TreeView) -> None
        """
        Handle double click on treeview.
        """
        (model, rows) = treeview.get_selection().get_selected_rows()
        if len(rows) != 1:
            return

        ref = Gtk.TreeRowReference(model, rows[0])
        try:
            rownum = model.get_value(model.get_iter(ref.get_path()), 3)
            row = self.rows[rownum]
            sortedlist = sorted(row.plist)
            self.personlist = Personlist(self.uistate, self.dbstate, sortedlist)
        except WindowActiveError as e:
            traceback.print_exc()
            if self.personlist:
                self.personlist.close()
                sortedlist = sorted(row.plist)
                self.personlist = Personlist(self.uistate, self.dbstate, sortedlist)
        except:
            traceback.print_exc()

    def on_personlist_selection_changed(self, selection):
        # type: (Gtk.TreeSelection) -> None
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.open_button.set_sensitive(False)
        else:
            self.open_button.set_sensitive(True)

    def __open_selected(self, obj):
        # type: (Gtk.Widget) -> None
        model, treeiter = self.treeview.get_selection().get_selected()
        if not treeiter:
            return
        row = list(model[treeiter])
        handle = row[2]
        person = self.dbstate.db.get_person_from_handle(handle)
        EditPerson(self.dbstate, self.uistate, [], person)

    def __button_press(self, treeview, event):
        # type: (Gtk.TreeView, Gdk.Event) -> bool
        """
        Called when a button press is executed
        """
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
            self.set_active_person()
            return False
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.__open_selected(None)
            return True
        return False

    def set_active_person(self):
        # type: () -> None
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter is None:
            return
        row = list(model[treeiter])
        handle = row[2]
        self.uistate.set_active(handle, "Person")

    def gender_ok(self, gender):
        # type: (str) -> bool
        if self.nametype == Nametype.SURNAME:
            return True
        if self.gender_male.get_active() and gender == "MALE":
            return True
        if self.gender_female.get_active() and gender == "FEMALE":
            return True
        if self.gender_unknown.get_active() and gender == "UNKNOWN":
            return True
        return False

    def refresh(self, obj):
        # type: (Gtk.Widget) -> None
        self.firstnamelist, self.suffixlist, self.surnamelist = fetch_names(self.db)
        if self.nametype == Nametype.FIRSTNAME:
            self.names = self.firstnamelist
        if self.nametype == Nametype.PATRONYME:
            self.names = self.suffixlist
        if self.nametype == Nametype.SURNAME:
            self.names = self.surnamelist
        self.init()
        self.find(None)

    def findtext(self, text):
        # type: (str) -> None
        self.namemodel.clear()
        self.namecount = 0
        self.personcount = 0
        # for [firstname,gender,count,rownum,is_deleted,plist] in self.rows:
        for row in self.rows:
            if row.deleted:
                continue
            if not self.gender_ok(row.gender):
                continue
            if row.name.lower().find(text) >= 0:
                self.namemodel.add([row.name, row.gender, row.count, row.rownum])
                self.namecount += 1
                self.personcount += row.count
        self.lbl_namecount.set_text(str(self.namecount))
        self.lbl_personcount.set_text(str(self.personcount))

    def find(self, obj):
        # type: (Gtk.Widget) -> None
        text = self.searchtext.get_text().lower()
        self.findtext(text)

    def reset(self, obj):
        # type: (Optional[Gtk.Widget]) -> None
        self.findtext("")

    def init(self):
        # type: () -> None
        self.namemodel.clear()
        rownum = 0
        self.rows = []
        for (name, gender), plist in self.names:
            if gender == Person.MALE:
                genderstring = "MALE"
            elif gender == Person.FEMALE:
                genderstring = "FEMALE"
            elif gender == -1:
                genderstring = ""
            else:
                genderstring = "UNKNOWN"
            count = len(plist)
            self.rows.append(Row(name, genderstring, count, rownum, False, plist))
            rownum += 1

    def merge(self, obj):
        # type: (Any) -> None
        config.set("defaults.set_gender", 
           "1" if self.set_gender.get_active() else "0"
        )
        config.set("defaults.save_original_names", 
           "1" if self.save_original_names.get_active() else "0"
        )
        config.save()

        (model, rows) = self.nameview.get_selection().get_selected_rows()
        names = []
        maxcount = 0
        maxindex = 0
        for index, row in enumerate(rows):
            ref = Gtk.TreeRowReference(model, row)
            path = ref.get_path()  # essentially a row number?
            row = list(model[path])
            name = row[0]  # type: str
            gender = row[1]  # type: str
            count = row[2]  # type: int
            if count > maxcount:
                maxcount = count
                maxindex = index
            names.append((name, gender))
        ok = self.select_primary(names, maxindex)
        if not ok:
            return
        self.new_gender_code = gender_string_to_code(self.new_gender)
        title = _("Merging names")
        it1 = None
        count = 0
        merged_rows = []
        with DbTxn(title, self.db) as self.trans:
            for row in rows[::-1]:
                ref = Gtk.TreeRowReference(model, row)
                path = ref.get_path()  # essentially a row number?
                it = model.get_iter(path)
                row = list(model[path])
                name = row[0]
                gender = row[1]
                count += row[2]
                rownum = row[3]
                if (name, gender) == self.primary_name:
                    it1 = it
                    remaining_row = self.rows[rownum]
                    continue
                model.remove(it)
                self.rows[rownum].deleted = True  # is_deleted
                merged_rows.append(self.rows[rownum])
            if it1:
                self.nameview.get_selection().unselect_all()
                self.nameview.get_selection().select_iter(it1)
                self.merge_individuals(remaining_row, merged_rows)
                if self.set_gender.get_active():
                    model[it1][1] = self.new_gender
                    rownum = model[it1][3]
                    self.rows[rownum].gender = self.new_gender
                model[it1][2] = count
                self.namecount -= len(merged_rows)
                self.lbl_namecount.set_text(str(self.namecount))
            else:
                raise
        selection = self.nameview.get_selection()
        self.on_tree_selection_changed(selection)  # update the person list

    def merge_individuals(self, remaining_row, merged_rows):
        # type: (Row,List[Row]) -> str
        remaining_name = remaining_row.name
        remaining_gender = remaining_row.gender
        if self.nametype != Nametype.SURNAME and self.set_gender.get_active():
            if remaining_gender != self.new_gender:
                # must update the gender for the "remaining" individuals also
                for pname, person_handle, grampsid in remaining_row.plist:
                    person = self.db.get_person_from_handle(person_handle)
                    self.replace_gender(person, self.new_gender_code)

        for row in merged_rows:
            for pname, person_handle, grampsid in row.plist:
                person = self.db.get_person_from_handle(person_handle)
                self.replace_name(person, row.name, remaining_name)
                if self.set_gender.get_active() and row.gender != self.new_gender:
                    self.replace_gender(person, self.new_gender_code)
            remaining_row.plist.extend(row.plist)
            remaining_row.count = len(remaining_row.plist)
            if do_trace:
                with open(tracefile, "a") as f:
                    ntype = "?"
                    if self.nametype == Nametype.FIRSTNAME:
                        ntype = "F"
                    if self.nametype == Nametype.PATRONYME:
                        ntype = "P"
                    if self.nametype == Nametype.SURNAME:
                        ntype = "S"
                    gendertype = "?"
                    if self.gender_male.get_active():
                        gendertype = "M"
                    if self.gender_female.get_active():
                        gendertype = "F"
                    print(ntype, gendertype, row.name, "=>", remaining_name, file=f)


    def replace_name(self, person, old_name, new_name):
        # type: (Person, str, str) -> None
        names = person_names(person)
        pname = name_displayer.display(person)
        for name in names:
            data1 = name.serialize()
            if name.get_type() == "Original": continue
            if self.nametype == Nametype.FIRSTNAME:
                firstnames = name.get_first_name()
                firstnames = firstnames.replace(".", ". ")
                newnames = []
                for firstname in firstnames.split():
                    if firstname == old_name:
                        firstname = new_name
                    newnames.append(firstname)
                firstnames = " ".join(newnames)
                name.set_first_name(firstnames)
            if self.nametype == Nametype.PATRONYME:
                suffix = name.get_suffix()
                if suffix == old_name:
                    name.set_suffix(new_name)

            surnames = name.get_surname_list()
            for surname in surnames:
                if surname.get_surname() == old_name:
                    surname.set_surname(new_name)

            data2 = name.serialize()
            if self.save_original_names.get_active() and data1 != data2:
                oldname = Name()
                oldname.unserialize(data1)
                oldname.set_type("Original")
                person.add_alternate_name(oldname)

        new_pname = name_displayer.display(person)
        if do_logging:
            print(person.gramps_id, pname, "=>", new_pname)
        self.db.commit_person(person, self.trans)

    def replace_gender(self, person, new_gender_code):
        # type: (Person, int) -> None
        person.set_gender(new_gender_code)
        self.db.commit_person(person, self.trans)

    def select_primary(self, names, maxindex):
        # type: (List[Tuple[str,str]], int) -> bool
        def cb_set_primary_name(obj, name_and_gender):
            # type: (Gtk.Widget, Tuple[str,str]) -> None
            self.primary_name = name_and_gender

        dialog = Gtk.Dialog(
            title=_("Select primary name"), parent=None, flags=Gtk.DialogFlags.MODAL
        )
        lbl1 = Gtk.Label()
        lbl1.set_markup("<b>" + _("Select primary name:") + "</b>")
        lbl1.set_halign(Gtk.Align.START)
        dialog.vbox.pack_start(lbl1, False, False, 5)
        # self.primary_name = None
        group = None
        self.new_gender = "UNKNOWN"
        frame = Gtk.Frame()
        vbox = Gtk.VBox()
        for index, (name, gender) in enumerate(names):
            group = Gtk.RadioButton.new_with_label_from_widget(
                group, name + " - " + gender
            )
            group.connect("toggled", cb_set_primary_name, (name, gender))
            vbox.pack_start(group, False, True, 0)
            # first one is the default:
            if index == maxindex:
                group.set_active(True)
                self.primary_name = (name, gender)
            if gender != "UNKNOWN":
                self.new_gender = gender
        frame.add(vbox)
        dialog.vbox.pack_start(frame, False, True, 0)

        if self.primary_name[1] != "UNKNOWN":
            self.new_gender = self.primary_name[1]
            
        if self.set_gender.get_active():
            frame = Gtk.Frame()
            genderbox = Gtk.VBox()
            
            gender_male = Gtk.RadioButton.new_with_label_from_widget(
                    None, _("Male")
                )
            gender_female = Gtk.RadioButton.new_with_label_from_widget(
                    gender_male, _("Female")
                )
            gender_unknown = Gtk.RadioButton.new_with_label_from_widget(
                    gender_male, _("Unknown")
                )
            genderbox.add(gender_male)
            genderbox.add(gender_female)
            genderbox.add(gender_unknown)
            if self.new_gender == "MALE":
                gender_male.set_active(True)
            if self.new_gender == "FEMALE":
                gender_female.set_active(True)
            if self.new_gender == "UNKNOWN":
                gender_unknown.set_active(True)
    
            dialog.vbox.add(Gtk.Label(""))
            genderlabel = Gtk.Label()
            genderlabel.set_markup("<b>" + _("Set Gender:") + "</b>")
            genderlabel.set_halign(Gtk.Align.START)
            dialog.vbox.add(genderlabel)
            frame.add(genderbox)
            dialog.vbox.add(frame)

        dialog.add_button("Ok", Gtk.ResponseType.OK)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        result = dialog.run()
        self.new_gender = "UNKNOWN"
        if self.set_gender.get_active():
            if gender_male.get_active(): self.new_gender = "MALE"
            if gender_female.get_active(): self.new_gender = "FEMALE"
        dialog.destroy()
        if result == Gtk.ResponseType.OK:
            return True
        return False


class Personlist(ManagedWindow):
    def __init__(self, uistate, dbstate, plist):
        # type: (DisplayState, DbState, Pinfo) -> None
        self.uistate = uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        self.plist = plist

        ManagedWindow.__init__(self, self.uistate, [], self.__class__, modal=False)
        store = Gtk.ListStore(str, str, str)
        for pname, handle, grampsid in self.plist:
            store.append([grampsid, pname, handle])
        self.draw_window()
        self.treeview.set_model(store)
        self.set_window(self.top, None, _("Show person"))
        self.top.show_all()

    def draw_window(self):
        # type: () -> None
        glade = Glade(toplevel=PLIST)
        self.glade = glade
        self.top = glade.get_child_object(PLIST)
        self.treeview = glade.get_child_object(TREEVIEW)
        renderer = Gtk.CellRendererText()
        columns = [("Id", 0), ("Nimi", 1)]
        for (title, colnum) in columns:
            col = Gtk.TreeViewColumn(title, renderer, text=colnum, weight_set=True)
            # if colnum == 1:
            # col.set_cell_data_func(renderer, datafunc)
            col.set_clickable(True)
            col.set_sort_column_id(colnum)
            col.set_resizable(True)
            self.treeview.append_column(col)

        open_button = glade.get_child_object(
            OPENBUTTON
        )  # cannot use id 'open_button'!!???
        open_button.connect("clicked", self.cb_open_selected)

        close_button = glade.get_child_object(CLOSEBUTTON)
        close_button.connect("clicked", self.close)

        self.treeview.connect("button-press-event", self.cb_button_press)
        self.treeview.connect("button-release-event", self.cb_button_press)

    def cb_open_selected(self, obj):
        # type: (Any) -> None
        model, treeiter = self.treeview.get_selection().get_selected()
        row = list(model[treeiter])
        handle = row[2]
        person = self.dbstate.db.get_person_from_handle(handle)
        EditPerson(self.dbstate, self.uistate, [], person)

    def cb_button_press(self, treeview, event):
        # type: (Any,Any) -> bool
        """
        Called when a button press is executed
        """
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
            self.set_active_person()
            return False
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.__open_selected(None)
            return True
        return False

    def set_active_person(self):
        # type: () -> None
        model, treeiter = self.treeview.get_selection().get_selected()
        row = list(model[treeiter])
        handle = row[2]
        self.uistate.set_active(handle, "Person")


# ------------------------------------------------------------------------
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
