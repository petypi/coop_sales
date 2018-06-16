import re
import csv
import base64
from io import StringIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class WizardBulkOrdersImport(models.TransientModel):
    _name = "wizard.bulk.orders.import"

    name = fields.Char("Name")
    data_file = fields.Binary("Excel Data File", required=True)
    free_product = fields.Boolean("Free Product", default=False)
    sms_include = fields.Boolean("Sent in SMS", default=False)
    line_ids = fields.One2many("wizard.bulk.orders.line", "wiz_bulk_orders_id", "Bulk Order Lines")
    state = fields.Selection([("draft", "Draft"), ("done", "Confirmed")], "Status", readonly=True, default="draft")

    @api.multi
    def import_bulk_order_csv(self):
        for record in self:
            free_product = record.free_product
            sms_include = record.sms_include
            if record.data_file:
                file_data = base64.decodestring(record.data_file)
                reader = csv.reader(StringIO(file_data.decode("utf-8")))

            n, res = 1, []
            for row in reader:
                if row.__len__() != 3:
                    raise ValidationError(
                        "Please use the provided format and try again, on line %s" % n 
                    )
                if re.match(r"^2547\d{8}$", row[0]) is None:
                    raise ValidationError(
                        "Please use the correct phone number format %s, on line %s" % (row[0], n)
                    )

                customer_id = self.env["res.partner"].search([("phone", "=", "+%s" % row[0])], limit=1)
                product_id = self.env["product.product"].search([("default_code", "=", row[1].upper())], limit=1)

                if not customer_id.exists():
                    raise ValidationError(
                        "Customer with phone number %s, was not found, on line %s" % (row[0], n)
                    )

                if not product_id.exists():
                    raise ValidationError(
                        "Product with code %s, was not found, on line %s" % (row[1], n)
                    )

                res.append((0, 0, {
                    "customer_id": customer_id.id,
                    "product_id": product_id.id,
                    "quantity": row[2],
                    "free_product": free_product,
                    "sms_include": sms_include,
                }))
                n += 1

            self.write({"state": "done", "line_ids": res})
            return {
                "name": "Confirm Bulk Order Import",
                "type": "ir.actions.act_window",
                "context": self.env.context,
                "view_type": "form",
                "view_mode": "form",
                "res_id":record.id,
                "res_model": "wizard.bulk.orders.import",
                "nodestroy": True,
                "target": "new",
            }

    @api.multi
    def confirm_orders(self):
        for r in self.line_ids:
            self.env["bulk.orders"].create({
                "customer_id":r.customer_id.id,
                "product_id": r.product_id.id,
                "quantity": r.quantity,
                "free_product": r.free_product,
                "sms_include": r.sms_include
            })

        return {
            "type": "ir.actions.act_window_close",
        }


class WizardBulkOrdersLine(models.TransientModel):
    _name = "wizard.bulk.orders.line"

    wiz_bulk_orders_id = fields.Many2one("wizard.bulk.orders.import", "Wizard Id")
    customer_id = fields.Many2one(
        "res.partner", string="Customer", domain=[("customer", "=", True), ("is_agent", "=", False)], 
        required=True
    )
    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float(string="Quantity", required=True)
    free_product = fields.Boolean("Free Product", default=False)
    sms_include = fields.Boolean("Sent in SMS", default=False)
