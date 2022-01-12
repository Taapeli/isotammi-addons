#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021 Gramps developers, Kari Kujansuu
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

import os
import shutil
from _io import BytesIO
import tarfile
import time
from xml.sax.saxutils import escape
try:
    import gzip
    _gzip_ok = 1
except:
    _gzip_ok = 0

from gi.repository import Gtk, Gdk, GObject
#import gtk

from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter, open_file_with_default_application
from gramps.gui.dialog import OkDialog
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.listmodel import ListModel
from gramps.gui.editors import EditPerson
from gramps.gui.glade import Glade

from gramps.gen.db import DbTxn
from gramps.gen.lib import Person, Family, Event, Place, Citation, Source, Repository, Note, Media
from gramps.gen.display.name import displayer as name_displayer
from gramps.gui.plug.export import WriterOptionBox, WriterOptionBoxWithCompression
from gramps.plugins.export.exportxml import GrampsXmlWriter
from gramps.plugins.export.exportpkg import PackageWriter, fix_mtime
from gramps.version import VERSION
from gramps.gen.db.exceptions import DbWriteFailure
from gramps.gen.constfunc import win
from gramps.gen.utils.file import media_path_full

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

from gramps.gen.config import config as configman
config = configman.register_manager("isotammiexport")
config.register("defaults.include_media", False)
config.register("defaults.material_type", "Family Tree")
config.register("defaults.description", "")

import logging
log = logging.getLogger(".isotammiexportxml")

#-------------------------------------------------------------------------
#
# export_data
#
#-------------------------------------------------------------------------
def export_data(database, filename, user, option_box=None):
    """
    Call the XML writer with the syntax expected by the export plugin.
    """
    if os.path.isfile(filename):
        try:
            shutil.copyfile(filename, filename + ".bak")
            shutil.copystat(filename, filename + ".bak")
        except:
            pass

    compress = _gzip_ok == 1
    include_media = False
    material_type = "family tree"
    if option_box:
        option_box.parse_options()
        database = option_box.get_filtered_database(database)
        include_media = option_box.get_include_media()
        compress = compress and option_box.get_use_compression()
        material_type = option_box.get_material_type()
        description = option_box.get_description()

        config.set("defaults.include_media", include_media)
        config.set("defaults.material_type", material_type)
        config.set("defaults.description", description)
        config.save()
    g = XmlWriter(database, user, 0, compress, material_type, description)
    return g.writepkg(filename, include_media)

#-------------------------------------------------------------------------
#
# XmlWriter
#
#-------------------------------------------------------------------------
class XmlWriter(GrampsXmlWriter):
    """
    Writes a database to the XML file.
    """

    def __init__(self, dbase, user, strip_photos, compress=1, material_type=None, description=None):
        GrampsXmlWriter.__init__(
            self, dbase, strip_photos, compress, VERSION, user)
        self.user = user
        self.material_type = material_type
        self.description = description
        
    def writepkg(self, pkg_filename, include_media):
        "Code copied from gramps/plugins/export/exportpkg.py"
        try:
            archive = tarfile.open(pkg_filename,'w:gz')
        except EnvironmentError as msg:
            log.warning(str(msg))
            self.user.notify_error(_('Failure writing %s') % pkg_filename, str(msg))
            return 0

        # Write media files first, since the database may be modified
        # during the process (i.e. when removing object)
        if include_media:
            for m_id in self.db.get_media_handles(sort_handles=True):
                mobject = self.db.get_media_from_handle(m_id)
                filename = media_path_full(self.db, mobject.get_path())
                archname = str(mobject.get_path())
                if os.path.isfile(filename) and os.access(filename, os.R_OK):
                    archive.add(filename, archname, filter=fix_mtime)

        # Write XML now
        g = BytesIO()
        gfile = XmlWriter(self.db, self.user, 2, compress=1, 
                        material_type=self.material_type, description=self.description)
        gfile.write_handle(g)
        tarinfo = tarfile.TarInfo('data.gramps')
        tarinfo.size = len(g.getvalue())
        tarinfo.mtime = time.time()
        if not win():
            tarinfo.uid = os.getuid()
            tarinfo.gid = os.getgid()
        g.seek(0)
        archive.addfile(tarinfo, g)
        archive.close()
        g.close()
        return True
        
    def write(self, filename):
        """
        Write the database to the specified file.
        """
        ret = 0 #False
        try:
            ret = GrampsXmlWriter.write(self, filename)
        except DbWriteFailure as msg:
            (m1, m2) = msg.messages()
            self.user.notify_error("%s\n%s" % (m1, m2))
        return ret

    def write_metadata(self):
        """ Method to write out metadata of the database
        """
        GrampsXmlWriter.write_metadata(self)
        self.g.write("    <isotammi>\n")
        #print(self.db)
        #self.write_line("familytree", self.db.get_dbname(), 3)
        #self.write_line("database-engine", "Neo4j", 3)
        # researcher data is not exported: https://gramps-project.org/bugs/view.php?id=9903
        self.g.write("      <researcher-info>\n")
        for itemname in configman.get_section_settings("researcher"):
            x = configman.get("researcher."+itemname)
            print(itemname,"=",x)
            self.write_line(itemname, escape(x), 4)
        self.g.write("      </researcher-info>\n")
        print(self.material_type)
        self.write_line("material_type", self.material_type, 3)
        self.g.write("      <user_description>\n")
        self.g.write(escape(self.description)+"\n")
        self.g.write("      </user_description>\n")
        self.g.write("    </isotammi>\n")


class IsotammiOptionBox(WriterOptionBoxWithCompression):
    """
    Extends the WriterOptionBox with option for using compression.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_compression = _gzip_ok
        self.use_compression_check = None

    def get_use_compression(self):
        return self.use_compression

    def get_option_box(self):
        config.load()
        include_media = config.get("defaults.include_media")
        material_type = config.get("defaults.material_type")
        description = config.get("defaults.description")
        
        option_box = super().get_option_box()
        label_include_media = Gtk.Label(_("Include media"))
        self.include_media = Gtk.CheckButton()
        self.include_media.set_active(include_media)
        
        label = Gtk.Label(_("Material type"))
        self.material_familytree = Gtk.RadioButton.new_with_label_from_widget(None, _("Family tree"))
        self.material_placedata = Gtk.RadioButton.new_with_label_from_widget(self.material_familytree, _("Place Data"))
        self.material_hiskitree = Gtk.RadioButton.new_with_label_from_widget(self.material_familytree, _("Hiski Tree"))
        description_label = Gtk.Label(_("Description:"))
        if material_type == "Family Tree":
            self.material_familytree.set_active(True)
        if material_type == "Place Data":
            self.material_placedata.set_active(True)
        if material_type == "Hiski Tree":
            self.material_hiskitree.set_active(True)
            
        self.win = Gtk.ScrolledWindow()
        self.win.set_size_request(400, 100)
        self.description = Gtk.TextView()
        buf = self.description.get_buffer()
        buf.set_text(description)

        
        grid = Gtk.Grid()
        grid.attach(label,0,0,1,1)
        grid.attach(self.material_familytree,0,1,1,1)
        grid.attach(self.material_placedata,0,2,1,1)
        grid.attach(self.material_hiskitree,0,3,1,1)

        box = Gtk.HBox()
        box1 = Gtk.VBox()
        box2 = Gtk.VBox()
        box1a = Gtk.HBox()

        box1a.pack_start(self.include_media, False, True, 0)
        box1a.pack_start(label_include_media, False, True, 5)

        box1.pack_start(box1a, False, True, 10)
        box1.pack_start(grid, False, True, 10)

        description_label.set_halign(Gtk.Align.START)
        self.win.add(self.description) #, False, True, 10)
        box2.pack_start(description_label, False, True, 0)
        box2.pack_start(self.win, False, True, 0)

        box.pack_start(box1, False, True, 10)
        box.pack_start(box2, False, True, 10)

        option_box.pack_start(box, False, True, 10)
        return option_box

    def get_include_media(self):
        return self.include_media.get_active()

    def get_material_type(self):
        if self.material_familytree.get_active(): return "Family Tree"
        if self.material_placedata.get_active(): return "Place Data"
        if self.material_hiskitree.get_active(): return "Hiski Tree"

    def get_description(self):
        buf = self.description.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

    def parse_options(self):
        super().parse_options()
        if self.use_compression_check:
            self.use_compression = self.use_compression_check.get_active()

