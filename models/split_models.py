from odoo import models, api, fields
import copy
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class SplitList(models.Model):
    '''
    Shows which category products should be split when the weight is over a
     certain amount in an order
    '''
    _name = 'split.list'
    _description = "Category Split"
    name = fields.Char(string='Name', help='The name of the list', required=True)
    max_weight = fields.Float(help='Weight at which order should be split if it is exceeded',\
    required=True, string="Max Weight")
    category_ids = fields.Many2many('product.category', 'split_list_category', 'split_list_id', \
    'category_id', string='Categories', ondelete='cascade', required=True, \
    help='The product categories this list applies to')

    @api.model
    def create(self, vals):
        existing_lists = self.search_count([])
        _logger.info('existing_lists is %s', existing_lists)
        if existing_lists:
            raise ValidationError('Only one list is allowed. You can add categories to this list')
        return super(SplitList, self).create(vals)

class ProductSplit(models.Model):
    '''
    Shows which products should be split
    '''
    _name = 'product.split'
    _description = "Product Split"
    _sql_constraints = [
        ('product_unique', 'UNIQUE(product_id)', 'Each product can only have one rule'),
    ]

    product_id = fields.Many2one('product.product', ondelete='cascade', required=True, \
    string="Product")
    quantity = fields.Float(help='Quantity at which order should be split if it is exceeded',\
    default=0, required=True, string="Quantity")