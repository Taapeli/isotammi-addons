#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2022      KKu
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

import json
import os
import re
import sys
import traceback

import urllib.request

from collections import defaultdict
from contextlib import contextmanager
from pprint import pprint

try:
    from typing import List, Tuple, Optional, Iterator, Generator, Any, Callable, Dict
except:
    pass
 
from gi.repository import Gtk, Gdk, GObject

from gramps.gen.lib import Person
from gramps.gen.utils.callman import CallbackManager

from gramps.gui.dialog import OkDialog
from gramps.gui.plug import tool

from gramps.gen.db import DbTxn
from gramps.gui.utils import ProgressMeter

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def read_ay_cache():
    global cachefile, ay_cache
    cachefile = __file__ + ".aycache.json"
#   print(cachefile)
    if os.path.exists(cachefile):
        ay_cache = json.loads(open(cachefile).read())
    else:
        ay_cache = {}

def save_cache():
    # type: () -> None
    with open(cachefile,"w") as f:
        print(json.dumps(ay_cache, indent=4), file=f)

def convert_narc_urls(text):
    # type: (str) -> Tuple[str, int, int, int]
    notetext = text
    numchanges = 0
    numfails = 0
    numdiffs = 0
    i = 0
    while True:
        i = notetext.find("http://digi.narc.fi/digi", i)
        if i < 0: break
        url = notetext[i:].split()[0]
        i += len(url)
        j = url.find("?kuid=") 
        if j < 0:
            continue
        if j > 0:
            #print("url",url)
            kuids = url.split("=")
            #print("kuid",kuid)
            kuid = kuids[1]
            url1 = "http://digi.narc.fi/digi/view.ka?kuid="+kuid
            astia_url, dh_url, astia_url2 = narc_url_to_astia_url(url)
            #print("url:",url,kuid,astia_url)
            if astia_url:
                notetext2 = notetext.replace(url,astia_url)
                assert notetext2 != notetext
                if notetext2 == notetext:
                    raise nochange
                notetext = notetext2
                numchanges += 1
            else:
                numfails += 1
    return notetext, numchanges, numfails, numdiffs
    
def narc_url_to_astia_url(url):
    # type: (str) -> Tuple[Optional[str], str, str]
    kuid = url.split("=")[1]
    try:
        #return kuid_to_astia_url(kuid)
        astia_url = kuid_to_astia_url(kuid)
        #astia_url = None
        dh_url = ""
        astia_url2 = astia_url
        return astia_url, dh_url, astia_url2
    except:
        traceback.print_exc()
        raise
        #return None


def kuid_to_astia_url(kuid):
    # type: (str) -> Optional[str]
    
    # from http://digi.narc.fi/digi/js/siirto.js:
    # http://digi.narc.fi/fetchJaksoAndTunniste.php?kuid=8770676
    #  => {"ayid":"124923","at3_ay_tunnus":"2620868.KA","jakso":"258"}
    global ay_cache
    
    url = "http://digi.narc.fi/fetchJaksoAndTunniste.php?kuid=" + kuid
    s = urllib.request.urlopen(url).read()
    rsp = json.loads(s)
    ay = rsp['at3_ay_tunnus']
    jakso = rsp['jakso']
    if ay is None:
        return None

    if ay not in ay_cache:
        # var tiedot = {searchString:"AY_" + json.at3_ay_tunnus, searchTarget:"aineisto"};
        tiedot = {"searchString":"AY_" + ay, "searchTarget":"aineisto"};

        # var aineisto = await $.post("https://astia.narc.fi/uusiastia/aineisto/read.php", JSON.stringify(tiedot), function(data) {
        url = "https://astia.narc.fi/uusiastia/aineisto/read.php"
        s = urllib.request.urlopen(url, data=json.dumps(tiedot).encode("utf-8")).read()
        rsp = None
        try:
            rsp = json.loads(s)
            aineistoId = rsp['tulokset'][0]['id']
        except:
            return None

        #  var tiedostot = await $.post("https://astia.narc.fi/uusiastia/json/json_tiedostot.php?id=" + id, function(data) {
        url = "https://astia.narc.fi/uusiastia/json/json_tiedostot.php?id=" + aineistoId
        s = urllib.request.urlopen(url, data=b'').read()
        try:
            rsp = json.loads(s)
            #print(rsp)
        except:
            return None
        tiedostot = rsp['fullres']
        file_cache = {}
        if tiedostot is None:
            tiedostot = []
        for tiedosto in tiedostot:
            children = tiedosto['children']
            title = children[1]['tagData']  # "Tiedosto <jakso>"
            fileId = children[0]['tagData']
            file_cache[title] = fileId
        ay_cache[ay] = (aineistoId,file_cache)
        save_cache()
    else:
        aineistoId, file_cache = ay_cache[ay]
    fileId = file_cache.get(f"Tiedosto {jakso}")
    if fileId:
        astia_url = f"https://astia.narc.fi/uusiastia/viewer/?fileId={fileId}&aineistoId={aineistoId}"
        return astia_url
    return None



#-------------------------------------------------------------------------
#
# Tool
#
#-------------------------------------------------------------------------
class Tool(tool.Tool):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        # type: (Any, Any, Any, str, Callable) -> None
        self.user = user
        self.uistate = user.uistate
        self.dbstate = dbstate
        self.db = dbstate.db
        tool.Tool.__init__(self, dbstate, options_class, name)
        with DbTxn(_("Converting NARC URLs"), self.dbstate.db) as trans:
            self.run(trans)


    def run(self, trans):
        # type: (DbTxn) -> None
        read_ay_cache()
        
        n = 0
        personcount = 0
        personfails = 0
        totalcount = self.db.get_number_of_people()
        with self.progress(
                _("Converting URLs for people ..."), '',
                totalcount
        )  as step: # type: Callable
            for person in self.db.iter_people():
                if step(): break
                n1 = 0
                for url_obj in person.get_url_list():
                    url = url_obj.get_path() 
                    newurl, numchanges, numfails, numdiffs = convert_narc_urls(url)
                    if newurl != url:
                        url_obj.set_path(newurl)
                        self.db.commit_person(person, trans)
                        n += 1
                        n1 += 1
                    if numfails:
                        print(f"{person.gramps_id}: failed")
                if n1 > 0: 
                    personcount += 1
            print(f"persons: updated {n} urls for {personcount} persons")

        totalcount = self.db.get_number_of_notes()
        with self.progress(
                _("Converting URLs in notes ..."), '',
                totalcount
        ) as step:
            notecount = 0
            notefails = 0
            n2 = 0
            for i, note in enumerate(self.db.iter_notes()):
                if step(): break
                text = note.get()
                newtext, numchanges, numfails, numdiffs = convert_narc_urls(text)
                if newtext != text:
                    note.set(newtext)
                    self.db.commit_note(note, trans)
                    notecount += 1
                    n2 += numchanges
                if numfails:
                    print(f"{note.gramps_id}: failed")
                notefails += numfails
                if numdiffs:
                    print("Diffs for ", note.gramps_id)
            print(f"notes: updated {n2} urls in {notecount} notes")
        
        save_cache()
        OkDialog(
            _("Convert NARC URLs"),
            f"Updated {n} urls for {personcount} persons\n" + 
            f"Updated {n2} urls in {notecount} notes\n" +
            f"Failed to update {notefails} urls",
            parent=self.uistate.window,
        )

    @contextmanager
    def progress(self, title1, title2, count):
        # type: (str,str,int) -> Iterator[Callable]
        self._progress = ProgressMeter(title1, can_cancel=True)
        self._progress.set_pass(title2, count, ProgressMeter.MODE_FRACTION)
        try:
            yield self._progress.step
        finally:
            self._progress.close()

#------------------------------------------------------------------------
#
# Options
#
#------------------------------------------------------------------------
class Options(tool.ToolOptions):
    pass
