"""
    Gramplet to select the URL for add-on installation
"""
#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.version import VERSION_TUPLE
from gramps.gen.config import config

from gramps.gen.plug import Gramplet
from gramps.gui.configure import GrampsPreferences
from gramps.gen.config import config as configman

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _TRANS = glocale.get_addon_translator(__file__)
except ValueError:
    _TRANS = glocale.translation
_ = _TRANS.gettext

VERSION_DIR = "gramps%s%s" % VERSION_TUPLE[0:2]
DEFAULT_URL = "https://raw.githubusercontent.com/gramps-project/addons/master/" + VERSION_DIR
ISOTAMMI_URL = "https://raw.githubusercontent.com/Taapeli/isotammi-addons/master/addons/" + VERSION_DIR

isotammi_config = configman.register_manager("isotammi")
isotammi_config.register("options.apikey", "") 
isotammi_config.register("options.apiurl", "") 

def get_apikey():
    isotammi_config.load()
    apikey = isotammi_config.get('options.apikey')
    return apikey

def set_apikey(apikey):
    isotammi_config.load()
    isotammi_config.set('options.apikey', apikey)
    isotammi_config.save()

def get_apiurl():
    isotammi_config.load()
    apiurl = isotammi_config.get('options.apiurl')
    return apiurl

def set_apiurl(apiurl):
    isotammi_config.load()
    isotammi_config.set('options.apiurl', apiurl)
    isotammi_config.save()


#------------------------------------------------------------------------
#
# SelectAddonSource
#
#------------------------------------------------------------------------
class IsotammiConfig(Gramplet):
    """
        Selectaddonsource
    """
    def __init__(self, *args):
        Gramplet.__init__(self, *args)
        self.root = None

    def init(self):
        """
            init
        """
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)

    def __create_gui(self):
        """
            __create_gui
        """
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_margin_top(20)
        grid.set_margin_left(20)

        label_url = Gtk.Label(_("Isotammi URL"))
        grid.attach(label_url, 0, 0, 1, 1)
        self.entry_apiurl = Gtk.Entry()
        self.entry_apiurl.set_width_chars(40)
        grid.attach(self.entry_apiurl, 1, 0, 1, 1)

        label_apikey = Gtk.Label(_("API Key"))
        grid.attach(label_apikey, 0, 1, 1, 1)
        self.entry_apikey = Gtk.Entry()
        grid.attach(self.entry_apikey, 1, 1, 1, 1)
        

        label = Gtk.Label(_("Addon source"))
        #abel.set_markup("<b>{}</b>".format(_("Select the source for installing add-ons")))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)

        grid.attach(label, 0, 2, 1, 1)

        self.addons_url = config.get("behavior.addons-url")

        group = None

        group = Gtk.RadioButton.new_with_label_from_widget(group, _("Default"))
        group.connect("toggled", self.cb_select, DEFAULT_URL)
        grid.attach(group, left=1, top=2, width=1, height=1)
        if self.addons_url == DEFAULT_URL:
            group.set_active(True)

        rownum = 1
        group = Gtk.RadioButton.new_with_label_from_widget(group, _("Isotammi"))
        group.connect("toggled", self.cb_select, ISOTAMMI_URL)
        if self.addons_url == ISOTAMMI_URL:
            group.set_active(True)

        grid.attach(group, 1, 3, 1, 1)

        btnbox = Gtk.ButtonBox()

        btn_save = Gtk.Button(_("Save"))
        btn_save.connect("clicked", self.save )
        btnbox.add(btn_save)

        btn = Gtk.Button(_("Gramps preferences"))
        btn.connect("clicked", lambda obj: GrampsPreferences(self.gui.uistate, self.dbstate).show())
        btnbox.add(btn)

        vbox.pack_start(grid, False, True, 0)
        #vbox.pack_start(label, False, True, 0)
        #vbox.pack_start(grid, False, True, 0)

        vbox.pack_start(btnbox, False, True, 0)

        apikey = get_apikey()
        self.entry_apikey.set_text(apikey)
        
        apiurl = get_apiurl()
        self.entry_apiurl.set_text(apiurl)

        vbox.show_all()
        return vbox

    def cb_select(self, obj, url):
        "Set the selected addon url"
        self.addons_url = url

    def save(self, obj):
        "Save values"
        print("saving")
        apikey = self.entry_apikey.get_text()
        set_apikey(apikey)
        
        apiurl = self.entry_apiurl.get_text()
        set_apiurl(apiurl)

        config.set("behavior.addons-url", self.addons_url)
        