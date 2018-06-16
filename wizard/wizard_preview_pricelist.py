import re
import base64
import csv
from io import StringIO
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    @api.multi
    def pricelist_preview(self):
        #_logger.info("^^^^^^")
        for record in self:
            lines = []
            for line in record.item_ids:
                product = line.product_tmpl_id or line.product_id
                if not product:
                    continue
                price = record.with_context(uom=product.uom_id.id).get_product_price(product, 1, False)
                actual_product = product._name == 'product.template' and product or product.product_tmpl_id
                lines.append((0, 0, {'product_id': actual_product.id, 'price_unit': price}))
            _logger.info("Lines are %s"%lines)
            return {
                "name": "Preview Pricelist",
                "type": "ir.actions.act_window",
                "context": {
                    'default_name': record.name + " Preview",
                    'default_price_line_ids': lines,
                },
                "view_type": "form",
                "view_mode": "form",
                "res_model": "wizard.pricelist.preview",
                "nodestroy": True,
                "target": "new",
            }

    @api.model
    def get_customer_price(self, phone, product_code):
        res = []
        agent = self.env['res.partner'].search(['|', ('phone','=',phone), ('mobile','=',phone)])
        if not agent:
            raise ValidationError("No agent found for that number")
        product = self.env['product.product'].search(['|', ('default_code', '=', product_code),
                                                      ('old_default_code', '=', product_code)], limit =1)
        if not product:
            raise ValidationError("No product found for code %s"%product_code)
        pricelist = agent.partner_type == 'agent' and agent[0].property_product_pricelist or False
        if not pricelist:
            pricelist = agent[0].agent_id and agent[0].agent_id.property_product_pricelist or False
        if not pricelist:
            price = product[0].list_price
            return {'name': product[0].name, 'price': price}
        else:
            _logger.info("The pricelist is %s" % agent[0].property_product_pricelist.name)
            price = pricelist.with_context(uom=product[0].uom_id.id).get_product_price(product[0], 1, False)
            return {'name': product[0].name, 'price': price}




class WizardPricelistPreview(models.TransientModel):
    _name = "wizard.pricelist.preview"
    _description = "Wizard for import/changing Routing Data on Partners"

    # @api.multi
    # def get_preview_pricelist_items(self):
    #     _logger.info("Get lines for %s"%self.env.context.get('active_id', False))
    #     for record in self:
    #         lines = []
    #         if self.env.context.get('active_id', False):
    #             pricelist = self.env['product.pricelist'].browse([self.env.context['active_id']])
    #             for line in pricelist.item_ids:
    #                 product = line.product_id.product_tmpl_id
    #                 price = pricelist.with_context(uom=product.uom_id.id).get_product_price(product, 1, False)
    #                 lines.append((0, 0, {'product_id': line.product_id.id, 'price_unit': price}))
    #         record.price_line_ids = lines

    name = fields.Char("Name")
    price_line_ids = fields.One2many(
        "wizard.pricelist.line.preview", "preview_id", "Wizard Pricelist Lines", limit=200,
        #compute = 'get_preview_pricelist_items'
    )


class WizardPricelistLinePreview(models.TransientModel):
    _name = "wizard.pricelist.line.preview"

    preview_id = fields.Many2one("wizard.pricelist.preview", "Import Wizard")
    product_id = fields.Many2one("product.template", "Product")
    price_unit = fields.Float("New Price")
