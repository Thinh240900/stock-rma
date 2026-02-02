# Copyright 2024 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):
    # =====================
    # Request RMA from Sale Order
    # =====================

    @http.route(
        ["/my/orders/<int:order_id>/requestrma/submit"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_request_rma_submit(self, order_id, access_token=None, **post):
        """Handle RMA request form submission."""
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        partner = request.env.user.partner_id
        RmaOrder = request.env["rma.order"].sudo()
        RmaOrderLine = request.env["rma.order.line"].sudo()

        # Handle delivery address - check if edited
        partner_shipping_id = self._get_or_create_delivery_address(order_sudo, post)

        # Parse form data and file uploads
        rma_lines_data = self._parse_rma_form_data(post)
        file_uploads = self._parse_rma_file_uploads()

        if not rma_lines_data:
            return request.redirect(order_sudo.get_portal_url())

        # Create RMA Order (group)
        # Use the sale order's partner to match stock move partner
        rma_order = RmaOrder.create(
            {
                "partner_id": order_sudo.partner_id.id,
                "type": "customer",
                "description": _("Portal RMA Request for %s") % order_sudo.name,
            }
        )

        # Create RMA lines
        created_lines = RmaOrderLine
        line_index_map = {}  # Map to track which index created which RMA line
        for _idx, line_data in enumerate(rma_lines_data):
            if line_data.get("quantity", 0) <= 0:
                continue

            rma_line_vals = self._prepare_rma_line_vals(
                order_sudo, rma_order, line_data, partner, partner_shipping_id
            )
            if rma_line_vals:
                rma_line = RmaOrderLine.create(rma_line_vals)
                rma_line._onchange_operation_id()
                created_lines |= rma_line
                line_index_map[line_data.get("form_index")] = rma_line

        if not created_lines:
            # No lines created, delete empty RMA order
            rma_order.unlink()
            return request.redirect(order_sudo.get_portal_url())

        # Create attachments for RMA lines
        self._create_rma_attachments(file_uploads, line_index_map)

        # Submit RMA lines for approval
        for line in created_lines:
            line.action_rma_to_approve()

        return request.redirect("/my/rma")

    @http.route(
        ["/my/requestrma/<int:order_id>"], type="http", auth="public", website=True
    )
    def request_sale_rma(self, order_id, access_token=None, **kw):
        """Request RMA on a single page"""
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        if order_sudo.state in ("draft", "sent", "cancel"):
            return request.redirect("/my")
        values = {
            "sale_order": order_sudo,
            "page_name": "request_rma",
            "default_url": order_sudo.get_portal_url(),
            "token": access_token,
            "partner_id": order_sudo.partner_id.id,
        }
        if order_sudo.company_id:
            values["res_company"] = order_sudo.company_id
        return request.render("rma_portal.request_rma_single_page", values)

    def _get_or_create_delivery_address(self, order, post):
        """Get or create/update delivery address based on form data.

        If address was edited, creates or updates a sub-contact under the
        commercial partner with the edited values.
        """
        Partner = request.env["res.partner"].sudo()

        # Get selected address ID
        partner_shipping_id = post.get("partner_shipping_id")
        if partner_shipping_id:
            try:
                partner_shipping_id = int(partner_shipping_id)
            except (ValueError, TypeError):
                partner_shipping_id = order.partner_shipping_id.id
        else:
            partner_shipping_id = order.partner_shipping_id.id

        # Check if address was edited
        address_edited = post.get("address_edited") == "1"

        if not address_edited:
            return partner_shipping_id

        # Get edited values from form
        shipping_name = post.get("shipping_name", "").strip()
        post.get("shipping_company", "").strip()
        shipping_street = post.get("shipping_street", "").strip()
        shipping_street2 = post.get("shipping_street2", "").strip()
        shipping_city = post.get("shipping_city", "").strip()
        shipping_zip = post.get("shipping_zip", "").strip()
        shipping_phone = post.get("shipping_phone", "").strip()
        shipping_mobile = post.get("shipping_mobile", "").strip()
        shipping_email = post.get("shipping_email", "").strip()

        if not shipping_name:
            # Name is required, fallback to original address
            return partner_shipping_id

        # Get the original selected address
        original_address = Partner.browse(partner_shipping_id)
        commercial_partner = order.partner_id.commercial_partner_id

        # Prepare values for the delivery address
        address_vals = {
            "name": shipping_name,
            "street": shipping_street,
            "street2": shipping_street2 or False,
            "city": shipping_city or False,
            "zip": shipping_zip or False,
            "phone": shipping_phone or False,
            "mobile": shipping_mobile or False,
            "email": shipping_email or False,
            "type": "delivery",
            "parent_id": commercial_partner.id,
        }

        # Check if the original address is a sub-contact of the commercial partner
        # and if it's a delivery type - then update it
        if (
            original_address.parent_id.id == commercial_partner.id
            and original_address.type == "delivery"
        ):
            # Update existing delivery sub-contact
            original_address.write(address_vals)
            return original_address.id
        # Create a new delivery sub-contact
        new_address = Partner.create(address_vals)
        return new_address.id

    def _parse_rma_form_data(self, post):
        """Parse the form data to extract RMA line information."""
        rma_lines = []
        # Group form fields by index
        indexed_data = {}
        for key, value in post.items():
            if "-" in key:
                try:
                    index, field = key.split("-", 1)
                    index = int(index)
                    if index not in indexed_data:
                        indexed_data[index] = {}
                    indexed_data[index][field] = value
                except (ValueError, TypeError):
                    continue

        for index in sorted(indexed_data.keys()):
            data = indexed_data[index]
            try:
                quantity = float(data.get("quantity", 0))
            except (ValueError, TypeError):
                quantity = 0

            if quantity > 0:
                rma_lines.append(
                    {
                        "form_index": index,  # Track original form index for file mapping
                        "product_id": int(data.get("product_id", 0)) or False,
                        "quantity": quantity,
                        "uom_id": int(data.get("uom_id", 0)) or False,
                        "move_id": int(data.get("move_id", 0)) or False,
                        "picking_id": int(data.get("picking_id", 0)) or False,
                        "sale_line_id": int(data.get("sale_line_id", 0)) or False,
                        "operation_id": int(data.get("operation_id", 0)) or False,
                        "reason_id": int(data.get("reason_id", 0)) or False,
                        "description": data.get("description", ""),
                    }
                )
        return rma_lines

    def _parse_rma_file_uploads(self):
        """Parse file uploads from the request."""
        file_uploads = {}
        for key, files in request.httprequest.files.lists():
            if "-attachments" in key:
                try:
                    index = int(key.split("-")[0])
                    file_uploads[index] = files
                except (ValueError, TypeError):
                    continue
        return file_uploads

    def _create_rma_attachments(self, file_uploads, line_index_map):
        """Create ir.attachment records for uploaded files."""
        Attachment = request.env["ir.attachment"].sudo()

        for form_index, files in file_uploads.items():
            rma_line = line_index_map.get(form_index)
            if not rma_line:
                continue

            for file_storage in files:
                if not file_storage.filename:
                    continue

                # Read file content
                file_content = file_storage.read()
                if not file_content:
                    continue

                # Create attachment
                Attachment.create(
                    {
                        "name": file_storage.filename,
                        "datas": base64.b64encode(file_content),
                        "res_model": "rma.order.line",
                        "res_id": rma_line.id,
                        "type": "binary",
                    }
                )

    def _prepare_rma_line_vals(
        self, order, rma_order, line_data, partner, partner_shipping_id=None
    ):
        """Prepare values for creating an RMA line."""
        product_id = line_data.get("product_id")
        if not product_id:
            return False

        product = request.env["product.product"].sudo().browse(product_id)
        operation_id = line_data.get("operation_id")

        # Get operation
        if operation_id:
            operation = request.env["rma.operation"].sudo().browse(operation_id)
        else:
            operation = (
                product.rma_customer_operation_id
                or product.categ_id.rma_customer_operation_id
            )
            # Use the default portal operation from company settings
            if not operation:
                operation = order.company_id.portal_operation_id
            if not operation:
                operation = (
                    request.env["rma.operation"]
                    .sudo()
                    .search(
                        [
                            ("type", "=", "customer"),
                        ],
                        limit=1,
                    )
                )

        if not operation:
            return False

        # Get warehouse and location
        warehouse = operation.in_warehouse_id
        if not warehouse:
            warehouse = (
                request.env["stock.warehouse"]
                .sudo()
                .search(
                    [
                        ("company_id", "=", order.company_id.id),
                        ("lot_rma_id", "!=", False),
                    ],
                    limit=1,
                )
            )

        location = (
            operation.location_id
            or operation.in_warehouse_id.lot_rma_id
            or warehouse.lot_rma_id
        )

        # Get route
        route = operation.in_route_id
        if not route:
            route = (
                request.env["stock.route"]
                .sudo()
                .search(
                    [
                        ("rma_selectable", "=", True),
                    ],
                    limit=1,
                )
            )

        move_id = line_data.get("move_id")
        sale_line_id = line_data.get("sale_line_id")

        # Use selected delivery address or fallback to order's shipping address
        delivery_address_id = partner_shipping_id or order.partner_shipping_id.id

        # Use the sale order's partner for RMA to match the stock move's partner
        # This avoids "RMA customer and originating stock move customer doesn't match" error
        rma_partner = order.partner_id

        vals = {
            "rma_id": rma_order.id,
            "partner_id": rma_partner.id,
            "product_id": product_id,
            "product_qty": line_data.get("quantity", 0),
            "uom_id": line_data.get("uom_id") or product.uom_id.id,
            "operation_id": operation.id,
            "origin": _("Portal: %s") % order.name,
            "delivery_address_id": delivery_address_id,
            "receipt_policy": operation.receipt_policy,
            "delivery_policy": operation.delivery_policy,
            "in_warehouse_id": warehouse.id if warehouse else False,
            "out_warehouse_id": warehouse.id if warehouse else False,
            "in_route_id": route.id if route else False,
            "out_route_id": operation.out_route_id.id
            if operation.out_route_id
            else (route.id if route else False),
            "location_id": location.id if location else False,
            "description": line_data.get("description", ""),
        }

        if move_id:
            vals["reference_move_id"] = move_id

        if sale_line_id:
            vals["sale_line_id"] = sale_line_id

        reason_id = line_data.get("reason_id")
        if reason_id:
            vals["reason_id"] = reason_id

        return vals
