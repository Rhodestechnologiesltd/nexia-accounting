# -*- coding: utf-8 -*-
{
    'name': "Restrict Reset to draft v17",

    'summary': """Hides/Restrict reset to draft buttons access in account""",

    'author': "M.Umar",
    'website': "http://www.teamUp4solutions.com",
    'category': 't4s mods',
    'version': '17.0.0.1',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/x_groups.xml',
        'views/views.xml',
    ],
    'installable': True,
    'images': ['static/description/banner.gif'],
}
