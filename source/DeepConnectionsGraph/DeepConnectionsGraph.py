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
# Author: kari.kujansuu@gmail.com
#
 
import sys
import json
import re
import time
import traceback
from threading import Thread
import urllib
import os
import importlib
import random
import queue

from pprint import pprint

from gi.repository import Gtk

from gramps.gen.plug import Gramplet
from gramps.gui.display import display_url

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

from http.server import BaseHTTPRequestHandler, HTTPServer
class Request:
    pass

request = Request()

basedir = os.path.split(__file__)[0]
sys.path.append(basedir)
os.chdir(basedir)

import routes
import connections

def get_func(path, server):
    if server.gramplet.development_mode.get_active():
        saved_path = sys.path[:]
        importlib.reload(connections)
        importlib.reload(routes)
        sys.path = saved_path
    routes.dbdata = server.dbdata
    routes.request = request
    routes.basedir = basedir
    routes.server = server
    return routes.map[path]

class WebServer(Thread):
    def __init__(self, gramplet, port=8888):
        Thread.__init__(self)
        self.gramplet = gramplet
        self.port = port
        self.running = False
        self.dbdata = connections.load_dbdata(gramplet.dbstate)
        self.refresh_needed = False

    def run(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
                
            def send(self, data, content_type="text/html"):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', content_type )
                self.end_headers()
                self.wfile.write(data)
            
            def do_GET(self):
                #print(self.path)
                if self.path == "/favicon.ico": return
                if self.path == "/": self.path = "/static/index.html"
                if self.path.startswith("/static/"):
                    fname = os.path.join(basedir,self.path[1:])
                    data = open(fname,"rb").read()
                    #print("data:"+data.decode("utf-8"))
                    self.send(data)
                    return
                i = self.path.find("?")
                #request = Request()
                if i > 0:
                    request.path = self.path[:i]
                    request.qs = self.path[i+1:]
                    request.args = urllib.parse.parse_qs(request.qs)
                else:
                    request.path = self.path
                    request.qs = None
                    request.args = None

                f = get_func(request.path, server)
                if f: 
                    rsp = ["?"]
                    exec("rsp[0] = f()",locals())
                    r = rsp[0]
                    if type(r) == str:
                        self.send(r.encode("utf-8"), content_type='application/json')
                    elif r.status != 200:
                        self.send_response(404)
                        self.end_headers()
                    else:
                        self.send(r.data, r.content_type)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write("Not found".encode("utf-8"))

        server_address = ('127.0.0.1', self.port)
        self.httpd = HTTPServer(server_address, Handler)
        server.gramplet.append_text("running at port {}\n".format(self.port))
        self.running = True
        self.httpd.serve_forever()
        server.gramplet.append_text("server stopped\n")

class NumberEntry(Gtk.Entry):
    def __init__(self):
        Gtk.Entry.__init__(self)
        self.connect('changed', self.on_changed)

    def on_changed(self, *args):
        text = self.get_text().strip()
        self.set_text(''.join([i for i in text if i in '0123456789']))        
        
class DeepConnectionsGraph(Gramplet):
    def init(self):
        self.root = self.__create_gui()
        self.selected_handle = None
        self.set_tooltip(_("Deep Connections Graph"))
        self.server = None
        self.running = True

    def db_changed(self):
        self.__clear(None)
        print("db changed: ",self.dbstate.db)
        if self.server:
            self.server.dbdata = connections.load_dbdata(self.dbstate)

        """Connect the signals that trigger an update."""
        self.connect(self.dbstate.db, 'person-update', self.updated)
        self.connect(self.dbstate.db, 'person-add', self.updated)
        self.connect(self.dbstate.db, 'person-delete', self.updated)
        self.connect(self.dbstate.db, 'person-rebuild', self.updated)
        self.connect(self.dbstate.db, 'family-rebuild', self.updated)
        self.connect(self.dbstate.db, 'family-add', self.updated)
        self.connect(self.dbstate.db, 'family-delete', self.updated)
        self.connect(self.dbstate.db, 'family-update', self.updated)
        self.connect(self.dbstate.db, 'event-rebuild', self.updated)
        self.connect(self.dbstate.db, 'event-add', self.updated)
        self.connect(self.dbstate.db, 'event-delete', self.updated)
        self.connect(self.dbstate.db, 'event-update', self.updated)
        
    def updated(self, *args):
        if self.server:
            self.server.refresh_needed = True
            self.server.dbdata = connections.load_dbdata(self.dbstate)

    def __clear(self, obj):
        pass
        
    def __create_gui(self):
        self.gui.get_container_widget().remove(self.gui.textview)
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        grid  = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(1)

        label = Gtk.Label(_("Port:"))
        self.entry_port = NumberEntry()
        self.entry_port.set_text("8888")
        self.random_port = Gtk.CheckButton("Random port")
        self.random_port.connect("clicked", self.cb_random)
        self.start_browser = Gtk.CheckButton("Start browser")
        self.development_mode = Gtk.CheckButton("Development mode")
        #self.development_mode.set_active(True)
        grid.attach( label, 0, 0, 1, 1 )
        grid.attach( self.entry_port, 1, 0, 1, 1 )
        #grid.attach( self.random_port, 2, 0, 1, 1 )
        #grid.attach( self.start_browser, 3, 0, 1, 1 )
        #grid.attach( self.development_mode, 2, 1, 1, 1 )

        butbox = Gtk.ButtonBox()
        self.but_start = Gtk.Button(label=_('Start server'))
        self.but_start.connect("clicked", self.cb_start)
        #butbox.pack_start(self.but_start, False, True, 0)
        grid.attach( self.but_start, 1, 1, 1, 1 )
        
        self.but_stop = Gtk.Button(label=_('Stop server'))
        self.but_stop.connect("clicked", self.cb_stop)
        #butbox.pack_start(self.but_stop, False, True, 0)
        self.but_stop.set_sensitive(False)
        grid.attach( self.but_stop, 2, 1, 1, 1 )

        butbox2 = Gtk.ButtonBox()
        self.but_refresh = Gtk.Button(label=_('Refresh tree'))
        self.but_refresh.connect("clicked", self.cb_refresh)
        #butbox2.pack_start(self.but_refresh, False, True, 0)
        self.but_refresh.set_sensitive(False)
        grid.attach( self.but_refresh, 1, 2, 1, 1 )

        self.start_browser = Gtk.Button(label=_('Start browser'))
        self.start_browser.connect("clicked", self.cb_start_browser)
        self.start_browser.set_sensitive(False)
        #butbox2.pack_start(self.start_browser, False, True, 0)
        grid.attach( self.start_browser, 2, 2, 1, 1 )

        vbox.pack_start(grid, False, True, 0)
        #vbox.pack_start(butbox, False, True, 0)
        #vbox.pack_start(butbox2, False, True, 0)

        vbox.pack_start(self.gui.textview, '', '', True)
        self.gui.get_container_widget().add_with_viewport(vbox)

        vbox.show_all()
        return vbox
        
    def cb_random(self,obj):
        checked = self.random_port.get_active()
        self.entry_port.set_sensitive(not checked)
        
    def cb_start(self,obj):
        if self.server:
            self.append_text("Already running\n")
            return
        
        if self.random_port.get_active():
            port = random.randint(10000,20000)
        else:
            port = int(self.entry_port.get_text())
        self.port = port
        self.append_text("starting server at port {}\n".format(port))
        importlib.reload(connections)
        importlib.reload(routes)
        self.server = WebServer(gramplet=self, port=port)
        self.server.start()
        #self.server.run()
        time.sleep(1)
        if not self.server.running:
            self.append_text("server failed\n")
            self.server = None
        else:
            print("server started")
            self.but_start.set_sensitive(False)
            self.but_stop.set_sensitive(True)
            self.but_refresh.set_sensitive(True)
            self.start_browser.set_sensitive(True)
            self.running = True

    def cb_stop(self,obj):
        if not self.server:
            self.append_text("Not running\n")
            return
        print("stopping server")
        self.append_text("stopping server\n")
        self.server.running = False
        self.server.httpd.shutdown()
        self.server.httpd.server_close()
        self.server = None
        self.but_start.set_sensitive(True)
        self.but_stop.set_sensitive(False)
        self.but_refresh.set_sensitive(False)
        self.start_browser.set_sensitive(False)
        self.running = False
        
    def cb_refresh(self,obj):
        if self.server:
            self.server.dbdata = connections.load_dbdata(self.dbstate)
            self.server.refresh_needed = False
            self.append_text("loaded new dbdata\n")

    def cb_start_browser(self,obj):
        display_url("http://localhost:{}".format(self.port))

    def on_save(self):
        self.cb_stop(None)
        self.running = False
        

