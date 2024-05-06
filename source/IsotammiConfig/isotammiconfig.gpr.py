from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id = "isotammiconfig",
         name = _("Isotammi configuration"),
         description = _("Isotammi configuration"),
         status = STABLE,
         version = '1.1.5',
         gramps_target_version =  major_version,
         fname = "isotammiconfig.py",
         gramplet = 'IsotammiConfig',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("Isotammi configuration"),
         help_url="",
         include_in_listing = True,
         navtypes=["Dashboard"],
         **additional_args,
        )
