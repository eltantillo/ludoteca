# -*- coding: utf-8 -*-
{
    'name': "Rental",

    'summary': "Manage rental contracts, deliveries and returns",

    'description': """
        Specify rentals of products (products, quotations, invoices, ...)
        Manage status of products, rentals, delays
        Manage user and manager notifications
    """,

    'website': "https://www.odoo.com/app/rental",

    'category': 'Sales/Sales',
    'sequence': 160,
    'version': '1.0',

    'depends': ['sale_temporal'],

    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        'data/rental_data.xml',

        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',

        'report/rental_order_report_templates.xml',
        'report/rental_report_views.xml',
        'report/rental_schedule_views.xml',

        'wizard/rental_configurator_views.xml',
        'wizard/rental_defect_views.xml',
        'wizard/rental_processing_views.xml',
        'wizard/sale_confirmation.xml',

        'views/sale_renting_menus.xml',
    ],
    'demo': [
        'data/rental_demo.xml',
    ],
    'application': True,
    'pre_init_hook': '_pre_init_rental',
    'assets': {
        'web.assets_backend': [
            'sale_renting/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}
