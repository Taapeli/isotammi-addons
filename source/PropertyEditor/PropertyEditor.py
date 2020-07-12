#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
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
#
# PlaceTool
# ---------
# Author: kari.kujansuu@gmail.com
# 9 Jun 2019
#
# Gramplet to change properties of multiple items at the same time. See README.
 
import json
import pprint
import re
import traceback 

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gen.db import DbTxn
from gramps.gen.lib import Person
from gramps.gen.lib import Family
from gramps.gen.lib import Event
from gramps.gen.lib import Place
from gramps.gen.lib import Source
from gramps.gen.lib import Citation
from gramps.gen.lib import Repository
from gramps.gen.lib import Media
from gramps.gen.lib import Note

from gramps.gui.dialog import OkDialog

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib.reporef import RepoRef
from gramps.gen.lib.styledtext import StyledText
from gramps.gui import display
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class PropertyEditor(Gramplet):

    def main(self):
        active_page = self.uistate.viewmanager.active_page
        viewname = active_page.__class__.__name__
        if viewname in {'PersonTreeView', 'PersonListView'}:
            self.cls = Person
        if viewname == 'FamilyView':
            self.cls = Family
        if viewname in {'PlaceTreeView', 'PlaceListView'}:
            self.cls = Place
        if viewname == 'EventView':
            self.cls = Event
        if viewname == 'SourceView':
            self.cls = Source
        if viewname == 'CitationListView':
            self.cls = Citation
        if viewname == 'RepositoryView':
            self.cls = Repository
        if viewname == 'MediaView':
            self.cls = Media
        if viewname == 'NoteView':
            self.cls = Note
        self.objname=self.cls.__name__.lower()
        self.getfunc = getattr(self.dbstate.db, "get_{objname}_from_handle".format(objname=self.objname) )
        self.commitfunc = getattr(self.dbstate.db, "commit_{objname}".format(objname=self.objname) )
        self.viewname = viewname
        self.schema = self.cls.get_schema()

        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        yield True

    def db_changed(self):
        self.__clear(None)
        
    def __tagnames(self):
        for handle in self.dbstate.db.get_tag_handles(sort_handles=True):
            tag = self.dbstate.db.get_tag_from_handle(handle)
            yield tag.get_name()
                    
    def __clear(self, obj):
        #self.replace_text.set_active(False)
        pass
    
    def get_propfuncs(self, objname, propname):
        if self.objname == "place":
            if propname == "long": propname = "longitude"
            if propname == "lat":  propname = "latitude"
        if self.objname == "source":
            if propname == "pubinfo": propname = "publication_info"
            if propname == "abbrev":  propname = "abbreviation"
        if self.objname == "citation":
            if propname == "source_handle": propname = "reference_handle"
        if self.objname == "media":
            if propname == "mime": propname = "mime_type"
            if propname == "desc": propname = "description"
        if self.objname == "note":
            getpropfunc = getattr(self.cls, "get" )
            setpropfunc = getattr(self.cls, "set" )
            return getpropfunc, setpropfunc

        getpropfuncname = "get_" + propname
        setpropfuncname = "set_" + propname 
        getpropfunc = getattr(self.cls, getpropfuncname )
        setpropfunc = getattr(self.cls, setpropfuncname )
        return getpropfunc, setpropfunc
    
    
    def _resolve_radio(self, master_radio):
        """
        from https://stackoverflow.com/questions/8812389/gtk-how-do-i-find-which-radio-button-is-selected
        """
        active = next((
            radio for radio in
            master_radio.get_group()
            if radio.get_active()
        ))
        return active
        
    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet allows editing attributes for multiple %s objects at the same time" % self.viewname))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        pt_grid = Gtk.Grid(column_spacing=10)

        propnames = []        
        for propname,propinfo in self.schema["properties"].items():
            print(propname,propinfo)
            if propname == "gramps_id": continue
            if propname.endswith("handle"): continue
            proptype = propinfo.get("type")
            proplabel = propinfo.get("title")
            if proptype is None: continue
            if proptype == "string": # or "string" in proptype:
                propnames.append((propname,proplabel))
                self.get_propfuncs(self.objname, propname)

        self.group = None
        for rownum,(propname,proplabel) in enumerate(sorted(propnames)):
            if proplabel is None: proplabel = propname
            r = Gtk.RadioButton.new_with_label_from_widget(self.group, proplabel)
            r.connect("toggled", self.__set_propname, propname)
            r.propname = propname
            if self.group is None: self.group = r
            pt_grid.attach(r,0,rownum,1,1)
        
        vbox.pack_start(pt_grid, False, True, 0)

        #self.replace_text = Gtk.CheckButton(_("Replace text string"))
        #self.replace_text.connect("clicked", self.__select_replace_text)

        self.use_regex = Gtk.CheckButton(_("Use regex"))
        self.use_regex.set_sensitive(True)

        replace_text_box = Gtk.HBox()
        replace_text_box.pack_start(self.use_regex, False, True, 0)
        vbox.pack_start(replace_text_box, False, True, 0)

        old_text_label = Gtk.Label()
        old_text_label.set_markup("<b>{}</b>".format(_("Old text:")))
        self.old_text = Gtk.Entry()
        self.old_text.set_sensitive(True)

        new_text_label = Gtk.Label()
        new_text_label.set_markup("<b>{}</b>".format(_("New text:")))
        self.new_text = Gtk.Entry()
        self.new_text.set_sensitive(True)

        replace_grid = Gtk.Grid(column_spacing=10)
        replace_grid.set_margin_left(20)
        replace_grid.attach(old_text_label,1,0,1,1)
        replace_grid.attach(self.old_text,2,0,1,1)
        replace_grid.attach(new_text_label,1,1,1,1)
        replace_grid.attach(self.new_text,2,1,1,1)
        vbox.pack_start(replace_grid, False, True, 0)
        
        but_clear = Gtk.Button(label=_('Clear'))
        but_clear.connect("clicked", self.__clear)
        vbox.pack_start(but_clear, False, True, 10)

        but_apply = Gtk.Button(label=_('Apply to selected objects'))
        but_apply.connect("clicked", self.__apply)
        vbox.pack_start(but_apply, False, True, 0)

        #but_help = Gtk.Button(label=_('_Help'))
        but_help = Gtk.Button.new_with_mnemonic(_("_Help"))
        but_help.connect("clicked", self.__help)
        vbox.pack_start(but_help, False, True, 0)

        vbox.show_all()
        return vbox
        
    def __help(self, obj ):    
        url = "http://wiki.isotammi.net/wiki/Gramps-laajennus:PropertyEditor"    
        display.display_url(url)

    def __set_propname(self, obj, propname ):        
        self.propname = propname

    def __fill_combo(self, combo, data_list, wrap_width=1):
        for data in sorted(data_list):
            if data:
                combo.append_text(data)

        combo.set_popup_fixed_width(False)
        combo.set_wrap_width(wrap_width)
        combo.set_entry_text_column(0)

    def __select_replace_text(self,obj):
        #checked = self.replace_text.get_active()
        #self.old_text.set_sensitive(checked)
        #self.new_text.set_sensitive(checked)
        #self.use_regex.set_sensitive(checked)
        pass

    def __apply(self,obj):
        if self.objname != "note":
            selected_prop = self._resolve_radio(self.group)
            propname = selected_prop.propname
            getpropfunc, setpropfunc = self.get_propfuncs(self.objname, propname)

            if getpropfunc is None: 
                OkDialog("failed","")
                return
        if self.objname == "note" and self.use_regex.get_active():
            getpropfunc, setpropfunc = self.get_propfuncs(self.objname, "text")
        with DbTxn(_("Setting properties"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_objects = len(selected_handles)
            for handle in selected_handles:
                obj = self.getfunc(handle)
                old_text = self.old_text.get_text()
                new_text = self.new_text.get_text()
                if self.objname == "note" and not self.use_regex.get_active():
                    next_text = obj.get_styledtext().replace(old_text, StyledText(new_text))
                    obj.set_styledtext(next_text)
                    self.commitfunc(obj,self.trans)
                    continue
                orig_text = getpropfunc(obj)
                if self.use_regex.get_active():
                    try:
                        next_text = re.sub(old_text,new_text,orig_text)
                    except Exception as e:
                        traceback.print_exc()
                        raise RuntimeError(_("Regex operation failed: {}").format(e))
                else:
                    next_text = orig_text.replace(old_text,new_text)
                setpropfunc(obj, next_text)
                self.commitfunc(obj,self.trans)
    

