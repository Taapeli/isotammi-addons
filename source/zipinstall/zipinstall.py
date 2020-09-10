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
from zipfile import ZipFile, ZIP_DEFLATED
from gramps.gen.plug._pluginreg import PTYPE, PTYPE_STR, VIEW
from gramps.gen.plug._pluginreg import PluginRegister, make_environment
import uuid
import shutil
import traceback

"""
Import a plugin from a ZIP file
"""
import os

from gramps.gui.managedwindow import ManagedWindow
from gramps.gen.config import config

from gi.repository import Gtk, Gdk, GObject

from gramps.gui.plug import tool
from gramps.gui.dialog import OkDialog, ErrorDialog

from gramps.gen.const import USER_PLUGINS

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

#-------------------------------------------------------------------------
#
# Tool
#
#-------------------------------------------------------------------------
class Tool(tool.Tool):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        tool.Tool.__init__(self, dbstate, options_class, name)
        self.id_to_plugin = self.list_plugins() # dict id => plugin
        ZipInstallFileDialog(dbstate, user.uistate, self.id_to_plugin)
        
    def list_plugins(self):
        id_to_plugin = {}  
        preg = PluginRegister.get_instance()
        for ptype in PTYPE:      
            plugins = preg.type_plugins(ptype)
            for p in plugins:
                #print(p.id,p.name,p.description,p.fpath,p.fname)
                id_to_plugin[p.id] = p
        return id_to_plugin

# code adapted from gramps.gui.dbloader:

#-------------------------------------------------------------------------
#
# FileChooser filters: what to show in the file chooser
#
#-------------------------------------------------------------------------
def add_all_files_filter(chooser):
    """
    Add an all-permitting filter to the file chooser dialog.
    """
    mime_filter = Gtk.FileFilter()
    mime_filter.set_name(_('All files'))
    mime_filter.add_pattern('*')
    chooser.add_filter(mime_filter)

def add_zip_files_filter(chooser):
    """
    Add a zip file permitting filter to the file chooser dialog.
    """
    mime_filter = Gtk.FileFilter()
    mime_filter.set_name(_('ZIP files'))
    mime_filter.add_pattern('*.zip')
    chooser.add_filter(mime_filter)

#-------------------------------------------------------------------------
#
# ZipInstallFileDialog
#
#-------------------------------------------------------------------------
class ZipInstallFileDialog(ManagedWindow):


    def __init__(self, dbstate, uistate, plugins, callback=None):
        """
        A dialog to import a file into Gramps
        """
        self.dbstate = dbstate
        self.uistate = uistate
        self.plugins = plugins
        self.debug = True

        self.title = _("Plugin installation from a ZIP file")
        ManagedWindow.__init__(self, uistate, [], self.__class__, modal=True)
        # the choose_plugin_name_dialog.run() below makes it modal, so any change to
        # the previous line's "modal" would require that line to be changed

        import_dialog = Gtk.FileChooserDialog(
            title='', transient_for=self.uistate.window,
            action=Gtk.FileChooserAction.OPEN)
        import_dialog.add_buttons(_('_Cancel'), Gtk.ResponseType.CANCEL,
                                  _('Open'), Gtk.ResponseType.OK)
        self.set_window(import_dialog, None, self.title)
        self.setup_configs('interface.zipimportfiledialog', 780, 630)
        import_dialog.set_local_only(False)

        # Always add automatic (match all files) filter
        add_zip_files_filter(import_dialog)   # *.zip
        add_all_files_filter(import_dialog)   # *

        import_dialog.set_current_folder(config.get('paths.recent-import-dir'))
        while True:
            # the choose_plugin_name_dialog.run() makes it modal, so any change to that
            # line would require the ManagedWindow.__init__ to be changed also
            response = import_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                break
            elif response == Gtk.ResponseType.DELETE_EVENT:  # ???
                return
            elif response == Gtk.ResponseType.OK:
                filename = import_dialog.get_filename()
                #if self.check_errors(filename):
                #    # displays errors if any
                #    continue

                (the_path, the_file) = os.path.split(filename)
                basename, extension = os.path.splitext(the_file)
                
                config.set('paths.recent-import-dir', the_path)

                if extension != ".zip":
                    ErrorDialog(_("Error"),
                        _("Could not open file: %s") % the_file + ": " +
                        _('File type "%s" is not a ZIP file.\n\n') % extension,
                        parent=self.uistate.window)
                    continue

                #dirname = os.path.join(USER_PLUGINS, basename)
                #if os.path.exists(dirname):
                #    ErrorDialog(_("Error"),
                #        _("Plugin already exists: %s") % basename,
                #        parent=self.uistate.window)
                #    continue
                plugindata = self.get_plugin_data(filename)
                for plugin_id in plugindata:
                    plugin_info = plugindata[plugin_id]
                    plugin_name = plugin_info['name']
                    if plugin_id in self.plugins:
#                         print(plugin_id,"already exists")
                        p = self.plugins[plugin_id]
                        old_plugin = p
                        if self.debug:
                            ptypestr = PTYPE_STR[p.ptype]
                            print("  type:",ptypestr)
                            print("  name:",p.name)
                            print("  desc:",p.description)
                            print("  path:",p.fpath)
                            print("  file:",p.fname)
                            print("  version:",p.version)
                            print()
                            print("This plugin:")
                            print(plugin_info)
                    else:
                        old_plugin = None
                self.backup_zipfname = None
                self.gramps_view_installed = False
                dirname = self.install_plugin_dialog(filename, plugin_info, old_plugin)
                msg = _("Plugin '%s' installed in\n    %s") % (plugin_name,dirname) 
                if self.backup_zipfname:
                    msg += _("\nOld version saved in\n    %s") % self.backup_zipfname 
                if self.gramps_view_installed:
                    msg += _("\n\nRestart Gramps.") 
                if dirname:
                    OkDialog(_("Installed"),
                        msg,
                        parent=self.uistate.window)
                    break

        self.close()

    def overwrite_clicked(self, overwrite, ok_button, backup ):
        if overwrite.get_active():
            backup.set_active(True)
            backup.set_sensitive(True)
            ok_button.set_sensitive(True)
        else:
            backup.set_active(False)
            backup.set_sensitive(False)
            ok_button.set_sensitive(False)

    def install_plugin_dialog(self, filename, plugin_data, old_plugin):
        plugin_type = PTYPE_STR[plugin_data['type']]
        plugin_id = plugin_data['id']
        plugin_name = plugin_data['name']
        plugin_desc = plugin_data['description']
        plugin_version = plugin_data['version']

        dialog = Gtk.Dialog(title=_("Plugin installation"), parent=None,
                            flags=Gtk.DialogFlags.MODAL)

        hdr = Gtk.Label()
        hdr.set_markup("<b>" + _("Installing from %s") % os.path.basename(filename) + "</b>")
        dialog.vbox.pack_start(hdr, False, False, 5)

        ok_button = dialog.add_button(_("Install"), Gtk.ResponseType.OK)
        print(ok_button)
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.OK)

        lbl_id_title = Gtk.Label(_("Plugin id:"))
        lbl_id_title.set_halign(Gtk.Align.START)
        lbl_id = Gtk.Label(plugin_id)
        lbl_id.set_halign(Gtk.Align.START)

        lbl_type_title = Gtk.Label(_("Plugin type:"))
        lbl_type_title.set_halign(Gtk.Align.START)
        lbl_type = Gtk.Label(plugin_type)
        lbl_type.set_halign(Gtk.Align.START)
        
        lbl_name_title = Gtk.Label(_("Plugin name:"))
        lbl_name = Gtk.Label(plugin_name)
        lbl_name_title.set_halign(Gtk.Align.START)
        lbl_name.set_halign(Gtk.Align.START)
        
        lbl_desc_title = Gtk.Label(_("Description:"))
        lbl_desc = Gtk.Label(plugin_desc)
        lbl_desc_title.set_halign(Gtk.Align.START)
        lbl_desc.set_halign(Gtk.Align.START)
        
        lbl_version_title = Gtk.Label(_("Version:"))
        lbl_version = Gtk.Label(plugin_version)
        lbl_version_title.set_halign(Gtk.Align.START)
        lbl_version.set_halign(Gtk.Align.START)
        
        grid = Gtk.Grid()
        grid.attach(lbl_id_title, 0, 0, 1, 1)
        grid.attach(lbl_id, 1, 0, 1, 1)
        grid.attach(lbl_type_title, 0, 2, 1, 1)
        grid.attach(lbl_type, 1, 2, 1, 1)
        grid.attach(lbl_name_title, 0, 3, 1, 1)
        grid.attach(lbl_name, 1, 3, 1, 1)
        grid.attach(lbl_desc_title, 0, 4, 1, 1)
        grid.attach(lbl_desc, 1, 4, 1, 1)
        grid.attach(lbl_version_title, 0, 5, 1, 1)
        grid.attach(lbl_version, 1, 5, 1, 1)
        overwrite = Gtk.CheckButton(_("Overwrite"))
        backup = Gtk.CheckButton(_("Make backup"))
        if old_plugin:
            ok_button.set_sensitive(False)
            overwrite.connect('clicked', self.overwrite_clicked, ok_button, backup)
            backup.set_sensitive(False)
            
            grid2 = Gtk.Grid()
            lbl_exists = Gtk.Label(_("Plugin already exists (version %s)") % old_plugin.version)
            red = Gdk.color_parse("red")
            lbl_exists.modify_fg(Gtk.StateType.NORMAL, red)
            grid2.attach(lbl_exists, 1, 1, 1, 1)
            grid2.attach(overwrite, 1, 2, 1, 1)
            grid2.attach(backup, 1, 3, 1, 1)
            grid.attach(grid2, 1, 1, 1, 1)
        dialog.vbox.pack_start(grid, False, False, 5)
        dialog.show_all()
        result = dialog.run()
        dialog.destroy()
        if result != Gtk.ResponseType.OK:
            return None
        if plugin_data['type'] == VIEW:
            self.gramps_view_installed = True
        return self.do_install(filename, plugin_id, plugin_version, old_plugin, overwrite.get_active(), backup.get_active() )    

    def do_install(self, filename, plugin_id, plugin_version, old_plugin, overwrite, make_backup ):
        if old_plugin:
            if make_backup:
                self.backup_zipfname = self.do_backup(old_plugin)
            if overwrite:
                self.delete_plugin(old_plugin)
        dirname = self.generate_dirname(plugin_id, plugin_version)   
        zf = ZipFile(filename)
        zf.extractall(dirname)
        self.uistate.viewmanager.do_reg_plugins(self.dbstate, self.uistate, rescan=True)
        print("done")
        return dirname
    
    def do_backup(self, old_plugin):
        zipname = os.path.join(USER_PLUGINS, old_plugin.id)
        zipname += "_" + old_plugin.version
        if os.path.exists(zipname + ".zip"):
            zipname += "_" + uuid.uuid4().hex[0:6]
        zipfname = zipname + ".zip"
        zf = ZipFile(zipfname,"w", compression=ZIP_DEFLATED)
        if old_plugin.fpath == USER_PLUGINS:
            # just back up this file: 
            pyfile = os.path.join(old_plugin.fpath,old_plugin.fname)
            zf.write(pyfile, old_plugin.fname)
            return zipfname
        prefix_len = len(old_plugin.fpath)
        for dname,dirs,files in os.walk(old_plugin.fpath):
            for name in files:
                fname = os.path.join(dname,name)
                arcname = fname[prefix_len:]
                zf.write(fname, arcname)
            dirs[:] = [d for d in dirs if d != "__pycache__"]
        return zipfname

    def delete_plugin(self, old_plugin):
        pyfile = os.path.join(old_plugin.fpath,old_plugin.fname)
        try:
            os.remove(pyfile)
        except:
            traceback.print_exc()
        if old_plugin.fpath != USER_PLUGINS:
            try:
                print("rmtree:",old_plugin.fpath)
                shutil.rmtree(old_plugin.fpath)
            except:
                traceback.print_exc()
            # remove any empty directories above the plugin directory
            parent,dname = os.path.split(old_plugin.fpath)
            if parent != USER_PLUGINS: 
                print("removedirs:",parent)
                try:
                    os.removedirs(parent)
                except:
                    traceback.print_exc()
            return
            path = old_plugin.fpath
            while True:
                parent,dname = os.path.split(path)
                if parent == USER_PLUGINS: 
                    os.rmdir(dname)
                    break
                files = os.listdir(parent)
                print("listdir:",files)
                if len(files) > 1:
                    break
                os.rmdir(dname)
                path = parent   

    def generate_dirname(self, plugin_id, plugin_version):
        dirname = os.path.join(USER_PLUGINS, plugin_id)
        dirname += "_" + plugin_version
        if os.path.exists(dirname):
            dirname += "_" + uuid.uuid4().hex[0:6]
        return dirname
    
    def get_plugin_data(self, filename):
        zf = ZipFile(filename)
        for name in zf.namelist():
            print(name)
            if name.endswith(".gpr.py"):
                return self.process_gpr(zf, name)

    def process_gpr(self, zf, name):
        s = zf.read(name)
        plugindata = {}
        def register(plugintype,**info):
            print("reg",plugintype,info)
            id = info.get('id')
            info['type'] = plugintype
            plugindata[id] = info
        def gettext(x):
            return x
        globals = {}
        locals = make_environment()
        locals["register"] = register
        locals["_"] = _
        exec(s, globals, locals)
        return plugindata

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



