{
    'name': 'Mass Delete Records',
    'version': '17.0.1.0.0',
    'summary': 'Manage and clean your Odoo database effectively. This Mass delete records Odoo app allows you to selectively delete outdated or unnecessary records from sales, purchases, inventory, and other modules. Enhance data accuracy and optimize system performance.',
    'description': """
        The Mass Clean and Delete Data module provides a user-friendly wizard interface for managing large datasets within Odoo. 
        It allows users to easily remove outdated or unnecessary records from various modules, including sales, purchases, inventory, 
        and invoicing. With options to clean all data with a single click or target specific records, this module enhances data accuracy 
        and optimizes system performance.
    """,
    "author": "Zehntech Technologies Inc.",
    "company": "Zehntech Technologies Inc.",
    "maintainer": "Zehntech Technologies Inc.",
    "contributor": "Zehntech Technologies Inc.",
    "website": "https://www.zehntech.com/",
    "support": "odoo-support@zehntech.com",
    "live_test_url": "https://odoo16.zehntech.net/app_name=zehntech_mass_delete_records/app_version=17.0",
    'category': 'Productivity',
    'depends': [ 'sale_management', 'purchase', 'project', 'mrp', 'account', 'stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        
        # 'security/access_control.xml',
        'views/clean_menu.xml',
        'views/confirm_deletion_wizard_views.xml',
        'views/clean_wizard_view.xml',
        'views/purchase_wizard.xml',
        'views/confirmation_wizard.xml',
        'views/summary_view.xml',
        'views/manufacture_views.xml',
        'views/audit_log.xml',
        'views/all_delete.xml',
        'views/audit_views.xml',

    ],
     'i18n': [
            'i18n/es.po',#spanish translation file
            'i18n/de.po',#german translation file
            'i18n/fr.po',#french translation file
            'i18n/ja_JP.po',#japanese translation file
    ],
    'assets': {
        'web.assets_backend': [

        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 0.00,
    'currency': 'USD',
}
