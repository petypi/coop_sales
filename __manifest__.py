# -- coding: utf-8 --
{
    "name": "Copia Sale",
    "summary": """Copia's customisations for Sales""",
    "description": """
Copia Customization of Sales Module
========================================
Include provisions under the following:

* SMS Messaging via RabbitMQ, through AfricasTalking's API
Provides Inbox and Outbox facilities and tracking the same on the ERP via the model sms.message.

* Sale Order Order and Delivery Timelines
Facilitates the following:
* Recalculation of the Sale Order's Order Date
* Recalculation of the Sale Order's Delivery Date based on:
   * The Sale Order's Order Date
   * Sale Order Line's Product's SLA Days
   * Sale Order Line's Product's Customer Lead Time
""",
    "author": "Rono, Darwesh & Muratha",
    "website": "http://www.copiaglobal.com/",
    "category": "sale",
    "version": "0.1",
    "depends": [
        "base", "sale_management", "sales_team", "delivery",
        "copia_product", "copia_keywords", "copia_partner"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_view.xml",
        "views/sms_message_view.xml",
        "views/bulk_order_view.xml",
        "views/sale_holiday_view.xml",
        "views/split_order_view.xml",
        "data/ir_sequence_type.xml",
        "wizard/wizard_send_sms_message_view.xml",
        "wizard/wizard_bulk_order_import_view.xml",
        "wizard/wizard_reply_sms_view.xml",
        "wizard/wizard_create_holiday.xml",
        "data/sale_configuration.yml",
        # "data/sale_configuration.xml",
        "wizard/wizard_preview_pricelist_view.xml",
    ],
    "demo": [
    ],
}
