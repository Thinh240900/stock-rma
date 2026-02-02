# Copyright 2026 Kencove (https://www.kencove.com).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "RMA Portal",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "summary": "Portal access for RMA orders",
    "author": "Kencove",
    "website": "https://github.com/ForgeFlow/stock-rma",
    "category": "RMA",
    "depends": [
        "rma",
        "rma_sale",
        "portal",
        "mrp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/rma_portal_security.xml",
        "data/rma_reason_data.xml",
        "views/res_config_settings_views.xml",
        "views/rma_reason_view.xml",
        "views/rma_order_line_view.xml",
        "views/rma_portal_templates.xml",
        "views/sale_portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "rma_portal/static/src/scss/rma_portal.scss",
            "rma_portal/static/src/js/rma_portal.js",
        ],
    },
    "installable": True,
    "application": False,
}
