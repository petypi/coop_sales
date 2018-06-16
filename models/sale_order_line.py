from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    hot_list_line = fields.Boolean("Hot List Item", related="product_id.hot_list")
    bulk_order_id = fields.Many2one("bulk.orders", string="Bulk Order")
    free_product = fields.Boolean("Is Free Product", related="bulk_order_id.free_product")
    sms_include = fields.Boolean("Free Product", default=True)
    state = fields.Selection(selection_add=[("cancel", "Cancelled")])
    invoice_status = fields.Selection(selection_add=[
        ('partial_invoice', 'Partially Invoiced')
    ])

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()

        if self.product_id.id in self._context.get("free_product_ids", []):
            self.update({"price_unit": 0.0})

        return result

    @api.multi
    def write(self, vals):
        res = False
        for record in self:
            if "product_uom_qty" in vals and record.product_id:
                if record.product_id.min_sale_qty and \
                                int(vals.get("product_uom_qty", 0)) < record.product_id.min_sale_qty:
                    raise UserError(_(
                        "Product quantity for %s is less than the minimum allowed" % record.product_id.name
                    ))

                if record.product_id.max_sale_qty and \
                                int(vals.get("product_uom_qty", 0)) < record.product_id.max_sale_qty:
                    raise UserError(_(
                        "Product quantity for %s is more than the maximum allowed" % record.product_id.name
                    ))

            res = super(SaleOrderLine, self).write(vals)

        return res

    @api.multi
    def _get_display_price(self, product):
        '''
        Do validation to prevent price_list misconfigurations from affecting the sale price
        Rules:
        1. If price is 0 but sale price is not 0, use sale price
        2. If price is 50% greater or less than sale price, use sale price
        '''
        sale_price = super(SaleOrderLine, self)._get_display_price(product)
        #_logger.info('sale_price %s, product %s', sale_price, product)
        if sale_price == 0.0 and product.list_price > 0:
            sale_price = product.list_price
        #get the % difference, anything more than 50% should result in the sale price being used
        if product.list_price:
            difference = (abs(product.list_price - sale_price) / product.list_price) * 100
            #_logger.info('difference is %s', difference)
            if difference > 50.0:
                sale_price = product.list_price
        
        return sale_price