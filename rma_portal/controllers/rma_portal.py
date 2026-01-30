# Copyright 2024 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).


import base64

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class RMAPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        RmaOrderLine = request.env["rma.order.line"]
        if "rma_count" in counters:
            rma_count = (
                RmaOrderLine.search_count(self._get_rma_domain(partner))
                if RmaOrderLine.check_access_rights("read", raise_exception=False)
                else 0
            )
            values["rma_count"] = rma_count

        return values

    def _is_rma_admin(self):
        """Check if current user is an RMA admin (internal user with RMA access)."""
        user = request.env.user
        return user.has_group("base.group_user") and user.has_group(
            "rma.group_rma_customer_user"
        )

    def _get_rma_domain(self, partner):
        """Get domain for RMA search.

        Admin users (internal users with RMA access) can see all customer RMAs.
        Portal users can only see their own RMAs.
        """
        domain = [("type", "=", "customer")]

        # If user is admin, show all RMAs
        if not self._is_rma_admin():
            # Portal user - only show their own RMAs
            domain.append(("partner_id", "child_of", partner.commercial_partner_id.id))

        return domain

    def _rma_get_page_view_values(self, rma, access_token, **kwargs):
        values = {
            "page_name": "rma",
            "rma": rma,
        }
        return self._get_page_view_values(
            rma, access_token, values, "my_rma_history", False, **kwargs
        )

    def _get_rma_searchbar_sortings(self):
        sortings = {
            "date": {"label": _("Date"), "order": "date_rma desc"},
            "name": {"label": _("Reference"), "order": "name"},
            "state": {"label": _("Status"), "order": "state"},
        }
        # Add customer sorting for admin users
        if self._is_rma_admin():
            sortings["customer"] = {"label": _("Customer"), "order": "partner_id"}
        return sortings

    @http.route(
        ["/my/rma", "/my/rma/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_rma(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        RmaOrderLine = request.env["rma.order.line"]

        domain = self._get_rma_domain(partner)

        searchbar_sortings = self._get_rma_searchbar_sortings()

        # default sort
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # date filter
        if date_begin and date_end:
            domain += [
                ("date_rma", ">", date_begin),
                ("date_rma", "<=", date_end),
            ]

        # count for pager
        rma_count = RmaOrderLine.search_count(domain)

        # pager
        pager = portal_pager(
            url="/my/rma",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=rma_count,
            page=page,
            step=self._items_per_page,
        )

        # content according to pager and target order
        rma_lines = RmaOrderLine.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )
        request.session["my_rma_history"] = rma_lines.ids[:100]

        values.update(
            {
                "date": date_begin,
                "rma_lines": rma_lines.sudo(),
                "page_name": "rma",
                "is_rma_admin": self._is_rma_admin(),
                "pager": pager,
                "default_url": "/my/rma",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("rma_portal.portal_my_rma", values)

    @http.route(["/my/rma/<int:rma_id>"], type="http", auth="public", website=True)
    def portal_my_rma_detail(
        self, rma_id, access_token=None, report_type=None, download=False, **kw
    ):
        try:
            rma_sudo = self._document_check_access(
                "rma.order.line", rma_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=rma_sudo,
                report_type=report_type,
                report_ref="rma.report_rma_action",
                download=download,
            )

        values = self._rma_get_page_view_values(rma_sudo, access_token, **kw)
        return request.render("rma_portal.portal_rma_page", values)

    @http.route(
        ["/my/rma/<int:rma_id>/attachment/<int:attachment_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_rma_attachment_download(self, rma_id, attachment_id, **kw):
        """Download attachment for an RMA order line."""
        try:
            self._document_check_access("rma.order.line", rma_id, None)
        except (AccessError, MissingError):
            return request.redirect("/my")

        # Check if attachment belongs to this RMA
        attachment = (
            request.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("id", "=", attachment_id),
                    ("res_model", "=", "rma.order.line"),
                    ("res_id", "=", rma_id),
                ],
                limit=1,
            )
        )
        if not attachment:
            return request.redirect(f"/my/rma/{rma_id}")

        # Return the file for download
        content_disposition = 'attachment; filename="%s"' % attachment.name
        return request.make_response(
            base64.b64decode(attachment.datas),
            headers=[
                ("Content-Type", attachment.mimetype or "application/octet-stream"),
                ("Content-Disposition", content_disposition),
            ],
        )
