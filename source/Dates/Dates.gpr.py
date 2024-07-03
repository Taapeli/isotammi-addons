from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id = "Dates",
         name = _("Dates"),
         description = _("Dates"),
         status = STABLE,
         version = '1.1.7',
         gramps_target_version = major_version,
         fname = "Dates.py",
         gramplet = 'Dates',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("Dates"),
         help_url="Dates gramplet",
         include_in_listing = True,
         navtypes=["Event"],
         **additional_args,
        )
