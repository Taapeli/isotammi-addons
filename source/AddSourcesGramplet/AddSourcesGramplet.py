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
# AddSourcesGramplet
# ------------------
# Author: kari.kujansuu@gmail.com
# 2 Mar 2020
#
 
import json
import pprint
import re
import traceback

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Event, Note

from gramps.gui.dialog import OkDialog

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class AddSourcesGramplet(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Lisää sama lähdeviitelisätieto moneen tapahtumaan kerrallaan"))

    def db_changed(self):
        self.__clear(None)
        
        
    def __typenames(self):
        for pt in self.dbstate.db.get_place_types():
            yield pt
        place_type_instance = PlaceType()
        for pt in place_type_instance.get_standard_names():
            yield pt

    def __tagnames(self):
        for handle in self.dbstate.db.get_tag_handles(sort_handles=True):
            tag = self.dbstate.db.get_tag_from_handle(handle)
            yield tag.get_name()
                    

    def __clear(self, obj):
        return
        self.selected_handle = None        
        selected_parent = None
        self.selected_name = ""
        self.enclosing_place.set_text(_("None"))
        self.tagcombo.get_child().set_text("")
        self.typecombo.get_child().set_text("")
        self.clear_enclosing.set_active(False)
        self.clear_tags.set_active(False)
        self.generate_hierarchy.set_active(False)
        self.spaces.set_active(False)
        self.reverse.set_active(False)
        self.replace_text.set_active(False)
    
    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(
            _("Lisää sama lähdeviitelisätieto moneen tapahtumaan kerrallaan.\n" +
            _("Lopuksi aja 'generatecitations'-työkalu (Muodosta lähdeviitteet lisätietojen perusteella).")
        ))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        label1 = Gtk.Label(_("Lähdeviite:"))
        vbox.pack_start(label1, False, True, 0)
        self.note = Gtk.Entry()
        vbox.pack_start(self.note, False, True, 0)
        
        but_apply = Gtk.Button(label=_('Lisää valittuihin tapahtumiin'))
        but_apply.connect("clicked", self.__apply)
        vbox.pack_start(but_apply, False, True, 0)

        vbox.show_all()
        return vbox

    def __apply(self,obj):
        with DbTxn(_("Processing events"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_events = len(selected_handles)
            for handle in selected_handles:
                event = self.dbstate.db.get_event_from_handle(handle)
                text = self.note.get_text()
                note = Note()
                note.set(text)
                notehandle = self.dbstate.db.add_note(note, self.trans)
                event.add_note(notehandle)
                self.dbstate.db.commit_event(event,self.trans)
    

