from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id = "AddSourcesGramplet",
         name = _("AddSourcesGramplet"),
         description = _("Gramplet to add sources"),
         status = STABLE,
         version = '0.9.8',
         gramps_target_version = major_version,
         fname = "AddSourcesGramplet.py",
         gramplet = 'AddSourcesGramplet',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("AddSourcesGramplet"),
         help_url="Addon:Isotammi_addons#Add_Sources_Gramplet",
         include_in_listing = True,
         navtypes=["Event"],
         **additional_args,
        )
