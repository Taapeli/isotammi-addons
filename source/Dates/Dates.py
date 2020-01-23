import datetime
import json
import pprint
import re
import traceback

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Event, EventRef, EventType, Tag, Date

from gramps.gui.dialog import OkDialog

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

def p(**kwargs):
    assert len(kwargs) == 1
    for name,pat in kwargs.items():
        return "(?P<{name}>{pat})".format(name=name,pat=pat)
    raise Error

def optional(pat):
    return "({pat})?".format(pat=pat)    

def match(s,*args):    
    pat = "".join(args)
    print(s)
    print(pat)
    flags = re.VERBOSE
    r = re.fullmatch(pat,s,flags)
    if r is None: return None
    class Ret: pass
    ret = Ret()
    ret.__dict__ = r.groupdict()
    return ret

def dateval(y,m,d):
    print(y,m,d)
    try:
        y = int(y)
        m = int(m)
        d = int(d)
        dt = datetime.date(y,m,d)
        return (d,m,y,False)
    except:
        traceback.print_exc()
        return None

class Dates(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Correct invalid dates"))

    def db_changed(self):
        self.__clear(None)
        
    def __clear(self, obj):
        pass

    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet helps to correct invalid dates..."))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        self.replace_text = Gtk.CheckButton(_("Replace text"))
        self.replace_text.connect("clicked", self.__select_replace_text)

        self.use_regex = Gtk.CheckButton(_("Use regex"))
        self.use_regex.set_sensitive(False)

        replace_text_box = Gtk.HBox()
        replace_text_box.pack_start(self.replace_text, False, True, 0)
        replace_text_box.pack_start(self.use_regex, False, True, 0)
        vbox.pack_start(replace_text_box, False, True, 0)

        old_text_label = Gtk.Label()
        old_text_label.set_markup("<b>{}</b>".format(_("Old text:")))
        self.old_text = Gtk.Entry()
        self.old_text.set_sensitive(False)

        new_text_label = Gtk.Label()
        new_text_label.set_markup("<b>{}</b>".format(_("New text:")))
        self.new_text = Gtk.Entry()
        self.new_text.set_sensitive(False)

        replace_grid = Gtk.Grid(column_spacing=10)
        replace_grid.set_margin_left(20)
        replace_grid.attach(old_text_label,1,0,1,1)
        replace_grid.attach(self.old_text,2,0,1,1)
        replace_grid.attach(new_text_label,1,1,1,1)
        replace_grid.attach(self.new_text,2,1,1,1)
        vbox.pack_start(replace_grid, False, True, 0)


        self.handle_dd_mm_yyyy = Gtk.CheckButton(label=_('31.12.1888 -> 1888-12-31'))
        vbox.pack_start(self.handle_dd_mm_yyyy, False, True, 0)

        self.handle_intervals = Gtk.CheckButton(label=_('1888-99 -> from 1888 to 1899'))
        vbox.pack_start(self.handle_intervals, False, True, 0)

        self.handle_before = Gtk.CheckButton(label=_('<1888/-1888 -> before 1888'))
        vbox.pack_start(self.handle_before, False, True, 0)

        self.handle_after = Gtk.CheckButton(label=_('>1888/1888- -> after 1888'))
        vbox.pack_start(self.handle_after, False, True, 0)



        btn_execute = Gtk.Button(label=_('Execute'))
        btn_execute.connect("clicked", self.__execute)
        vbox.pack_start(btn_execute, False, True, 20)


        vbox.show_all()
        return vbox
    
    def __select_replace_text(self,obj):
        checked = self.replace_text.get_active()
        self.old_text.set_sensitive(checked)
        self.new_text.set_sensitive(checked)
        self.use_regex.set_sensitive(checked)

    
    def __execute(self,obj):
        with DbTxn(_("Correcting invalid dates"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_places = len(selected_handles)
            for eventhandle in selected_handles:
                event = self.dbstate.db.get_event_from_handle(eventhandle)
                print(event)
                dateobj = event.get_date_object()
                datestr = dateobj.get_text()
                pprint.pprint(dateobj.__dict__)
                if dateobj.is_valid():
                    print(dateobj,"is valid")
                    continue
                if datestr == "":
                    print(dateobj,"is blank")
                    continue
                print(datestr,"is INvalid")
                self.__fix_date(dateobj,datestr)
                print("newdate:",repr(dateobj))
                pprint.pprint(dateobj.__dict__)
                #event.set_date_object(dateobj)
                #dateobj.set_text_value(newdate)

                if self.replace_text.get_active():
                    datestr = dateobj.get_text()
                    old_text = self.old_text.get_text()
                    new_text = self.new_text.get_text()
                    if self.use_regex.get_active():
                        try:
                            new_datestr = re.sub(old_text,new_text,datestr)
                        except Exception as e:
                            traceback.print_exc()
                            raise RuntimeError(_("Regex operation failed: {}").format(e))
                    else:
                        new_datestr = datestr.replace(old_text,new_text)
                    if new_datestr != datestr: dateobj.set(text=new_datestr,modifier=Date.MOD_TEXTONLY)

                self.dbstate.db.commit_event(event,self.trans)

    def __fix_date(self, dateobj, datestr):
        if self.handle_dd_mm_yyyy.get_active():
                # 31.12.1888 -> 31 DEC 1888
                # 31,12,1888 -> 31 DEC 1888
                # 31-12-1888 -> 31 DEC 1888
                # 31/12/1888 -> 31 DEC 1888
                r = match(datestr,
                          p(d=oneortwodigits),sep,
                          p(m=oneortwodigits),sep,
                          p(y=fourdigits))
                if r:
                    val = dateval(r.y,r.m,r.d)
                    if val:
                        dateobj.set(value=val,modifier=Date.MOD_NONE)
                        return 

        if self.handle_intervals.get_active():
            # 1888-1899 
            r = match(datestr,p(y1=fourdigits),dash,p(y2=fourdigits))
            if r:
                dateobj.set(modifier=Date.MOD_SPAN,value=(0,0,int(r.y1),False,0,0,int(r.y2),False),)
                return 

            # 1888-99
            r = match(datestr,p(y1=fourdigits),dash,p(y2=twodigits))
            if r:
                if int(r.y2) > int(r.y1[2:]): 
                    century = r.y1[0:2]
                    #dateobj.set(modifier=Date.MOD_RANGE,value=(0,0,int(r.y1),False,0,0,int(century+r.y2),False))
                    dateobj.set(modifier=Date.MOD_SPAN,value=(0,0,int(r.y1),False,0,0,int(century+r.y2),False))
                    return 

        if self.handle_before.get_active():
            r = match(datestr,dash,p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_BEFORE,value=(0,0,int(r.y),False))
                return
            r = match(datestr,lt,p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_BEFORE,value=(0,0,int(r.y),False))
                return

        if self.handle_after.get_active():
            r = match(datestr,p(y=fourdigits),dash,)
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_AFTER,value=(0,0,int(r.y),False))
                return
            r = match(datestr,gt,p(y=fourdigits))
            if r:
                text = "{r.y}".format(**locals())
                dateobj.set(modifier=Date.MOD_AFTER,value=(0,0,int(r.y),False))
                return

    '''
    class Date:
    ...
    def set(self, quality=None, modifier=None, calendar=None,
            value=None, text=None, newyear=0):
        """
        Set the date to the specified value.

        :param quality: The date quality for the date (see :meth:`get_quality`
                        for more information).
                        Defaults to the previous value for the date.
        :param modified: The date modifier for the date (see
                         :meth:`get_modifier` for more information)
                         Defaults to the previous value for the date.
        :param calendar: The calendar associated with the date (see
                         :meth:`get_calendar` for more information).
                         Defaults to the previous value for the date.
        :param value: A tuple representing the date information. For a
                      non-compound date, the format is (DD, MM, YY, slash)
                      and for a compound date the tuple stores data as
                      (DD, MM, YY, slash1, DD, MM, YY, slash2)
                      Defaults to the previous value for the date.
        :param text: A text string holding either the verbatim user input
                     or a comment relating to the date.
                     Defaults to the previous value for the date.
        :param newyear: The newyear code, or tuple representing (month, day)
                        of newyear day.
                        Defaults to 0.

        The sort value is recalculated.
        """
'''
        
    def transform(self,item,options,phase):
        """
        Fix dates of the forms:
        
        31.12.1888    -> 31 DEC 1888
        31,12,1888    -> 31 DEC 1888
        31-12-1888    -> 31 DEC 1888
        31/12/1888    -> 31 DEC 1888
        1888-12-31    -> 31 DEC 1888
        .12.1888      ->    DEC 1888
        12.1888       ->    DEC 1888
        12/1888       ->    DEC 1888
        12-1888       ->    DEC 1888
        0.12.1888     ->    DEC 1888
        00.12.1888    ->    DEC 1888
        00.00.1888    ->    1888
        00 JAN 1888   ->    JAN 1888
        1950-[19]59   -> FROM 1950 TO 1959
        1950-         -> FROM 1950 
        >1950         -> FROM 1950 
        -1950         -> TO 1950 
        <1950         -> TO 1950 
        """
        self.options = options

        if item.tag == "DATE":
            value = item.value.strip()

            if options.handle_dd_mm_yyyy:
                    # 31.12.1888 -> 31 DEC 1888
                    # 31,12,1888 -> 31 DEC 1888
                    # 31-12-1888 -> 31 DEC 1888
                    # 31/12/1888 -> 31 DEC 1888
                    r = match(value,
                              p(d=oneortwodigits),sep,
                              p(m=oneortwodigits),sep,
                              p(y=fourdigits))
                    if r:
                        val = fmtdate(r.y,r.m,r.d)
                        if val:
                            item.value = val
                            return item
    
            if options.handle_zeros:
                # 0.0.1888 -> 1888
                # 00.00.1888 -> 1888
                r = match(value,zerototwozeros,dot,zerototwozeros,p(y=fourdigits))
                if r:
                    item.value = r.y
                    return item
            
                # 00.12.1888 -> DEC 1888
                # .12.1888 -> DEC 1888
                #  12.1888 -> DEC 1888
                r = match(value,zerototwozeros,dot,p(m=oneortwodigits),dot,p(y=fourdigits))
                if not r:
                    r = match(value,p(m=oneortwodigits),dot,p(y=fourdigits))
                if r:
                    val = fmtdate(r.y,r.m,1)
                    if val:
                        item.value = val[3:]
                        return item

            if options.handle_zeros2:
                # 0 JAN 1888   ->    JAN 1888
                if value.startswith("0 "):
                    item.value = item.value[2:]
                    return item
                
                # 00 JAN 1888   ->    JAN 1888
                if value.startswith("00 "):
                    item.value = item.value[3:]
                    return item
    
    
            if options.handle_intervals:
                # 1888-1899 
                r = match(value,p(y1=fourdigits),dash,p(y2=fourdigits))
                if r:
                    century = r.y1[0:2]
                    item.value = "FROM {r.y1} TO {r.y2}".format(**locals())
                    return item
    
                # 1888-99
                r = match(value,p(y1=fourdigits),dash,p(y2=twodigits))
                if r:
                    if int(r.y2) > int(r.y1[2:]): 
                        century = r.y1[0:2]
                        item.value = "FROM {r.y1} TO {century}{r.y2}".format(**locals())
                        return item
                    
            if options.handle_intervals2:
                # 1888-, >1888
                tag = item.path.split(".")[-2]
                kw = "AFT"
                if tag in ('RESI','OCCU'): kw = "FROM"
                r = match(value,p(y=fourdigits),dash)
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
                r = match(value,gt,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
    
            if options.handle_intervals3:
                # -1888, <1888
                tag = item.path.split(".")[-2]
                kw = "BE"
                if tag in ('RESI','OCCU'): kw = "ennen"
                r = match(value,dash,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals()) 
                    return item
                r = match(value,lt,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
    
            if options.handle_yyyy_mm_dd:
                # 1888-12-31
                r = match(value,p(y=fourdigits),dash,p(m=twodigits),dash,p(d=twodigits))
                if r:
                    val = fmtdate(r.y,r.m,r.d)
                    if val:
                        item.value = val
                        return item
    
            if options.handle_yyyy_mm:
                # 1888-12
                r = match(value,p(y=fourdigits),dash,p(m=twodigits))
                if r:
                    val = fmtdate(r.y,r.m,1)
                    if val:
                        item.value = val[3:]
                        return item

        return True

