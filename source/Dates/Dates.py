# encoding:utf-8
#
# Gramplet addon - for the Gramps GTK+/GNOME based genealogy program
#
# Copyright (C) 2020-2024 Kari Kujansuu, the Isotammi project
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

import datetime
import pprint
import re
import traceback

from gi.repository import Gtk

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------

from gramps.gen.datehandler import parser
from gramps.gen.plug import Gramplet
from gramps.gen.db import DbTxn
from gramps.gen.lib import Date

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# regex helpers
zerototwozeros = r"0{0,2}"
oneortwodigits = r"\d{1,2}"
twodigits = r"\d{2}"
fourdigits = r"\d{4}"
dot = r"\."
dash = r"-"
sep = "[\.,-/]"
gt = "\>"
lt = "\<"
space = r"\s"


def p(**kwargs):
    assert len(kwargs) == 1
    for name, pat in kwargs.items():
        return "(?P<{name}>{pat})".format(name=name, pat=pat)
    raise Error


def optional(pat):
    return "({pat})?".format(pat=pat)


def match(s, *args):
    pat = "".join(args)
    flags = re.VERBOSE
    r = re.fullmatch(pat, s, flags)
    if r is None:
        return None

    class Ret:
        pass

    ret = Ret()
    ret.__dict__ = r.groupdict()
    return ret


def dateval(y, m, d):
    try:
        y = int(y)
        m = int(m)
        d = int(d)
        dt = datetime.date(y, m, d)
        return (d, m, y, False)
    except:
        traceback.print_exc()
        return None


class Dates(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Transforms to correct invalid date formats"))

    def db_changed(self):
        self.__clear(None)

    def __clear(self, obj):
        pass

    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet helps to correct invalid date formats:"))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        self.replace_text = Gtk.CheckButton(_("Replace text"))
        self.replace_text.connect("clicked", self.__select_replace_text)

        self.use_regex = Gtk.CheckButton(_("Use regular expressions"))
        self.use_regex.set_sensitive(False)

        replace_text_box = Gtk.HBox()
        replace_text_box.pack_start(self.replace_text, False, True, 0)
        replace_text_box.pack_start(self.use_regex, False, True, 0)
        vbox.pack_start(replace_text_box, False, True, 0)

        old_text_label = Gtk.Label()
        old_text_label.set_markup("<b>{}</b>".format(_("Find:")))
        self.old_text = Gtk.Entry(width_chars=30)
        old_text_label.set_halign(Gtk.Align.END)
        self.old_text.set_sensitive(False)

        new_text_label = Gtk.Label()
        new_text_label.set_markup("<b>{}</b>".format(_("Replace:")))
        self.new_text = Gtk.Entry(width_chars=30)
        self.new_text.set_halign(Gtk.Align.END)
        self.new_text.set_sensitive(False)

        replace_grid = Gtk.Grid(column_spacing=10)
        replace_grid.set_margin_left(20)
        replace_grid.attach(old_text_label, 1, 0, 1, 1)
        replace_grid.attach(self.old_text, 2, 0, 3, 1)
        replace_grid.attach(new_text_label, 1, 1, 1, 1)
        replace_grid.attach(self.new_text, 2, 1, 3, 1)
        vbox.pack_start(replace_grid, False, True, 0)

#         self.reparse = Gtk.CheckButton(label=_("Re-parse date"))
#         vbox.pack_start(self.reparse, False, True, 0)

        self.handle_dd_mm_yyyy = Gtk.CheckButton(label=_("31.12.1888 ⇒ 1888-12-31"))
        vbox.pack_start(self.handle_dd_mm_yyyy, False, True, 0)

        self.handle_mm_dd_yyyy = Gtk.CheckButton(label=_("12.31.1888 ⇒ 1888-12-31"))
        vbox.pack_start(self.handle_mm_dd_yyyy, False, True, 0)

        self.handle_yyyy_mm_dd = Gtk.CheckButton(label=_("1888.12.31 ⇒ 1888-12-31"))
        vbox.pack_start(self.handle_yyyy_mm_dd, False, True, 0)

        self.handle_yyyy_dd_mm = Gtk.CheckButton(label=_("1888.31.12 ⇒ 1888-12-31"))
        vbox.pack_start(self.handle_yyyy_dd_mm, False, True, 0)

        self.handle_mm_yyyy = Gtk.CheckButton(label=_(".12.1888 ⇒ 1888-12"))
        vbox.pack_start(self.handle_mm_yyyy, False, True, 0)

        self.handle_dd_yyyy = Gtk.CheckButton(label=_("31..1888 ⇒ 1888-00-31"))
        vbox.pack_start(self.handle_dd_yyyy, False, True, 0)

        self.handle_yyyy = Gtk.CheckButton(label=_("..1888 ⇒ 1888"))
        vbox.pack_start(self.handle_yyyy, False, True, 0)

        self.handle_intervals = Gtk.CheckButton(label=_("1888-99 ⇒ 1888 - 1899"))
        vbox.pack_start(self.handle_intervals, False, True, 0)

        # self.handle_intervals2 = Gtk.CheckButton(label=_('1888-1899 ⇒ 1888 - 1899'))
        # vbox.pack_start(self.handle_intervals2, False, True, 0)

        self.handle_before = Gtk.CheckButton(label=_("<1888 (or -1888) ⇒ before 1888"))
        vbox.pack_start(self.handle_before, False, True, 0)

        self.handle_after = Gtk.CheckButton(label=_(">1888 (or 1888-) ⇒ after 1888"))
        vbox.pack_start(self.handle_after, False, True, 0)

        msg = _("Dot (period) means any delimiter: dot, comma, hyphen, slash.")
        vbox.pack_start(Gtk.Label(msg), False, True, 0)

        btn_execute = Gtk.Button(label=_("Execute"))
        btn_execute.set_margin_start(50)
        btn_execute.set_margin_end(50)
        btn_execute.set_halign(Gtk.Align.CENTER)
        btn_execute.connect("clicked", self.__execute)
        vbox.pack_start(btn_execute, False, True, 30)

        vbox.show_all()
        return vbox

    def __select_replace_text(self, obj):
        checked = self.replace_text.get_active()
        self.old_text.set_sensitive(checked)
        self.new_text.set_sensitive(checked)
        self.use_regex.set_sensitive(checked)

    def __execute(self, obj):
        with DbTxn(_("Correcting invalid dates"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_places = len(selected_handles)
            for eventhandle in selected_handles:
                event = self.dbstate.db.get_event_from_handle(eventhandle)
                # print(event)
                dateobj = event.get_date_object()
                datestr = dateobj.get_text()
                old_values = repr(dateobj.__dict__)
                if dateobj.is_valid():
                    # print(dateobj, "is valid")
                    continue
                if datestr == "":
                    # print(dateobj, "is blank")
                    continue
                old_values = repr(dateobj.__dict__)

                if self.replace_text.get_active():
                    datestr = dateobj.get_text()
                    old_text = self.old_text.get_text()
                    new_text = self.new_text.get_text()
                    if self.use_regex.get_active():
                        try:
                            new_datestr = re.sub(old_text, new_text, datestr)
                        except Exception as e:
                            traceback.print_exc()
                            raise RuntimeError(
                                _("Regex operation failed: {}").format(e)
                            )
                    else:
                        new_datestr = datestr.replace(old_text, new_text)
                    if new_datestr != datestr:
                        dateobj.set(text=new_datestr, modifier=Date.MOD_TEXTONLY)

                datestr = dateobj.get_text()
                self.__fix_date(dateobj, datestr)

                if dateobj.get_modifier() == Date.MOD_TEXTONLY:
                    datestr = dateobj.get_text()
                    dateobj = parser.parse(datestr)
                    event.set_date_object(dateobj)

                new_values = repr(dateobj.__dict__)
                if new_values != old_values:
                    self.dbstate.db.commit_event(event, self.trans)

    def __fix_date(self, dateobj, datestr):
        if self.handle_dd_mm_yyyy.get_active():
            # 31.12.1888 ⇒ 31 DEC 1888
            # 31,12,1888 ⇒ 31 DEC 1888
            # 31-12-1888 ⇒ 31 DEC 1888
            # 31/12/1888 ⇒ 31 DEC 1888
            r = match(
                datestr,
                p(d=oneortwodigits),
                sep,
                p(m=oneortwodigits),
                sep,
                p(y=fourdigits),
            )
            if r:
                val = dateval(r.y, r.m, r.d)
                if val:
                    dateobj.set(value=val, modifier=Date.MOD_NONE)
                    return

        if self.handle_mm_dd_yyyy.get_active():
            # 12.31.1888 ⇒ 31 DEC 1888
            # 12,31,1888 ⇒ 31 DEC 1888
            # 12-31-1888 ⇒ 31 DEC 1888
            # 12/31/1888 ⇒ 31 DEC 1888
            r = match(
                datestr,
                p(m=oneortwodigits),
                sep,
                p(d=oneortwodigits),
                sep,
                p(y=fourdigits),
            )
            if r:
                val = dateval(r.y, r.m, r.d)
                if val:
                    dateobj.set(value=val, modifier=Date.MOD_NONE)
                    return

        if self.handle_yyyy_mm_dd.get_active():
            # 1888.12.31 ⇒ 31 DEC 1888
            # 1888,12,31 ⇒ 31 DEC 1888
            # 1888-12-31 ⇒ 31 DEC 1888
            # 1888/12/31 ⇒ 31 DEC 1888
            r = match(
                datestr,
                p(y=fourdigits),
                sep,
                p(m=oneortwodigits),
                sep,
                p(d=oneortwodigits),
            )
            if r:
                val = dateval(r.y, r.m, r.d)
                if val:
                    dateobj.set(value=val, modifier=Date.MOD_NONE)
                    return

        if self.handle_yyyy_dd_mm.get_active():
            # 1888.31.12 ⇒ 31 DEC 1888
            # 1888,31,12 ⇒ 31 DEC 1888
            # 1888-31-12 ⇒ 31 DEC 1888
            # 1888/31/12 ⇒ 31 DEC 1888
            r = match(
                datestr,
                p(y=fourdigits),
                sep,
                p(d=oneortwodigits),
                sep,
                p(m=oneortwodigits),
            )
            if r:
                val = dateval(r.y, r.m, r.d)
                if val:
                    dateobj.set(value=val, modifier=Date.MOD_NONE)
                    return

        if self.handle_mm_yyyy.get_active():
            # .12.1888 ⇒ 31 DEC 1888
            r = match(datestr, sep, p(m=oneortwodigits), sep, p(y=fourdigits))
            if r:
                val = dateval(r.y, r.m, 1)
                if val:
                    dateobj.set(
                        value=(0, int(r.m), int(r.y), False), modifier=Date.MOD_NONE
                    )
                    return

        if self.handle_dd_yyyy.get_active():
            # 31..1888 ⇒ 1888-00-31
            r = match(datestr, p(d=oneortwodigits), sep, sep, p(y=fourdigits))
            if r:
                val = dateval(r.y, 1, r.d)
                if val:
                    dateobj.set(
                        value=(int(r.d), 0, int(r.y), False), modifier=Date.MOD_NONE
                    )
                    return

        if self.handle_yyyy.get_active():
            # ..1888 ⇒ 1888
            r = match(datestr, sep, sep, p(y=fourdigits))
            if r:
                dateobj.set(value=(0, 0, int(r.y), False), modifier=Date.MOD_NONE)
                return

        if self.handle_intervals.get_active():
            # 1888-1899
            r = match(datestr, p(y1=fourdigits), dash, p(y2=fourdigits))
            if r:
                dateobj.set(
                    modifier=Date.MOD_SPAN,
                    value=(0, 0, int(r.y1), False, 0, 0, int(r.y2), False),
                )
                return

            # 1888 -1899
            r = match(datestr, p(y1=fourdigits), space, dash, p(y2=fourdigits))
            if r:
                dateobj.set(
                    modifier=Date.MOD_SPAN,
                    value=(0, 0, int(r.y1), False, 0, 0, int(r.y2), False),
                )
                return

            # 1888- 1899
            r = match(datestr, p(y1=fourdigits), dash, space, p(y2=fourdigits))
            if r:
                dateobj.set(
                    modifier=Date.MOD_SPAN,
                    value=(0, 0, int(r.y1), False, 0, 0, int(r.y2), False),
                )
                return

            # 1888-99
            r = match(datestr, p(y1=fourdigits), dash, p(y2=twodigits))
            if r:
                if int(r.y2) > int(r.y1[2:]):
                    century = r.y1[0:2]
                    # dateobj.set(modifier=Date.MOD_RANGE,value=(0,0,int(r.y1),False,0,0,int(century+r.y2),False))
                    dateobj.set(
                        modifier=Date.MOD_SPAN,
                        value=(
                            0,
                            0,
                            int(r.y1),
                            False,
                            0,
                            0,
                            int(century + r.y2),
                            False,
                        ),
                    )
                    return

        if self.handle_before.get_active():
            r = match(datestr, dash, p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_BEFORE, value=(0, 0, int(r.y), False))
                return
            r = match(datestr, lt, p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_BEFORE, value=(0, 0, int(r.y), False))
                return

        if self.handle_after.get_active():
            r = match(
                datestr,
                p(y=fourdigits),
                dash,
            )
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_AFTER, value=(0, 0, int(r.y), False))
                return
            r = match(datestr, gt, p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_AFTER, value=(0, 0, int(r.y), False))
                return
