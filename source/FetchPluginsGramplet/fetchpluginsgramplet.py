# encoding: utf-8
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009 Doug Blank <doug.blank@gmail.com>
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

# $Id$

"""
This gramplet fetches plugins from Github
Author: kari.kujansuu@gmail.com, 2019


"""

#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
from collections import defaultdict
import json
import os
from pprint import pprint
import shutil
import time
import urllib

from gi.repository import Gtk

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.version import VERSION_TUPLE

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.const import USER_PLUGINS
from gramps.gen.plug import Gramplet

from gramps.gui.dialog import OkDialog
from gramps.gui.display import display_url
from gramps.gui.glade import Glade

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
sgettext = _trans.sgettext

DEBUG = False

github_user = "Taapeli"
github_repo = "stk-addons"
stk_plugin_dir = USER_PLUGINS + "/isotammi-addons"

version_dir = "gramps%s%s" % (VERSION_TUPLE[0],VERSION_TUPLE[1])
base_url = "https://api.github.com/repos/kkujansuu/gramps/contents/addons/"
base_url = "https://api.github.com/repos/{github_user}/{github_repo}/contents/GrampsUtils/{version_dir}/plugins/".format(
    version_dir=version_dir,
    github_user=github_user,
    github_repo=github_repo)
help_base_url = "https://github.com/{github_user}/{github_repo}/tree/master/GrampsUtils/{version_dir}/plugins/".format(
    version_dir=version_dir,
    github_user=github_user,
    github_repo=github_repo)

#------------------------------------------------------------------------
#
# Config
#
#------------------------------------------------------------------------
class Config:
    def __init__(self):
        modname = os.path.abspath(__file__)
        dirname = os.path.dirname(modname)
        self.config_fname = os.path.join(dirname,__name__+".ini")
        print("config_fname:",self.config_fname)
        try:
            self.config = json.loads(open(self.config_fname).read())
        except:
            self.config = {}
    def get(self,key):
        return self.config.get(self.dbid+":"+key)
    def set(self,key,value):
        self.config[self.dbid+":"+key] = value
        self.save()
    def setdbid(self,dbid):
        self.dbid = dbid
    def save(self):
        open(self.config_fname,"w").write(json.dumps(self.config))

config = Config()

#------------------------------------------------------------------------
#
# The Gramplet
#
#------------------------------------------------------------------------
class FetchPluginsGramplet(Gramplet):
    """
    """
    def __init__(self, *args):
        print("base_url:",base_url)
        Gramplet.__init__(self, *args)

    def init(self):
        g = Glade()
        top = g.get_object('top')
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(top)
        self.person1_label = g.get_object('person1_label')
        self.person2_label = g.get_object('person2_label')

        """
        button_start = g.get_object('button_start')
        button_pause = g.get_object('button_pause')
        button_continue = g.get_object('button_continue')
        button_swap = g.get_object('button_swap')
        button_copy = g.get_object('button_copy')


        
        button_start.connect("clicked", self.cb_search)
        button_start.set_sensitive(False)

        button_pause.connect("clicked", self.interrupt)
        button_pause.set_sensitive(False)

        button_continue.connect("clicked", self.resume)
        button_continue.set_sensitive(False)

        button_swap.connect("clicked", self.cb_swap)
        button_swap.set_sensitive(False)

        button_copy.connect("clicked", lambda widget: \
              self.gui.pane.pageview.copy_to_clipboard('Person', self.selected_handles))
        button_copy.set_sensitive(False)

        self.buttons1 = [
            button_start,
            button_swap,
        ]
        self.buttons2 = [
            button_pause,
            button_continue,
            button_copy,
        ]

        button_person2.connect("clicked", self.cb_select2)
        button_person1.connect("clicked", self.cb_select1)
        """
        button_fetch_plugin_list = g.get_object('button_fetch_plugin_list')
        button_fetch_plugin_list.connect("clicked", self.cb_fetch_plugin_list)
        self.status_msg = g.get_object('status_msg')
        
        top.show_all()
        self.top = top
        self.g = g
        self.cb_fetch_plugin_list(None)

    def db_changed(self):
        print("db_changed",self.dbstate.db.get_dbid(),self.dbstate.db.get_dbname())
        self.reset()
        

    def reset(self):
        self.person1  = None

    def cb_fetch_plugin_list(self, obj):
        self.status_msg.set_text("")
        try:
            self.plugin_list = self.__fetch_plugin_list()
        except urllib.error.URLError as e:
            self.status_msg.set_text(_("Unable to retrieve plugin list: ") + e.reason)
            self.plugin_list = []
        self.refresh_list()

    def refresh_list(self):
        grid = self.g.get_object('grid1')
        row = 3
        for plugin_name in self.plugin_list:
            grid.remove_row(3)
        for plugin_name in self.plugin_list:
            is_installed = self.is_installed(plugin_name)
            #print(plugin_name,is_installed)
            label1 = Gtk.Label(plugin_name)
            grid.attach(label1, 0, row, 1, 1)
            label1.show()

            if is_installed:
                label2 = Gtk.Label(sgettext("fetchplugins|installed"))
                grid.attach(label2, 1, row, 1, 1)
                label2.show()
                button_label = sgettext("fetchplugins|Remove")
                button_install_or_remove = Gtk.Button(button_label)
                button_install_or_remove.connect("clicked", lambda obj, plugin_name=plugin_name: self.__remove_plugin(plugin_name))
            else:
                button_label = sgettext("fetchplugins|Install")
                button_install_or_remove = Gtk.Button(button_label)
                button_install_or_remove.connect("clicked", lambda obj, plugin_name=plugin_name: self.__install_plugin(plugin_name))
            grid.attach(button_install_or_remove, 2, row, 1, 1)
            button_install_or_remove.show()

            help_url = help_base_url + plugin_name     
            button_help = Gtk.Button(sgettext("fetchplugins|Help"))
            button_help.connect("clicked", lambda obj, url=help_url: display_url(url))
            grid.attach(button_help, 3, row, 1, 1)
            button_help.show()

            row += 1
        grid.show()

        


    def main(self):
        """
        Main method.
        """
        print("main")

    def __fetch_url(self,url):
        rsp = urllib.request.urlopen(url)
        info = rsp.info()
        #print(rsp.getcode())
        #print(info)
        ratelimit_remaining = info.get('X-RateLimit-Remaining')
        if ratelimit_remaining:
            t = time.localtime(int(info['X-RateLimit-Reset']))
            label1 = self.g.get_object('label1')
            label1.set_text( _("%(numrequests)s requests remaining until %(time)s") % 
                dict(numrequests=ratelimit_remaining, 
                time=time.strftime("%H:%M:%S", t)) 
            )
        else:
            label1.set_text("")

        if rsp.getcode() != 200: return []
        
        s = rsp.read().decode("utf-8")        
        return json.loads(s)

    def __fetch_plugin_list(self):
        plugins = []
        filelist = self.__fetch_url(base_url)
        for f  in filelist:
            #print(f)
            plugins.append(f.get('name'))
        return plugins
            
    def is_installed(self, plugin_name):
        plugin_dir = os.path.join(stk_plugin_dir,plugin_name)
        return os.path.exists(plugin_dir)

    
    def __install_plugin(self, plugin_name):
        #print(plugin_name)

        def download_file(path,download_url):
            plugin_file = os.path.join(stk_plugin_dir,path)
            print("downloading",path,"to",plugin_file)
            filedata = urllib.request.urlopen(download_url).read() 
            open(plugin_file,"wb").write(filedata)
            
        def download(path):
            url = base_url + path
            plugin_dir = os.path.join(stk_plugin_dir,path)
            try:
                os.makedirs(plugin_dir)
            except FileExistsError:
                pass
            #print(url)
            s = urllib.request.urlopen(url).read().decode("utf-8")        
            filelist = json.loads(s)
            for f in filelist:
                #print(f)
                type = f.get("type")
                name = f.get("name")
                download_url = f.get("download_url")
                filepath = os.path.join(path,name)
                if type == "file":
                    download_file(filepath,download_url)
                if type == "dir":
                    download(filepath)
        
        download(plugin_name)
        self.refresh_list()

    def __remove_plugin(self, plugin_name):
        #print("Removing",plugin_name)
        plugin_dir = os.path.join(stk_plugin_dir,plugin_name)
        shutil.rmtree(plugin_dir)
        self.refresh_list()
        
