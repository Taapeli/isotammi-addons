"""
    Gramplet to select the URL for add-on installation
"""
#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
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

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _TRANS = glocale.get_addon_translator(__file__)
except ValueError:
    _TRANS = glocale.translation
_ = _TRANS.gettext

VERSION_DIR = "gramps%s%s" % VERSION_TUPLE[0:2]
DEFAULT_URL = "https://raw.githubusercontent.com/gramps-project/addons/master/" + VERSION_DIR
ISOTAMMI_URL = "https://raw.githubusercontent.com/Taapeli/isotammi-addons/master/addons/" + VERSION_DIR

#------------------------------------------------------------------------
#
# SelectAddonSource
#
#------------------------------------------------------------------------
class SelectAddonSource(Gramplet):
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

        label = Gtk.Label()
        label.set_markup("<b>{}</b>".format(_("Select the source for installing add-ons")))
        label.set_markup("<b>{}</b>".format(_("Where to check")))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        grid = Gtk.Grid(column_spacing=10)
        grid.set_margin_left(20)

        orig_url = config.get("behavior.addons-url")

        group = None

        rownum = 0
        group = Gtk.RadioButton.new_with_label_from_widget(group, _("Default"))
        group.connect("toggled", self.cb_select, DEFAULT_URL)
        grid.attach(group, 0, rownum, 1, 1)
        if orig_url == DEFAULT_URL:
            group.set_active(True)

        rownum = 1
        group = Gtk.RadioButton.new_with_label_from_widget(group, _("Isotammi"))
        group.connect("toggled", self.cb_select, ISOTAMMI_URL)
        grid.attach(group, 0, rownum, 1, 1)
        if orig_url == ISOTAMMI_URL:
            group.set_active(True)

        vbox.pack_start(grid, False, True, 0)

        btnbox = Gtk.ButtonBox()
        btn = Gtk.Button(_("Preferences"))
        btn.connect("clicked", lambda obj: GrampsPreferences(self.gui.uistate, self.dbstate).show())
        btnbox.add(btn)
        vbox.pack_start(btnbox, False, True, 0)

        vbox.show_all()
        return vbox

    @staticmethod
    def cb_select(obj, url):
        "Set the selected addon url"
        config.set("behavior.addons-url", url)
