#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
# Copyright (C) 2020-2022 Kari Kujansuu
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
# 2020 kari.kujansuu@gmail.com
#
# https://xlrd.readthedocs.io/en/latest/licenses.html

import codecs
import csv
from io import TextIOWrapper
import time

import logging
LOG = logging.getLogger(__name__)

from collections import defaultdict
import pprint
import re
import traceback

try:
    import xlrd     # Excel support
except:
    pass

try:
    from pyexcel_ods import get_data # ods (OpenOffice/Libreoffice) support
    import odf, defusedxml
except:
    pass

from gi.repository import Gtk

from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gui.dialog import OkDialog
from gramps.gen.db import DbTxn

from gramps.gen.lib import Event
from gramps.gen.lib import EventRef
from gramps.gen.lib import Repository
from gramps.gen.lib import RepoRef
from gramps.gen.lib import Source
from gramps.gen.lib import SrcAttribute

from gramps.gen.display.name import displayer as name_displayer

from gramps.gen.utils.libformatting import ImportInfo
from gramps.gen.errors import GrampsImportError as Error

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

#-------------------------------------------------------------------------
#
# Support and main functions
#
#-------------------------------------------------------------------------
def rd(line_number, row, col, key, default=""):
    """ Return Row data by column name """
    if key in col:
        if col[key] >= len(row):
            LOG.warning("missing '%s, on line %d" % (key, line_number))
            return default
        retval = str(row[col[key]]).strip()
        if retval == "":
            return default
        else:
            return retval
    else:
        return default

def read_xls(fname, sheetname):
    wb = xlrd.open_workbook(filename=fname)
    sheets = wb.sheets()
    print(type(sheets))
    for s in wb.sheets():
        kommentti = ""
        rows = []
        for row in range(0,s.nrows):
            values = []
            for col in range(s.ncols):
                values.append(str(s.cell(row,col).value))
            rows.append(values)
        return rows

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
        self.run(dbstate.db, user)



    def run(self, dbase, user):
        """Function called by Gramps to import data on persons in CSV format."""
        choose_file_dialog = Gtk.FileChooserDialog(
            title='', transient_for=self.uistate.window,
            action=Gtk.FileChooserAction.OPEN)
        choose_file_dialog.add_buttons(
            _('_Cancel'), Gtk.ResponseType.CANCEL,
            _('Import'), Gtk.ResponseType.OK)

        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        choose_file_dialog.add_filter(filter_csv)
        
        while True:
            response = choose_file_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                break
            elif response == Gtk.ResponseType.DELETE_EVENT:
                break
            elif response == Gtk.ResponseType.OK:
                filename = choose_file_dialog.get_filename()
                print(filename)

                if filename.endswith(".csv"):
                    parser = CSVParser(dbase, user, None)
                    parser.parsecsvfile(filename)

                if filename.endswith(".ods"):
                    parser = CSVParser(dbase, user, None)
                    parser.parseodsfile(filename)

                if filename.endswith(".xls") or filename.endswith(".xlsx"):
                    parser = CSVParser(dbase, user, None)
                    parser.parsexlsfile(filename)

                break
        choose_file_dialog.destroy()
        
#-------------------------------------------------------------------------
#
# CSV Parser
#
#-------------------------------------------------------------------------
class CSVParser:
    """Class to read data in CSV format from a file object."""
    def __init__(self, dbase, user, default_tag_format=None):
        self.db = dbase
        self.user = user
        self.trans = None
        self.lineno = 0
        self.index = 0
        self.source_count = 0
        self.repos = {}
        self.current_source = None

    def cleanup_column_name(self, column):
        """Handle column aliases for CSV spreadsheet import and SQL."""
        return self.label2column.get(column, column)

    def read_csv(self, filehandle):
        "Read the data from the file and return it as a list."
        reader = csv.reader(filehandle)
        try:
            data = [[r.strip() for r in row] for row in reader]
        except csv.Error as err:
            self.user.notify_error(_('format error: line %(line)d: %(zero)s') % {
                        'line' : reader.line_num, 'zero' : err } )
            return None
        return data


    def import_data(self, data, title):
        with self.user.progress(title,
                _('Importing data...'), len(data)) as step:
            tym = time.time()
            self.db.disable_signals()
            with DbTxn(title, self.db, batch=True) as self.trans:
                self._parse_data(data, step)
            self.db.enable_signals()
            self.db.request_rebuild()
            tym = time.time() - tym
            # translators: leave all/any {...} untranslated
            msg = ngettext('Import Complete: {number_of} second',
                           'Import Complete: {number_of} seconds', tym
                          ).format(number_of=tym)
            LOG.debug(msg)
            LOG.debug("New sources: %d" % self.source_count)
    
    def parseodsfile(self, filename):
        ods_data = get_data(filename)
        for data in ods_data.values():
            self.import_data(data, _("ODS import"),)

    def parsexlsfile(self, filename):
        data = read_xls(filename, "sources")
        self.import_data(data, _("XLS import"),)

    def parsecsvfile(self, filename):
        """
        Prepare the database and parse the input file.

        :param filehandle: open file handle positioned at start of the file
        """
        with open(filename, 'rb') as filehandle:
            line = filehandle.read(3)
            if line == codecs.BOM_UTF8:
                filehandle.seek(0)
                filehandle = TextIOWrapper(filehandle, encoding='utf_8_sig',
                                           errors='replace', newline='')
            else:                       # just open with OS encoding
                filehandle.seek(0)
                filehandle = TextIOWrapper(filehandle,
                                           errors='replace', newline='')
            data = self.read_csv(filehandle)

        self.import_data(data, _("CSV import"),)

    def _parse_data(self, data, step):
        """Parse each line of the input data and act accordingly."""
        self.lineno = 0
        self.index = 0
        self.fam_count = 0
        self.indi_count = 0
        self.place_count = 0
        self.pref = {} # person ref, internal to this sheet
        self.fref = {} # family ref, internal to this sheet
        self.placeref = {}
        header = None
        line_number = 1
        seq = 0

        col = {}
        for colnum,key in enumerate(data[0]):
            col[key.lower()] = colnum
        for row in data[1:]:
            step()
            line_number += 1
            seq += 1
            self._parse_source_line(line_number, seq, row, col)
        return None

        
    def _parse_source_line(self, line_number, seq, row, col):
        "Parse the content of a Source line."
        source_ref = rd(line_number, row, col, "source")

        source = Source()
        source.title = rd(line_number, row, col, "title")
        source.author = rd(line_number, row, col, "author")
        source.abbrev = rd(line_number, row, col, "abbrev")
        source.pubinfo = rd(line_number, row, col, "pubinfo")
        if source.title == "":
            if source.author != "": raise RuntimeError("Line {}: title is blank - author should be blank also".format(line_number))
            if source.abbrev != "": raise RuntimeError("Line {}: title is blank - abbrev should be blank also".format(line_number))
            if source.pubinfo != "": raise RuntimeError("Line {}: title is blank - pubinfo should be blank also".format(line_number))
            if self.current_source is None: raise RuntimeError("Line {}: title is blank".format(line_number))
            source = self.current_source
            add_new_source = False
        else:
            self.current_source = source
            add_new_source = True

        if add_new_source:
            self.db.add_source(source, self.trans)
            self.source_count += 1

        reponame = rd(line_number, row, col, "repository")
        repo_handle = None
        if reponame:
            repo_handle = self.repos.get(reponame)
            if repo_handle is None:
                if reponame.startswith("[") and reponame.endswith("]"):
                    repo_id = reponame[1:-1]
                    repo = self.db.get_repository_from_gramps_id(repo_id)
                    if repo:
                        repo_handle = repo.handle
                if repo_handle is None:
                    repo = Repository()
                    repo.name = reponame
                    repo_handle = self.db.add_repository(repo, self.trans)
                self.repos[reponame] = repo_handle
            if repo_handle:
                reporef = RepoRef()
                reporef.ref = repo_handle
                source.add_repo_reference(reporef)
            self.db.commit_source(source, self.trans)

        attributetype = rd(line_number, row, col, "attributetype")
        attributevalue = rd(line_number, row, col, "attributevalue")
        if attributetype:
            LOG.debug("adding attribute")
            attr = SrcAttribute()
            attr.set_type(attributetype)
            attr.set_value(attributevalue)
            source.add_attribute(attr)
            self.db.commit_source(source, self.trans)


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

