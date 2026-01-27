/** @odoo-module **/

import publicWidget from "web.public.widget";

publicWidget.registry.PortalHomeCounters.include({
    /**
     * @override
     */
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat(["rma_count"]);
    },
});

/**
 * Widget for RMA Request Form - handles delivery address selection, file uploads, and validation
 */
publicWidget.registry.RmaRequestForm = publicWidget.Widget.extend({
    selector: "#form-request-rma",
    events: {
        "click .o_rma_portal_shipping_card": "_onClickShippingCard",
        "change .rma-file-input": "_onFileChange",
        "change .address-field": "_onAddressFieldChange",
        "input .address-field": "_onAddressFieldChange",
        submit: "_onFormSubmit",
    },

    /**
     * @override
     */
    start() {
        this._removeExistingAlerts();
        this._originalAddressData = this._getCurrentAddressData();
        return this._super(...arguments);
    },

    /**
     * Remove any existing validation alerts
     */
    _removeExistingAlerts() {
        this.$(".rma-validation-alert").remove();
    },

    /**
     * Get current address data from form
     */
    _getCurrentAddressData() {
        return {
            name: this.$("#shipping_name").val() || "",
            company: this.$("#shipping_company").val() || "",
            street: this.$("#shipping_street").val() || "",
            street2: this.$("#shipping_street2").val() || "",
            city: this.$("#shipping_city").val() || "",
            zip: this.$("#shipping_zip").val() || "",
            phone: this.$("#shipping_phone").val() || "",
            mobile: this.$("#shipping_mobile").val() || "",
            email: this.$("#shipping_email").val() || "",
        };
    },

    /**
     * Check if address has been edited
     */
    _checkAddressEdited() {
        const current = this._getCurrentAddressData();
        const original = this._originalAddressData;

        const edited =
            current.name !== original.name ||
            current.company !== original.company ||
            current.street !== original.street ||
            current.street2 !== original.street2 ||
            current.city !== original.city ||
            current.zip !== original.zip ||
            current.phone !== original.phone ||
            current.mobile !== original.mobile ||
            current.email !== original.email;

        this.$("#address_edited").val(edited ? "1" : "0");
        return edited;
    },

    /**
     * Handle address field change
     */
    _onAddressFieldChange() {
        this._checkAddressEdited();
    },

    /**
     * Handle click on shipping address card
     * @param {Event} ev
     */
    _onClickShippingCard(ev) {
        const $card = $(ev.currentTarget);
        const $allCards = this.$(".o_rma_portal_shipping_card");

        // Remove selection from all cards (reset styles)
        $allCards.removeClass("selected");
        $allCards.css({
            "border-color": "#dee2e6",
            "background-color": "",
        });
        $allCards.find(".selected-indicator").css("display", "none");

        // Select the clicked card (apply selected styles)
        $card.addClass("selected");
        $card.css({
            "border-color": "#007bff",
            "background-color": "rgba(0, 123, 255, 0.05)",
        });
        $card.find(".selected-indicator").css("display", "block");

        // Get address data from card
        const addressId = $card.data("address-id");
        const addressData = {
            name: $card.data("name") || "",
            company: $card.data("company") || "",
            street: $card.data("street") || "",
            street2: $card.data("street2") || "",
            city: $card.data("city") || "",
            zip: $card.data("zip") || "",
            phone: $card.data("phone") || "",
            mobile: $card.data("mobile") || "",
            email: $card.data("email") || "",
        };

        // Update hidden field with selected address ID
        this.$("#selected_address_id").val(addressId);

        // Populate edit form
        this.$("#shipping_name").val(addressData.name);
        this.$("#shipping_company").val(addressData.company);
        this.$("#shipping_street").val(addressData.street);
        this.$("#shipping_street2").val(addressData.street2);
        this.$("#shipping_city").val(addressData.city);
        this.$("#shipping_zip").val(addressData.zip);
        this.$("#shipping_phone").val(addressData.phone);
        this.$("#shipping_mobile").val(addressData.mobile);
        this.$("#shipping_email").val(addressData.email);

        // Update original data to track edits from this selection
        this._originalAddressData = this._getCurrentAddressData();
        this.$("#address_edited").val("0");
    },

    /**
     * Handle file input change - show file count
     * @param {Event} ev
     */
    _onFileChange(ev) {
        const $input = $(ev.currentTarget);
        const inputId = $input.attr("id");
        const index = inputId.replace("file-", "");
        const $countSpan = this.$("#file-count-" + index);
        const files = ev.currentTarget.files;

        if (files && files.length > 0) {
            const text =
                files.length === 1
                    ? "1 file selected"
                    : files.length + " files selected";
            $countSpan.text(text).addClass("text-success").removeClass("text-muted");
        } else {
            $countSpan.text("").removeClass("text-success");
        }
    },

    /**
     * Validate form before submission
     * @param {Event} ev
     */
    _onFormSubmit(ev) {
        this._removeExistingAlerts();
        this._clearValidationStyles();

        const errors = [];
        const $rows = this.$("tbody.request-rma-tbody tr:not(.collapse)");
        let hasAtLeastOneItem = false;

        $rows.each((index, row) => {
            const $row = $(row);
            const $qtyInput = $row.find("input[type='number']");
            const $reasonSelect = $row.find("select.rma-reason");

            // Skip rows without quantity input (qty = 0 rows)
            if ($qtyInput.length === 0) {
                return;
            }

            const qty = parseFloat($qtyInput.val()) || 0;
            const maxQty = parseFloat($qtyInput.attr("max")) || 0;
            const reasonId = $reasonSelect.val();

            if (qty > 0) {
                hasAtLeastOneItem = true;

                // Validate quantity doesn't exceed max
                if (qty > maxQty) {
                    const productName = $row
                        .find("td:first span")
                        .first()
                        .text()
                        .trim();
                    errors.push(
                        `"${productName}": Quantity (${qty}) exceeds available quantity (${maxQty})`
                    );
                    $qtyInput.addClass("is-invalid");
                }

                // Validate reason is selected
                if (!reasonId) {
                    const productName = $row
                        .find("td:first span")
                        .first()
                        .text()
                        .trim();
                    errors.push(`"${productName}": Please select a reason`);
                    $reasonSelect.addClass("is-invalid");
                }
            }
        });

        // Check if at least one item is selected
        if (!hasAtLeastOneItem) {
            errors.unshift("Please enter a quantity for at least one product");
        }

        if (errors.length > 0) {
            ev.preventDefault();
            ev.stopPropagation();
            this._showValidationErrors(errors);
            return false;
        }

        return true;
    },

    /**
     * Clear validation styles from all inputs
     */
    _clearValidationStyles() {
        this.$(".is-invalid").removeClass("is-invalid");
    },

    /**
     * Show validation errors as an alert
     * @param {Array} errors
     */
    _showValidationErrors(errors) {
        const $alert = $("<div>", {
            class: "alert alert-danger rma-validation-alert mt-2",
            role: "alert",
        });

        const $title = $("<strong>").text("Please correct the following errors:");
        const $list = $("<ul>", {class: "mb-0 mt-2"});

        errors.forEach((error) => {
            $list.append($("<li>").text(error));
        });

        $alert.append($title).append($list);

        // Insert alert after the info alert
        this.$(".alert-info").after($alert);

        // Scroll to the alert
        $alert[0].scrollIntoView({behavior: "smooth", block: "center"});
    },
});
