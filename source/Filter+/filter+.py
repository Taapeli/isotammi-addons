import time

from gi.repository import Gtk

import gramps.gen.filters

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.filters import reload_custom_filters

from gramps.gui.editors import EditFilter
from gramps.gui.filters.sidebar import (
    PersonSidebarFilter, FamilySidebarFilter, EventSidebarFilter,
    SourceSidebarFilter, CitationSidebarFilter, PlaceSidebarFilter,
    MediaSidebarFilter, RepoSidebarFilter, NoteSidebarFilter)

from gramps.plugins.gramplet.filter import Filter
from gramps.gen.filters.rules.event._hasdata import HasData
from gramps.gen.filters.rules.citation._hassource import HasSource
from gramps.gen.filters.rules._haseventbase import HasEventBase
from gramps.gen.filters.rules._hassourcebase import HasSourceBase
from gramps.gui.filters._searchbar import SearchBar
from gramps.gen.filters.rules.person import RegExpName
from gramps.gen.filters import GenericFilter
from gramps.gen.filters.rules._rule import Rule
from gramps.gen.filters._genericfilter import GenericFamilyFilter
from gramps.gen.filters.rules.family._memberbase import father_base, mother_base
from gramps.gen.filters.rules.family._regexpfathername import RegExpFatherName
from gramps.gen.filters.rules.family._regexpmothername import RegExpMotherName
from gramps.gen.filters.rules.family._regexpchildname import RegExpChildName

_ = glocale.translation.gettext
    
#-------------------------------------------------------------------------
#
# SidebarFilterBase class
#
#-------------------------------------------------------------------------
class SidebarFilterBase:

    def _init_interface(self):
        super()._init_interface()
        b = Gtk.Button(_("Define filter"))
        b.connect("clicked", self.define_filter)
        hbox = Gtk.ButtonBox()
        hbox.set_layout(Gtk.ButtonBoxStyle.START)
        hbox.set_spacing(6)
        hbox.set_border_width(12)
        hbox.add(b)

        self.msg_label = Gtk.Label()
        self.msg_label.set_halign( Gtk.Align.START)
        self.msg_label.set_margin_left(12)

        if isinstance(self, CitationSidebarFilter):
            self.set_min_conf_to_very_low()
                    
        self.vbox.pack_start(hbox, False, False, 0)
        self.vbox.pack_start(self.msg_label, False, False, 0)

    def set_min_conf_to_very_low(self):
        grid = self.vbox.get_children()[0]
        for i,c in enumerate(grid.get_children()):
            if isinstance(c, Gtk.ComboBox):
                tree_iter = c.get_active_iter()
                if tree_iter is not None:
                    model = c.get_model()
                    text = model[tree_iter][0]
                    if text == _("Normal"):                
                        c.set_active(0)

    def get_filter(self):
        the_filter = super().get_filter()
        if the_filter is None:
            return None

        if isinstance(self, FamilySidebarFilter):
            new_filter = GenericFamilyFilter()
            for rule in the_filter.flist:
                if isinstance(rule, RegExpFatherName):
                    for name in rule.list[0].split():
                        new_filter.add_rule(RegExpFatherName([name], use_regex=rule.use_regex))
                elif isinstance(rule, RegExpMotherName):
                    for name in rule.list[0].split():
                        new_filter.add_rule(RegExpMotherName([name], use_regex=rule.use_regex))
                elif isinstance(rule, RegExpChildName):
                    for name in rule.list[0].split():
                        new_filter.add_rule(RegExpChildName([name], use_regex=rule.use_regex))
                else:
                    new_filter.add_rule(rule)
            the_filter = new_filter
        return the_filter

    def define_filter(self, _obj):
        self.filterdb = gramps.gen.filters.CustomFilters
        the_filter = self.get_filter()
        if the_filter is None:
            self.msg_label.set_markup("<span color='red'>" + _("Supply at least one value") + "</span>")
            return


        # fix some rules:
        new_rules = []
        for rule in the_filter.get_rules():
            print("rule:", rule.__class__.__name__)
            # HasEvent is defined as an alias for HasEventBase in gramps.gen.filters.rules.event.__init__
            # and the rule class will be HasEventBase.
            # But the code parsing custom_filters.xml does not accept HasEventBase because it is not listed
            # in gramps.gen.filters.rules.event.__init__.py.
            # The workaround is to create a new custom rule HasEventBase1 which is identical to HasEventBase.
            if rule.__class__.__name__ == "HasEventBase":
                rule1 = HasEventBasePlus(rule.list, rule.use_regex)
                new_rules.append(rule1)
                continue
            # Similar problem with HasSourceBase.
            if rule.__class__.__name__ == "HasSourceBase":
                rule1 = HasSourceBasePlus(rule.list, rule.use_regex)
                new_rules.append(rule1)
                continue
            # The Place rule WithinArea might have None or numeric values while custom_filters.xml only accepts strings.
            if rule.__class__.__name__ == "WithinArea":
                if rule.list[0] is None:
                    rule.list[0] = "Pxxxx"
                rule.list[1] = str(rule.list[1])
                rule.list[2] = str(rule.list[2])
            new_rules.append(rule)
        the_filter.flist = new_rules
        comment = "Created by Filter+ gramplet on " + time.strftime("%Y-%m-%d", time.localtime(time.time()))
        the_filter.set_comment(comment)
        
        self.msg_label.set_text("")
        track = []
        EditFilter(self.namespace, self.dbstate, self.uistate, track,
                   the_filter, self.filterdb, update=self.update)

    def update(self):
        self.filterdb.save()
        reload_custom_filters()
        self.uistate.emit('filters-changed', (self.namespace,))

    def clicked(self, obj):
        t1 = time.perf_counter()
        super().clicked(obj)
        t2 = time.perf_counter()
        #print(t2-t1)
        msg = _("Elapsed time: %.2fs") % (t2-t1) 
        self.msg_label.set_text(msg)
    

class PersonFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, PersonSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class FamilyFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, FamilySidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class EventFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, EventSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class PlaceFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, PlaceSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class CitationFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, CitationSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class SourceFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, SourceSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class RepositoryFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, RepoSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class MediaFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, MediaSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus

class NoteFilterPlus(Filter):
    class SidebarFilterPlus(SidebarFilterBase, NoteSidebarFilter):
        pass
    FILTER_CLASS = SidebarFilterPlus



#-------------------------------------------------------------------------
#
# HasEventBasePlus
#
#-------------------------------------------------------------------------
class HasEventBasePlus(HasEventBase):
    pass

#-------------------------------------------------------------------------
#
# HasSourceBasePlus
#
#-------------------------------------------------------------------------
class HasSourceBasePlus(HasSourceBase):
    pass


class NameMatch(Rule):
    """Rule that checks for full or partial name matches"""
 
    labels = [_('Text:')]
    name = _('People with a name matching <text>')
    description = _("Matches people's names containing a substring or "
                    "matching a regular expression")
    category = _('General filters')
    allow_regex = True
 
    def prepare(self, db, user):
        """prepare so the rule can be executed efficiently"""
        self.names = set(self.list[0].strip().lower().split())
        print("NameMatch",self.__class__.__name__, self.names)
 
    def apply(self,db, person):
        for name in self.names:
            if self.bname.lower() not in self.names:
                return False
        return True
    
class FatherNameMatch(RegExpName):
    """Rule that checks for full or partial name matches"""

    labels = [_('Text:')]
    name = _('People with first names matching <text>')
    description = _("Matches if each of person's first names is one of the names given as parameters")
    category = _('General filters')
    allow_regex = True
    base_class = RegExpName
    apply = father_base
    
class MotherNameMatch(RegExpName):
    """Rule that checks for full or partial name matches"""

    labels = [_('Text:')]
    name = _('People with first names matching <text>')
    description = _("Matches if each of person's first names is one of the names given as parameters")
    category = _('General filters')
    allow_regex = True
    base_class = RegExpName
    apply = mother_base
    

