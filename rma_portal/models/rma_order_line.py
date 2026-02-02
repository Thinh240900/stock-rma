# Copyright 2024 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class RmaOrderLine(models.Model):
    _inherit = "rma.order.line"

    reason_id = fields.Many2one(
        comodel_name="rma.reason",
        string="Reason",
        help="Reason for the RMA request",
    )
    kit_id = fields.Many2one(
        comodel_name="product.product",
        string="Kit",
        compute="_compute_kit_id",
        store=True,
        help="The kit product from the original stock move's sale order",
    )

    @api.depends("product_id", "reference_move_id", "reference_move_id.sale_line_id")
    def _compute_kit_id(self):
        for line in self:
            kit_product = False
            if line.reference_move_id and line.product_id:
                # Get the sale order line from the stock move
                sale_line = line.reference_move_id.sale_line_id
                if sale_line:
                    sale_product = sale_line.product_id
                    # If the sale order line product is different from RMA product,
                    # it means a kit was sold and this is a component
                    if sale_product and sale_product != line.product_id:
                        # Verify the sale product is actually a kit (has phantom BOM)
                        bom = (
                            self.env["mrp.bom"]
                            ._bom_find(
                                sale_product,
                                bom_type="phantom",
                            )
                            .get(sale_product)
                        )
                        if bom:
                            kit_product = sale_product
            line.kit_id = kit_product
