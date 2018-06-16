from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger("Promo (Bulk) Order")


class BulkOrders(models.Model):
    _name = "bulk.orders"

    @api.multi
    @api.depends("product_id.default_code", "product_id.name", "customer_id.name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "{} : {}".format(
                record.customer_id.name, record.product_id.id and record.product_id.name_get()[0][1] or "-"
            )

    customer_id = fields.Many2one(
        "res.partner", string="Customer", domain=[("customer", "=", True), ("is_agent", "=", False)],
        required=True
    )
    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float(string="Quantity", required=True)
    active = fields.Boolean(string="Active", default=True)
    used = fields.Boolean(string="Used", default=False)
    free_product = fields.Boolean(string="Free", default=False)
    sms_include = fields.Boolean(
        string="Sent in SMS", default=False,
        help="Whether the Order Line for this product is included in the Order SMS"
    )

    @api.constrains("customer_id", "product_id")
    def _check_duplicate(self):
        _dupl = self.search([
            ("customer_id", "=", self.customer_id.id), ("product_id", "=", self.product_id.id),
            ("used", "=", False), ("active", "=", True), ("id", "!=", self.id)
        ])

        if _dupl.exists():
            raise ValidationError(
                _("Duplicate. An entry already exists for %s, for product %s for a quantity of %s Unit(s)" %
                (_dupl.customer_id.name, _dupl.product_id.name, _dupl.quantity))
            )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        # Add promotion (bulk_orders) lines into the Sale Order
        free_product_ids = []
        if vals.get("customer_id", False) and vals.get("order_line", False):
            _promo_bulk = self.env["bulk.orders"].search([
                ("customer_id", "=", vals.get("customer_id")),
                ("used", "=", False), ("active", "=", True)
            ])

            try:
                for i in _promo_bulk:
                    # TODO - we assume that they are ordering Unit(s)
                    uom = self.env.ref("product.product_uom_unit")
                    price_unit = 0.0
                    if i.free_product == False:
                        price_unit = i.product_id.list_price
                    vals["order_line"].append([0, 0, {
                        "name": i.product_id.name_get()[0][1],
                        "product_id": i.product_id.id,
                        "product_uom_qty": i.quantity,
                        "product_uom": uom.id,
                        "bulk_order_id": i.id,
                        "price_unit": price_unit,
                        "sms_include": i.sms_include
                    }])

                    if i.free_product:
                        free_product_ids.append(i.product_id.id)

                    i.write({"used": True})
            except Exception as e:
                _logger.error("{}".format(e.__str__()))
                raise UserError(_(
                    "Exception occurred on Bulk Order inclusion into Order Line."
                ))

        return super(SaleOrder, self.with_context(free_product_ids=free_product_ids)).create(vals)
