# Copyright 2024 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class RmaReason(models.Model):
    _name = "rma.reason"
    _description = "RMA Reason"
    _order = "sequence, id"

    name = fields.Char(string="Reason", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
