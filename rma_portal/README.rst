.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
    :alt: License LGPL-3

==========
RMA Portal
==========

This module provides portal access for customers to create and manage RMA
(Return Merchandise Authorization) requests directly from the customer portal.

Features
========

* Customers can request RMAs directly from their sale order portal page
* Support for selecting return reasons from predefined options
* Ability to specify return quantities per product
* File attachment support for documenting issues (photos, documents)
* Delivery address selection and editing
* Support for kit products (shows individual components)
* RMA tracking in customer portal

Configuration
=============

**Default Portal RMA Operation:**

#. Go to *Settings > RMA*.
#. In the RMA settings, set the *Default Portal RMA Operation*.
#. This operation will be used for portal RMA requests when no product-specific
   operation is configured.

**RMA Reasons:**

The module comes with predefined RMA reasons:

* Defective
* Damaged
* Wrong Item
* Not as Described
* Changed Mind
* Other

To manage RMA reasons:

#. Go to *RMA > Configuration > RMA Reasons*.
#. Create, edit, or deactivate reasons as needed.

Usage
=====

**Customer Portal - Request an RMA:**

#. Log in to the customer portal.
#. Go to *My Account > Orders* and select a delivered sale order.
#. Click the *Request RMAs* button.
#. For each product to return:

   * Enter the quantity to return
   * Select a reason for the return
   * Optionally add a comment or attach files

#. Select or edit the delivery address for replacements.
#. Click *Submit RMA Request*.

**Customer Portal - Track RMAs:**

#. Log in to the customer portal.
#. Go to *My Account > RMA* to view all RMA requests.
#. Click on an RMA to view its details and status.

**Operation Resolution Hierarchy:**

When creating an RMA from the portal, the operation is determined in this order:

#. Product's default customer RMA operation
#. Product category's default customer RMA operation
#. System-wide default portal operation (configured in Settings > RMA)
#. First available customer operation

