#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021      Kari Kujansuu
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
# Name Editor Tool
# Author: kari.kujansuu@gmail.com, 2020-2021
#
import os
import traceback
import re
from collections import defaultdict
from gramps.gui.display import display_url

try:
    from typing import List, Tuple, Optional, Any, Callable, Union
except:
    pass

 
from gi.repository import Gtk, Gdk, GObject

from gramps.gen.lib import Person
from gramps.gen.lib import NameType

from gramps.gen.utils.callman import CallbackManager

from gramps.gui.editors import EditPerson
from gramps.gui.dbguielement import DbGUIElement
from gramps.gui.dialog import OkDialog
from gramps.gui.glade import Glade
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.plug import tool
from gramps.gui.views.listview import ListView

from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

lastmod = 0

import code, traceback, signal

def debug(sig, frame):
    traceback.print_stack()

def listen():
    signal.signal(signal.SIGUSR1, debug)


class Names:
    def __init__(self, displayname:str, prefix: str, surname: str, firstname: str, suffix: str, title:str):
        self.displayname = displayname
        self.prefix = prefix
        self.surname = surname
        self.firstname = firstname
        self.suffix = suffix
        self.title = title

class Row:
    def __init__(self,names: Names, nametype: str,gramps_id:str, gender:int, handle:str, is_primary:bool, rownum:int, nameindex:int):
        self.names = names
        self.nametype = nametype
        self.nametype_str = repr(nametype.serialize())
        self.gramps_id = gramps_id
        self.gender = gender
        self.handle = handle
        self.is_primary = is_primary
        self.rownum = rownum    # row index in NameDialog.names
        self.nameindex = nameindex

def getrow(person, nameindex, rownum):
    names  = person_names(person)
    name = names[nameindex]
    is_primary = (nameindex == 0)
    displayname = name.get_name()
    firstname = name.get_first_name()
    surnames = name.get_surname_list()
    for surname in surnames:
        prefix = surname.get_prefix()
        suffix = name.get_suffix()
        row = Row(Names(displayname,prefix,surname.get_surname(),firstname,suffix,name.get_title()),
               name.get_type(),
               person.gramps_id,
               person.gender,
               person.handle,
               is_primary,
               rownum,
               nameindex)
        return row  # use only first surname

def gender_string_to_code(gender_string):
    # type: (Optional[str]) -> int
    if gender_string == "MALE": return Person.MALE    
    if gender_string == "FEMALE": return Person.FEMALE    
    if gender_string == "UNKNOWN": return Person.UNKNOWN    
    return -1

def gender_code_to_string(gender_code:int) -> str:
    if gender_code == Person.MALE: return "M"    
    if gender_code == Person.FEMALE: return "F"    
    if gender_code == Person.UNKNOWN: return "?"    
    return "?"    

#-------------------------------------------------------------------------
#
# Tool
#
#-------------------------------------------------------------------------
class Tool(tool.Tool):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        tool.Tool.__init__(self, dbstate, options_class, name)
#        if not self.check_filechange():
#            return
        self.run()

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
        n = 0
        namelist = []
        rownum = 0
        for person_handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(person_handle)
            names  = person_names(person)
            pname = name_displayer.display(person)
            for nameindex,name in enumerate(names):
                row = getrow(person,nameindex,rownum=0) # set rownum in NameDialog after sorting
                namelist.append(row)
                n += 1
                rownum += 1
        try:
            d = NameDialog(self.uistate, self.dbstate, sorted(namelist, key=lambda row:row.names.displayname))
        except:
            traceback.print_exc()

def person_names(person):
    return [person.get_primary_name()] + person.get_alternate_names()
        
def datafunc(col, renderer, model, titer, data):
    is_primary = model.get_value(titer, 9)
    if is_primary:
        renderer.set_property("weight", 700)        
    else:
        renderer.set_property("weight", 0)        

class MyTreeView(Gtk.TreeView):
    def __init__(self):
        Gtk.TreeView.__init__(self)

class MyListModel(Gtk.ListStore):
    def __init__(self, treeview, columns, event_func ):
        Gtk.ListStore.__init__(self, str, str, str, str, str, str, str, str, str, int, int, int)
        self.event_func = event_func
        treeview.set_model(self)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        for (title, colnum, width) in columns:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=colnum, weight_set=True)
            if colnum == 7: # name type column
                col.set_cell_data_func(renderer, datafunc)
            col.set_clickable(True)
            #col.set_sort_column_id(colnum)
            col.set_resizable(True)
            treeview.append_column(col)
        treeview.connect('button-press-event', self.__button_press)
        
    def add(self, row):
        #print(row)
        node = self.append()
        for col,value in enumerate(row):
            self.set_value( node, col, value)

    def __button_press(self, obj, event):
        """
        Called when a button press is executed
        """
        if (event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1):
            self.event_func(obj)
            return True
        return False

class NameDialog(ManagedWindow, DbGUIElement):

    def __init__(self, uistate, dbstate, names ):
        self.uistate = uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        self.names = names
        self.nametypes = set()
        for rownum,row in enumerate(self.names):
            row.rownum = rownum
            code, text = row.nametype.serialize()
            self.nametypes.add((code,text))

        ManagedWindow.__init__(self, self.uistate, [], self.__class__, modal=False)
        # the self.top.run() below makes Gtk make it modal, so any change to
        # the previous line's "modal" would require that line to be changed
        DbGUIElement.__init__(self, dbstate.db)
        
        self.draw_window()
        self.set_window(self.top, None, _("Name editor"))
        self.setup_configs('interface.names', 400, 350)
        self.show()

    # see ManagedWindow.clean_up        
    def clean_up(self):        
        print("done")
        self.callman.disconnect_all()

    def show_help(self, obj):
        url = "http://wiki.isotammi.net/wiki/Name_Editor_Tool"
        display_url(url)

    def draw_window(self):
        """Draw the dialog box."""

        # Copied from PlaceCleanup:
        # Found out that Glade does not support translations for plugins, so
        # have to do it manually.
        import os
        import locale
        import ctypes
        from gramps.gen.constfunc import win
        base = os.path.dirname(__file__)
        glade_file = base + os.sep + "nameeditortool.glade"
        # This is needed to make gtk.Builder work by specifying the
        # translations directory in a separate 'domain'
        try:
            localedomain = "addon"
            localepath = base + os.sep + "locale"
            if hasattr(locale, 'bindtextdomain'):
                libintl = locale
            elif win():  # apparently wants strings in bytes
                localedomain = localedomain.encode('utf-8')
                localepath = localepath.encode('utf-8')
                libintl = ctypes.cdll.LoadLibrary('libintl-8.dll')
            else:  # mac, No way for author to test this
                libintl = ctypes.cdll.LoadLibrary('libintl.dylib')

            libintl.bindtextdomain(localedomain, localepath)
            libintl.textdomain(localedomain)
            libintl.bind_textdomain_codeset(localedomain, "UTF-8")
            # and finally, tell Gtk Builder to use that domain
            self.top.set_translation_domain("addon")
        except (OSError, AttributeError):
            # Will leave it in English
            print("Localization of PlaceCleanup failed!")
                    
        glade = Glade()
        self.glade = glade
        self.top = glade.toplevel

        columns = [(_('Id'), 0, 80),
                   (_('Gender'), 1, 100), 
                   (_('Prefix'), 2, 100), 
                   (_('Surname'), 3, 200), 
                   (_('First name'), 4, 200), 
                   (_('Suffix'), 5, 200), 
                   (_('Title'), 6, 300),
                   (_('Type'), 7, 100), 
                   ]
#                   ('',-1,0)]
        self.namelist = MyTreeView()
        self.namemodel = MyListModel(self.namelist, columns, event_func=self.cb_double_click)
        
        find = glade.get_child_object("find")
        find.connect('clicked', self.find_clicked)

        reset = glade.get_child_object("reset")
        reset.connect('clicked', self.reset_clicked)
        
        self.searchtext = glade.get_child_object("searchtext")
        self.searchtext.connect("key-press-event",self.keypress)

        slist = glade.get_child_object("slist")
        slist.add(self.namelist)
        #self.namelist.connect('button-release-event', self.__button_release)
        select = self.namelist.get_selection()
        select.connect("changed", self.on_selection_changed)


        self.replace_button = glade.get_child_object("replace")
        self.replace_button.connect('clicked', self.replace_clicked)

        button_undo = glade.get_child_object("button_undo")
        button_undo.connect('clicked', self.undo_clicked)

        
        clear_button = glade.get_child_object("clear_button")
        clear_button.connect('clicked', self.clear_form)

        editgrid = self.glade.get_child_object('editgrid')
        self.special_prefix = self.build_combobox()
        self.special_surname = self.build_combobox()
        self.special_firstname = self.build_combobox()
        self.special_suffix = self.build_combobox()
        self.special_title = self.build_combobox()
        
        self.old_prefix= self.glade.get_child_object("old_prefix")
        self.old_surname = self.glade.get_child_object("old_surname")
        self.old_firstname = self.glade.get_child_object("old_firstname")
        self.old_suffix = self.glade.get_child_object("old_suffix")
        self.old_title = self.glade.get_child_object("old_title")

        
        self.new_prefix = self.glade.get_child_object('new_prefix')
        self.new_surname = self.glade.get_child_object('new_surname')
        self.new_firstname = self.glade.get_child_object('new_firstname')
        self.new_suffix = self.glade.get_child_object('new_suffix')
        self.new_title = self.glade.get_child_object("new_title")

        editgrid.attach(self.special_prefix,2,1,1,1)
        editgrid.attach(self.special_surname,2,2,1,1)
        editgrid.attach(self.special_firstname,2,3,1,1)
        editgrid.attach(self.special_suffix,2,4,1,1)
        editgrid.attach(self.special_title,2,5,1,1)

        self.use_special = glade.get_child_object("use_special")
        self.use_special.connect('clicked', self.use_special_clicked)
        
        self.use_regex_checkbox = self.glade.get_child_object("use_regex") 

        self.find_use_regex = self.glade.get_child_object("find_regex") 

        self.find_all = self.glade.get_child_object("find_all") 
        self.find_prefix = self.glade.get_child_object("find_prefix") 
        self.find_surname = self.glade.get_child_object("find_surname") 
        self.find_firstname = self.glade.get_child_object("find_firstname") 
        self.find_suffix = self.glade.get_child_object("find_suffix") 
        self.find_title = self.glade.get_child_object("find_title") 

        self.find_type = self.glade.get_child_object("find_type") 
        self.fill_typecombo(self.find_type)

        self.old_nametype = self.glade.get_child_object("old_nametype") 
        self.fill_typecombo(self.old_nametype)

        self.new_nametype = self.glade.get_child_object("new_nametype") 
        self.fill_typecombo(self.new_nametype)

        self.type_primary = self.glade.get_child_object("type_primary") 
        self.type_alternate = self.glade.get_child_object("type_alternate") 

        self.find_all.connect('clicked', self.find_all_clicked)

        self.gender_all = self.glade.get_child_object("gender_all") 
        self.gender_male = self.glade.get_child_object("gender_male") 
        self.gender_female = self.glade.get_child_object("gender_female") 
        self.gender_unknown = self.glade.get_child_object("gender_unknown") 

        self.label_count = self.glade.get_child_object("label_count") 

        self.help_button = self.glade.get_child_object("help_button") 
        self.help_button.connect("clicked", self.show_help)
        
        self.find_in_progress = True
        self.reset_clicked(None)

        self.find_in_progress = False
        
        return self.top
    
    def clear_form(self, selection):
        self.glade.get_child_object("old_prefix").set_text("")
        self.glade.get_child_object("new_prefix").set_text("")
        self.glade.get_child_object("old_surname").set_text("")
        self.glade.get_child_object("new_surname").set_text("")
        self.glade.get_child_object("old_firstname").set_text("")
        self.glade.get_child_object("new_firstname").set_text("")
        self.glade.get_child_object("old_suffix").set_text("")
        self.glade.get_child_object("new_suffix").set_text("")
        self.glade.get_child_object("old_title").set_text("")
        self.glade.get_child_object("new_title").set_text("")
        self.special_prefix.set_active_id("none")
        self.special_surname.set_active_id("none")
        self.special_firstname.set_active_id("none")
        self.special_suffix.set_active_id("none")
        self.special_title.set_active_id("none")
        self.old_nametype.set_active_id("")
        self.new_nametype.set_active_id("")
                
    def on_selection_changed(self, selection):
        if self.find_in_progress: return
        (model, rows) = selection.get_selected_rows()
        self.replace_button.set_sensitive(len(rows) > 0)
        if len(rows) != 1:
            return
        row = rows[0]
        handle = list(model[row])[8]
        self.uistate.set_active(handle, 'Person')
        return False

        
    def keypress(self, obj, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):  # 65421 is keypad Enter
            self.find_clicked(None)

    def find_all_clicked(self, obj):
        if self.find_all.get_active():
            self.find_prefix.set_sensitive(False) 
            self.find_surname.set_sensitive(False) 
            self.find_firstname.set_sensitive(False) 
            self.find_suffix.set_sensitive(False) 
            self.find_title.set_sensitive(False) 
        else:
            self.find_prefix.set_sensitive(True) 
            self.find_surname.set_sensitive(True) 
            self.find_firstname.set_sensitive(True) 
            self.find_suffix.set_sensitive(True) 
            self.find_title.set_sensitive(True) 

    def gender_clicked(self, obj):
        print( self.gender_all.get_active())

    def undo_clicked(self, obj):
        self.uistate.viewmanager.undo()
        
    def use_special_clicked(self, obj):
        print("use_special")
        print(self.use_special.get_active())
        if self.use_special.get_active():
            self.old_prefix.set_sensitive(False)
            self.old_surname.set_sensitive(False)
            self.old_firstname.set_sensitive(False)
            self.old_suffix.set_sensitive(False)
            self.old_title.set_sensitive(False)
            
            self.new_prefix.set_visible(False)
            self.new_surname.set_visible(False)
            self.new_firstname.set_visible(False)
            self.new_suffix.set_visible(False)
            self.new_title.set_visible(False)
            
            self.special_prefix.show_all()
            self.special_surname.show_all()
            self.special_firstname.show_all()
            self.special_suffix.show_all()
            self.special_title.show_all()
            self.use_regex_checkbox.set_sensitive(False)
        else:
            self.old_prefix.set_sensitive(True)
            self.old_surname.set_sensitive(True)
            self.old_firstname.set_sensitive(True)
            self.old_suffix.set_sensitive(True)
            self.old_title.set_sensitive(True)

            self.new_prefix.set_visible(True)
            self.new_surname.set_visible(True)
            self.new_firstname.set_visible(True)
            self.new_suffix.set_visible(True)
            self.new_title.set_visible(True)
            
            self.special_prefix.set_visible(False)
            self.special_surname.set_visible(False)
            self.special_firstname.set_visible(False)
            self.special_suffix.set_visible(False)
            self.special_title.set_visible(False)
            self.use_regex_checkbox.set_sensitive(True)
            
    def build_combobox(self):
        combobox = Gtk.ComboBoxText.new()
        combobox.append('none',"")
        combobox.append('clear',_("Clear|name-editor"))
        combobox.append('from-prefix',_("Copy from prefix"))
        combobox.append('from-surname',_("Copy from surname"))
        combobox.append('from-firstname',_("Copy from firstname"))
        combobox.append('from-suffix',_("Copy from suffix"))
        combobox.append('from-title',_("Copy from title"))
        combobox.append('append-prefix',_("Append prefix"))
        combobox.append('append-surname',_("Append surname"))
        combobox.append('append-firstname',_("Append firstname"))
        combobox.append('append-suffix',_("Append suffix"))
        combobox.append('append-title',_("Append from title"))
        return combobox

    def fill_typecombo(self, combobox):
        combobox.append('',"")
        types = []
        for value in self.nametypes:
            nametype = NameType()
            nametype.set(value)
            types.append((str(nametype),repr(value)))
        for name,xmlname in sorted(types):
            combobox.append(xmlname, name)
        return combobox

    def cb_double_click(self, treeview):
        #row = self.namemodel.get_selected_row()
        #print(row)
        """
        Handle double click on treeview.
        """
        (model, rows) = treeview.get_selection().get_selected_rows()
        if len(rows) != 1:
            return

        ref = Gtk.TreeRowReference(model, rows[0])
        print(ref)
        try:
            handle = model.get_value(model.get_iter(ref.get_path()), 8)
            person = self.dbstate.db.get_person_from_handle(handle)
            EditPerson(self.dbstate, self.uistate, [], person)
        except:
            pass
        
    def rowmatch(self, row, text):
        if self.gender_male.get_active() and row.gender != Person.MALE: return False
        if self.gender_female.get_active() and row.gender != Person.FEMALE: return False
        if self.gender_unknown.get_active() and row.gender != Person.UNKNOWN: return False
        if self.find_type.get_active_id():
            if self.find_type.get_active_id() != row.nametype_str: return False

        if row.is_primary:
            if not self.type_primary.get_active(): 
                return False
        if not row.is_primary:
            if not self.type_alternate.get_active(): 
                return False
            
        if self.find_use_regex.get_active():
            if self.find_all.get_active():
                key = (row.gramps_id + " " + row.names.title + " " + row.names.displayname) 
                return re.search(text,key,re.IGNORECASE)
            if self.find_prefix.get_active(): 
                key = row.names.prefix;
                if re.search(text,key,re.IGNORECASE): return True
            if self.find_surname.get_active(): 
                key = row.names.surname;
                if re.search(text,key,re.IGNORECASE): return True
            if self.find_firstname.get_active(): 
                key = row.names.firstname;
                if re.search(text,key,re.IGNORECASE): return True
            if self.find_suffix.get_active(): 
                key = row.names.suffix;
                if re.search(text,key,re.IGNORECASE): return True
            if self.find_title.get_active(): 
                key = row.names.title;
                if re.search(text,key,re.IGNORECASE): return True
            return False
        else:
            if self.find_all.get_active():
                key = (row.gramps_id + " " + row.names.title + " " + row.names.displayname) 
            else:
                key = ""
                if self.find_prefix.get_active(): key += " " + row.names.prefix;
                if self.find_surname.get_active(): key += " " + row.names.surname;
                if self.find_firstname.get_active(): key += " " + row.names.firstname;
                if self.find_suffix.get_active(): key += " " + row.names.suffix;
                if self.find_title.get_active(): key += " " + row.names.title;
            return key.lower().find(text) >= 0
        
    def find_clicked(self, obj):
        self.find_in_progress = True
        text = self.searchtext.get_text().lower()
        self.namemodel.clear()
        self.map = defaultdict(list)  # handle to list on row numbers in the model
        self.label_count.set_text("")
        i = 0
        for row in self.names:
            if self.rowmatch(row, text):
                self.namemodel.add([row.gramps_id,gender_code_to_string(row.gender),
                                    row.names.prefix,row.names.surname,row.names.firstname,row.names.suffix,
                                    row.names.title,
                                    str(row.nametype),
                                    row.handle,row.is_primary,row.rownum,row.nameindex])
                self.map[row.handle].append((row.rownum,i,row.nameindex))
                i += 1
        self.namelist.get_selection().unselect_all()
        self.label_count.set_text(_("Names:") + "{}/{}".format(i, len(self.names)))
        self.find_in_progress = False
        self.replace_button.set_sensitive(False)

    def reset_clicked(self, obj):
        self.find_in_progress = True

        self.namemodel.clear()
        self.map = defaultdict(list)
        self.label_count.set_text("")
        i = 0
        #for name,type,title,id,handle,is_primary,rownum,index in self.names:
        for row in self.names:
            #(displayname,prefix,surname,firstname,suffix) = name
            self.namemodel.add([row.gramps_id,gender_code_to_string(row.gender),
                                row.names.prefix,row.names.surname,row.names.firstname,row.names.suffix,
                                row.names.title,
                                str(row.nametype),
                                row.handle,row.is_primary,row.rownum,row.nameindex])
            self.map[row.handle].append((row.rownum,i,row.nameindex))
            i += 1
        self.label_count.set_text(_("Names:") + "{}".format(i))
        self.replace_button.set_sensitive(False)
        self.find_in_progress = False

    
    def replace_clicked(self, obj):
        old_prefix_value = self.glade.get_child_object("old_prefix").get_text()
        new_prefix_value = self.glade.get_child_object("new_prefix").get_text()
        old_surname_value = self.glade.get_child_object("old_surname").get_text()
        new_surname_value = self.glade.get_child_object("new_surname").get_text()
        old_firstname_value = self.glade.get_child_object("old_firstname").get_text()
        new_firstname_value = self.glade.get_child_object("new_firstname").get_text()
        old_suffix_value = self.glade.get_child_object("old_suffix").get_text()
        new_suffix_value = self.glade.get_child_object("new_suffix").get_text()

        old_title_value = self.glade.get_child_object("old_title").get_text()
        new_title_value = self.glade.get_child_object("new_title").get_text()

        old_nametype = self.old_nametype.get_active_id()
        new_nametype = self.new_nametype.get_active_id()

        self.use_regex = self.glade.get_child_object("use_regex").get_active()

        (model, rows) = self.namelist.get_selection().get_selected_rows()
        #print(rows)
        self.num_replacements = 0

        msg = _("Updating names")
        with DbTxn(msg, self.db, batch=False) as self.trans:
            for i, row in enumerate(rows):
                ref = Gtk.TreeRowReference(model, row)
                changed = False
                try:
                    #print("path", ref.get_path())
                    path = ref.get_path()  # essentially a row number?
                    iter = model.get_iter(path)
                    handle = model.get_value(iter, 8)
                    rownum = model.get_value(iter, 10)
                    index = model.get_value(iter, 11)
    
                    person = self.db.get_person_from_handle(handle)
                    names  = person_names(person)
                    pname = name_displayer.display(person)
                    #print(handle, index, pname, path)
                    name = names[index]
                    orig_nametype = repr(name.get_type().serialize())
                    firstname = name.get_first_name()
                    title = name.get_title()
                    surnames = name.get_surname_list()
                    if len(surnames) == 0:
                        print("no surnames:", pname)
                    for surname in surnames:
                        old_prefix = surname.get_prefix()
                        suffix = name.get_suffix()
                        #print(is_primary,pname)
                        old_surname = surname.get_surname()

                        # update new values to database
                        # the model and view are updated thru 'person-update' signal in the method persin_update below   
                        def get_new_value(original, old_value, new_value, combobox):
                            if self.use_special.get_active():
                                new_value = None
                                action = combobox.get_active_id()
                                if action == 'clear':
                                    new_value = ""
                                elif action == 'from-prefix':
                                    new_value = old_prefix
                                elif action == 'from-surname':
                                    new_value = old_surname
                                elif action == 'from-firstname':
                                    new_value = firstname
                                elif action == 'from-suffix':
                                    new_value = suffix
                                elif action == 'from-title':
                                    new_value = title
                                elif action == 'append-prefix':
                                    new_value = original + " " + old_prefix
                                elif action == 'append-surname':
                                    new_value = original + " " + old_surname
                                elif action == 'append-firstname':
                                    new_value = original + " " + firstname
                                elif action == 'append-suffix':
                                    new_value = original + " " + suffix
                                elif action == 'append-title':
                                    new_value = original + " " + title
                                return new_value
                            else:
                                return self.do_replace(original, old_value, new_value )
                        
                        new_prefix = get_new_value(old_prefix, old_prefix_value, new_prefix_value, self.special_prefix)
                        if new_prefix is not None:
                            surname.set_prefix(new_prefix)
                            changed = True

                        new_surname =  get_new_value(old_surname, old_surname_value, new_surname_value, self.special_surname )
                        if new_surname is not None:
                            surname.set_surname(new_surname)
                            changed = True

                        new_firstname =  get_new_value(firstname, old_firstname_value, new_firstname_value, self.special_firstname )
                        if new_firstname is not None:
                            name.set_first_name(new_firstname)
                            changed = True

                        new_suffix =  get_new_value(suffix, old_suffix_value, new_suffix_value, self.special_suffix )
                        if new_suffix is not None:
                            name.set_suffix(new_suffix)
                            changed = True

                        new_title = get_new_value(title, old_title_value, new_title_value, self.special_title )
                        if new_title:
                            name.set_title(new_title)
                            changed = True

                        if new_nametype:
                            if (not old_nametype) or (orig_nametype == old_nametype):
                                nametype = NameType()
                                nametype.set(eval(new_nametype))
                                name.set_type(nametype)
                                changed = True

                        break
                    #self.namemodel.update_row_by_handle()
                    if changed:
                        self.db.commit_person(person, self.trans)
                    #self.db.commit_person(person, self.trans)
        
                
                except:
                    raise
        print("Num replacements:", self.num_replacements)

                
    def do_replace(self, original_value, old_text, new_text ):
        new_value = None
        if old_text:
            if self.use_regex:
                new_value = re.sub(old_text, new_text, original_value)
            else:
                new_value = original_value.replace(old_text,new_text)
        elif new_text:
            new_value = new_text
        return new_value


    def _connect_db_signals(self): # called from DbGUIElement
        self.callman.add_db_signal('person-update', self.person_update)

    def person_update(self, handle_list):
        for handle in set(handle_list):
            person = self.db.get_person_from_handle(handle)
            pname = name_displayer.display(person)
            for namerownum,modelrownum,nameindex in self.map[handle]:
                row = getrow(person, nameindex, namerownum)
                #print(namerownum,modelrownum,row)
                self.names[namerownum] = row
                self.namemodel[modelrownum][1] = gender_code_to_string(row.gender)
                self.namemodel[modelrownum][2] = row.names.prefix
                self.namemodel[modelrownum][3] = row.names.surname
                self.namemodel[modelrownum][4] = row.names.firstname
                self.namemodel[modelrownum][5] = row.names.suffix
                self.namemodel[modelrownum][6] = row.names.title
                self.namemodel[modelrownum][7] = str(row.nametype)
                self.num_replacements += 1

#------------------------------------------------------------------------
#
# Options
#
#------------------------------------------------------------------------
class Options(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

