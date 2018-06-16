# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.translate import _
from odoo import api, fields, models
import logging
from odoo.exceptions import UserError, ValidationError, MissingError
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    loyalty_points = fields.Float(help='The amount of Loyalty points the customer won or lost with this order')

    @api.model
    def _order_fields(self, vals):
        #order = super(SaleOrder, self)._order_fields(ui_order)
        vals['loyalty_points'] = self.loyalty_points
        return vals

    @api.multi
    def action_compute_loyality_points(self):
        loyality_program=self.env['loyalty.program'].search([],limit=1)
        if not loyality_program:
            raise UserError(_('No loyality Program is defined!!! define one please'))

        if loyality_program.pp_currency>0:
            self.loyalty_points=loyality_program.pp_currency*self.amount_total

        elif loyality_program.pp_product>0:
            order = self.env['sale.order.line'].search([('order_id', '=', self.id)])
            quantities = 0
            for order_id in order:
                quantities+=order_id.product_uom_qty
            self.loyalty_points = loyality_program.pp_product*quantities
        elif loyality_program.pp_order>0:
            self.loyalty_points = loyality_program.pp_order

        else:
            raise UserError(_('No loyality Program creteria for points is defined!!! define one please'))

        if self.loyalty_points != 0 and self.customer_id and (self.is_soc_order or self.customer_id.is_soc_customer):
            self.customer_id.loyalty_points += self.loyalty_points
            self.customer_id.write({'loyalty_points':self.customer_id.loyalty_points})
            _logger.info("awarded points:%spartner Loyality points:%s",self.customer_id.loyalty_points,self.loyalty_points)
