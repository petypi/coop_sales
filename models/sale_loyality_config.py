# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    config_sale_order_loyalty = fields.Boolean(string='Loyalty Program', widget='upgrade_boolean')
    loyalty_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The loyalty program currently used by the system.')


    @api.onchange('config_sale_order_loyalty')
    def _onchange_module_sale_loyalty(self):
        if self.config_sale_order_loyalty:
            self.loyalty_id = self.env['loyalty.program'].search([], limit=1)
        else:
            self.loyalty_id = False
