from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    portal_operation_id = fields.Many2one(
        comodel_name="rma.operation",
        string="Default Portal RMA Operation",
        domain=[("type", "=", "customer")],
        help=(
            "Default RMA operation for portal RMA requests when no "
            "product-specific operation is configured."
        ),
    )
