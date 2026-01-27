from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    portal_operation_id = fields.Many2one(
        comodel_name="rma.operation",
        related="company_id.portal_operation_id",
        readonly=False,
        string="Default Portal RMA Operation",
        domain=[("type", "=", "customer")],
    )
