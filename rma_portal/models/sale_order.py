# Copyright 2024 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_portal_rma_data(self):
        """Get data for portal RMA request form.

        For kit products (phantom BOM), shows the component products.
        For normal products, shows the product itself.
        Always shows items even if returnable quantity is 0.
        """
        self.ensure_one()
        data = []
        for line in self.order_line:
            line_data_list = line._prepare_portal_rma_data()
            if line_data_list:
                data.extend(line_data_list)
        return data


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_delivered_moves(self):
        """Get stock moves that delivered products to customer."""
        self.ensure_one()
        return self.move_ids.filtered(
            lambda m: (
                m.state == "done"
                and not m.scrapped
                and m.location_dest_id.usage == "customer"
                and (
                    not m.origin_returned_move_id
                    or (m.origin_returned_move_id and m.to_refund)
                )
            )
        )

    def _is_kit_product(self):
        """Check if the sale line product is a kit (phantom BOM)."""
        self.ensure_one()
        bom = (
            self.env["mrp.bom"]
            ._bom_find(
                self.product_id,
                bom_type="phantom",
            )
            .get(self.product_id)
        )
        return bool(bom)

    def _get_existing_rma_qty_for_product(self, product_id):
        """Get quantity already in RMA for a specific product from this sale line."""
        self.ensure_one()
        return sum(
            self.env["rma.order.line"]
            .sudo()
            .search(
                [
                    ("sale_line_id", "=", self.id),
                    ("product_id", "=", product_id),
                    ("state", "not in", ["canceled"]),
                ]
            )
            .mapped("product_qty")
        )

    def _prepare_portal_rma_data(self):
        """Prepare RMA data for portal form.

        For kit products, returns a list of component products from stock moves.
        For normal products, returns a list with the product itself.
        Always returns data even if returnable quantity is 0.
        """
        self.ensure_one()
        if self.product_id.type not in ("product", "consu"):
            return []

        moves = self._get_delivered_moves()
        if not moves:
            # No delivered moves, check if it's a service or not delivered yet
            if self.qty_delivered <= 0:
                return []

        # Check if this is a kit product
        is_kit = self._is_kit_product()

        if is_kit and moves:
            # For kit products, show each component from stock moves
            return self._prepare_kit_components_data(moves)
        # For normal products, show the product itself
        return self._prepare_single_product_data(moves)

    def _prepare_kit_components_data(self, moves):
        """Prepare RMA data for kit component products."""
        data_list = []
        # Group moves by product to handle multiple moves of same product
        product_moves = {}
        for move in moves:
            if move.product_id.id not in product_moves:
                product_moves[move.product_id.id] = {
                    "product": move.product_id,
                    "moves": self.env["stock.move"],
                    "delivered_qty": 0,
                }
            product_moves[move.product_id.id]["moves"] |= move
            product_moves[move.product_id.id]["delivered_qty"] += move.quantity_done

        for product_id, product_data in product_moves.items():
            product = product_data["product"]
            delivered_qty = product_data["delivered_qty"]
            first_move = product_data["moves"][0]

            # Get existing RMA qty for this specific product
            returned_qty = self._get_existing_rma_qty_for_product(product_id)
            returnable_qty = max(0, delivered_qty - returned_qty)

            data_list.append(
                {
                    "product": product,
                    "quantity": returnable_qty,
                    "delivered_qty": delivered_qty,
                    "returned_qty": returned_qty,
                    "uom": product.uom_id,
                    "picking": first_move.picking_id,
                    "move": first_move,
                    "sale_line": self,
                    "is_kit_component": True,
                    "kit_product": self.product_id,
                }
            )

        return data_list

    def _prepare_single_product_data(self, moves):
        """Prepare RMA data for a single (non-kit) product."""
        delivered_qty = self.qty_delivered
        returned_qty = self._get_existing_rma_qty_for_product(self.product_id.id)
        returnable_qty = max(0, delivered_qty - returned_qty)

        picking = moves[0].picking_id if moves else False
        first_move = moves[0] if moves else False

        return [
            {
                "product": self.product_id,
                "quantity": returnable_qty,
                "delivered_qty": delivered_qty,
                "returned_qty": returned_qty,
                "uom": self.product_uom,
                "picking": picking,
                "move": first_move,
                "sale_line": self,
                "is_kit_component": False,
                "kit_product": False,
            }
        ]
