# -*- coding: utf-8 -*-
import re
import copy
import datetime
import logging
from pytz import timezone
from itertools import groupby
from json import dumps
from dateutil.parser import parse
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # TODO: For testing purposes only
    @api.model
    def _get_date_order_2(self, order_date=None):
        """
        Calculates Order Date based on today() through these constraints
        if sunday order date ==  saturday
        """
        today = datetime.datetime.strptime(
            order_date or datetime.date.today().__str__(), "%Y-%m-%d"
        ).replace(
            tzinfo=timezone("UTC")
        ).astimezone(timezone("Africa/Nairobi"))

        if today.weekday() == 6:
            today = today - datetime.timedelta(days=1)

        return today.__str__()

    def _get_date_order(self):
        """
        if sunday order date ==  saturday
        :return: String value of the calculated Order Date
        """
        today = datetime.datetime.now(timezone("UTC")).astimezone(timezone("Africa/Nairobi"))
        if today.weekday() == 6:
            today = today - datetime.timedelta(days=1)

        return today.replace(hour=0, minute=0, second=0, microsecond=0)

    def _get_delivery_date(self, date_order, partner, t_delay):
        """
        Calculates fore-casted Delivery Date based on Order Date

        :param date_order: String value of the Order Date
        :return: datetime.date() Object value of the Calculated Delivery Date
        """
        date_order = date_order if isinstance(date_order, datetime.datetime) else parse(date_order)
        _logger.info('t_delay in _get_delivery_date is %s' % t_delay)
        # count the holidays, we go one month in advance to minimize db calls
        holidays = self.env['sale.holiday'].search_holidays(date_order + datetime.timedelta(days=1), date_order + \
                                                            datetime.timedelta(days=t_delay))
        if len(holidays):
            t_delay += len(holidays)
        # add the delay while checking that the date of delivery is not on a holiday
        on_holiday = True
        while on_holiday:
            date_delivery = (date_order + datetime.timedelta(days=t_delay)).date()
            _logger.info('date_delivery: %s' % date_delivery)
            if len(self.env['sale.holiday'].search_holidays(date_delivery, date_delivery)):
                t_delay += 1
            else:
                on_holiday = False
        return date_delivery

    def _get_mode(self):
        result = []
        channels = self.env['sms.message.channel'].search_read([], ['name'])
        for k in channels:
            name = k.get('name')
            result.append((re.sub("\s+", "_", name.lower()), name))
        return result

    partner_id = fields.Many2one("res.partner", string="Agent", readonly=True,
                                 states={
                                     "draft": [("readonly", False)], "sent": [("readonly", False)]
                                 }, required=True, change_default=True, index=True, track_visibility="always")
    customer_id = fields.Many2one("res.partner", string="Customer", readonly=True, required=True,
                                  states={
                                      "draft": [("readonly", False)], "sent": [("readonly", False)]
                                  }, index=True)
    date_order = fields.Datetime("Order Date", index=True, readonly=True, copy=False, default=_get_date_order)
    date_delivery = fields.Date("Forecasted Delivery Date", readonly=True, index=True)
    islayaway = fields.Boolean("Layaway Order")
    is_duplicate = fields.Boolean("Possible Duplicate")

    remote_shopping = fields.Boolean(string='Remote Shopping', default=False)
    remote_customer_id = fields.Many2one('res.partner', string='Delivery Customer', domain=[('customer', '=', True)])
    mode = fields.Selection(_get_mode, "Creation Mode", help="From which channel was this order created?",
                            default="erp", store=True)
    split_ref = fields.Char("Split Order Ref")
    related_orders = fields.Many2many("sale.order", string="Related orders",
                                      help="Orders that were created at the same time as this order due to splitting",
                                      compute="_get_related_orders")
    fake_hot_list = fields.Boolean("Hot List Order", compute="_compute_fake_hot_list")
    hot_list = fields.Boolean("Hot List", compute="_compute_hot_list", store=True)
    sale_type_id = fields.Many2one(
        "product.category.sale.type", string="Sale Type"
    )
    state = fields.Selection(selection_add=[
        ("rejected", "Rejected"),
        ("partner_shipping_required", "RA Required"),
        ("payment_required", "Payment Required")
    ])
    reject_reason = fields.Selection(
        [
            ("qty_exception", "Invalid Quantity"),
            ("stock_exception", "Maximum Sale Quantity Exceeded"),
            ("out_of_stock", "Out of stock"),
            ("quota_exceeded_exception", "Quota Exceeded"),
        ], "Reject Reason"
    )
    sale_associate_id = fields.Many2one("res.partner", string="Sale Associate")
    route_types = [('normal', 'Normal'), ('special', 'Special')]
    route_type = fields.Selection(
        route_types, "Route Type",
        help="Route type: Normal for normal orders or special for special orders e.g. Building/Construction",
        default="normal"
    )
    invoice_status = fields.Selection(selection_add=[
        ('partial_invoice', 'Partially Invoiced'),
    ])

    @api.onchange('remote_shopping')
    def onchange_remote_shopping(self):
        '''
        This method populates the address to the remote agent going to receive the products
        :return:
        '''
        if self['remote_shopping']:
            self.partner_shipping_id = None
        else:
            self.partner_shipping_id = self.partner_id

    @api.onchange('customer_id')
    def onchange_customer_id(self):
        '''
        This method populates the address to the remote agent going to receive the products
        :return:
        '''
        if self['remote_shopping']:
            self.partner_shipping_id = self.customer_id.agent_id

    @api.onchange('remote_customer_id')
    def onchange_remote_customer_id(self):
        '''
        This method populates the address to the remote agent going to receive the products
        :return:
        '''
        if self['remote_shopping']:
            self.partner_shipping_id = self.remote_customer_id.agent_id

    @api.one
    @api.depends("order_line.hot_list_line")
    def _compute_fake_hot_list(self):
        if self.order_line.filtered(lambda line: line.hot_list_line is True):
            self.fake_hot_list = True
        else:
            self.fake_hot_list = False
        #self.write({"hot_list": self.hot_list})

        # Force a recompute of hot_list
        # Skip NewId instances
        if isinstance(self.id, models.NewId):
            pass
        else:
            self.env.add_todo(self._fields['hot_list'], self.search([("id", "=", self.id)]))
            self.recompute()

    @api.one
    @api.depends("order_line.hot_list_line")
    def _compute_hot_list(self):
        if self.order_line.filtered(lambda line: line.hot_list_line is True):
            self.hot_list = True
        else:
            self.hot_list = False

    @api.model
    def _get_related_orders(self):
        for record in self:
            if record.split_ref:
                record.related_orders = self.search([("split_ref", "=", record.split_ref), ("id", "<>", record.id)])
            else:
                record.related_orders = []

    @api.model
    def _get_product_delay(self, product_uom_qty, product_id):
        if product_uom_qty is None or not product_id:
            return False

        p_product = self.env["product.product"].browse(product_id)
        _delay = max(2, p_product.sale_delay)

        if product_uom_qty >= p_product.sla_quantity:
            _delay = max(p_product.sale_delay, p_product.sla_days)

        return _delay

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        """
        Perform a change on the following (additional) field when we change partner_id
        - warehouse_id

        :return: None
        """

        if not self.partner_id:
            self.update({
                "warehouse_id": False
            })
            return super(SaleOrder, self).onchange_partner_id()

        default_wh = self.env["stock.warehouse"].search([("default", "=", True)], limit=1)

        warehouse_id = self.partner_id and self.partner_id.partner_data \
                       and self.partner_id.partner_data[0].warehouse_id \
                       and self.partner_id.partner_data[0].warehouse_id \
                       and self.partner_id.partner_data[0].warehouse_id.id or \
                       default_wh and default_wh.id or False

        if not warehouse_id:
            raise ValidationError(
                _("Please configure a default Warehouse for %s specifically, or one generally." % self.partner_id.name)
            )

        # Update Sales Associate
        sale_associate_id = self.partner_id and self.partner_id.sale_associate_id \
                            and self.partner_id.sale_associate_id and self.partner_id.sale_associate_id.id or False

        self.update({"warehouse_id": warehouse_id, "sale_associate_id": sale_associate_id})

        if self.remote_shopping:
            partner_shipping_id = self.remote_customer_id.agent_id

        else:
            partner_shipping_id = self.partner_id

        res = super(SaleOrder, self).onchange_partner_id()
        self.partner_shipping_id = partner_shipping_id

        return res

    # Validators & Checkers & Modifiers
    @api.multi
    def do_prepare_duplicate(self, vals=None):
        """
        Checks if an order is a possible duplicate and marks the field is_duplicate as True
        Assumptions made:

        (1) product_uom_qty is always present else its zero
        (2) price_unit is always present else its set as the product's list_price or 1
        """
        _logger.info('prepare duplicates with vals %s'%vals)
        if vals is not None:
            _total = [
                (l[2].get("price_unit") or
                 self.env["product.product"].browse(l[2].get("product_id")).list_price
                 or 0) * l[2].get("product_uom_qty", 0)
                for l in vals.get("order_line")
            ]

            _logger.info("Check if order with total %s partner_id %s and customer_id %s and date_order %s "
                         % (sum(_total), vals.get("partner_id"), vals.get("customer_id"), vals.get("date_order")),
                         exc_info=True)

            self._cr.execute("""
                SELECT
                    COUNT(id)
                FROM sale_order
                WHERE (amount_total is null or amount_total::int = %s) AND partner_id = %s
                AND customer_id = %s AND DATE(date_order) = DATE(%s)
                AND state IN ('draft', 'sale');
            """, (sum(_total).__int__(), vals.get("partner_id"), vals.get("customer_id"), vals.get("date_order")))

            # TODO: Should we just generate SHA256/md5 sums for this instead?
            _check = [x[0] for x in self._cr.fetchall()]
            _logger.info("Check is %s" % _check)
            if _check.__len__() > 0 and _check[0] or 0 > 0:
                _logger.info('duplicate found for vals %s and total %s'%(vals,sum(_total)))
                vals.update({"is_duplicate": True})
            else:
                _logger.info('no duplicate found for vals %s and total %s'%(vals,sum(_total)))
                vals.update({"is_duplicate": False})
        else:
            _logger.info('do_prepare_duplicate with empty %s'%vals)

        return vals


    # Validators & Checkers & Modifiers
    @api.multi
    def do_check_duplicate(self, order):
        """
        Checks if an order has a possible duplicate and update is_duplicate field as True
        Assumptions made:

        (1) product_uom_qty is always present else its zero
        (2) price_unit is always present else its set as the product's list_price or 1
        """
        _logger.info('prepare duplicates for order %s'%order)
        if order:
            _total = order.amount_total or 0

            self._cr.execute("""
                SELECT id
                FROM sale_order
                WHERE (amount_total is null or amount_total::int = %s) AND partner_id = %s
                AND customer_id = %s AND DATE(date_order) = DATE(%s)
                AND state IN ('draft', 'sale');
            """, (_total, order.partner_id.id, order.customer_id.id, order.date_order))

            _check = self._cr.rowcount
            if _check > 1:
                # Read through the sale orders and compare their lines
                o_ids = [x[0] for x in self._cr.fetchall()]
                o_lines = self.env['sale.order.line'].search([('order_id', 'in', o_ids)])
                duplicates = []
                for l in o_lines:
                    if l.order_id.id in duplicates:
                        continue
                    #get any other line that has the same product
                    dup = o_lines.filtered(lambda x : x.id != l.id and x.product_id.id == l.product_id.id)
                    if dup:
                        duplicates.append(l.order_id.id)
                        order.is_duplicate = True
            else:
                return order
                #order.is_duplicate = False

        return order

    @api.multi
    def do_prepare_order_line_stock(self, order_line={}, partner_id=None):
        """
        Validates the order lines for:
        (1) Out of Stock - ordered qty > what is available for ordering per stockable product
        (1b) If out of stock check if product has alternative product and send sms to that effect about the alternative products
        (2) Invalid Quantity - order qty > what is available for ordering per stockable product per agent
        (3) Quota Exceeeded
        (4)

        NOTE: We use order_line.has_key("product_uom_qty") because order_line.get("product_uom_qty")
        on a product_uom_qty = 0, will return False

        :param order_line: Dict of Sale Order Lines
        :param partner_id: Integer of the Agent ordering
        :return: Dict of Sale Order Line vals marked with the appropriate reason
        """
        if order_line.get("product_id", False) and "product_uom_qty" in order_line:
            ordered_qty = float(order_line.get("product_uom_qty"))
            if ordered_qty % 1 != 0 or ordered_qty == 0:
                order_line.update({"reject_reason": "qty_exception"})
            else:
                order_line.update({"reject_reason": "ok"})

            product = self.env["product.product"].browse(order_line.get("product_id"))
            if product.exists() and product.can_stock and partner_id is not None:
                if product.max_sale_qty > 0 and ordered_qty > product.max_sale_qty:
                    order_line.update({"reject_reason": "stock_exception"})
                elif product.max_sale_qty > 0 and  ordered_qty + self.get_sale_qty_today(partner_id, product.id) \
                    > product.max_sale_qty:
                    order_line.update({"reject_reason": "quota_exceeded_exception"})
                elif product.reject_orders and ordered_qty > self.check_stock(product.id):
                    order_line.update({"reject_reason": "out_of_stock"})
                else:
                    order_line.update({"reject_reason": "ok"})

            if product.exists() and product.track_stock and \
                ordered_qty > self.check_stock(product.id):
                order_line.update({"reject_reason": "out_of_stock"})
        #finally if there was no reject reason..
        if 'reject_reason' not in order_line:
            order_line.update({"reject_reason": "ok"})

        return order_line

    @api.multi
    def do_prepare_product_un_bundling(self, lines=[]):
        """
        Method that checks for bundle products and consolidates as needed

        :param vals: Dict of the Sale Order Lines
        :return: Changes the Dict of Sale Order lines
        """
        _check = list(filter(
            lambda x: self.env["product.product"].browse(x[2].get("product_id")).can_bundle_product is True,
            lines
        ))
        # TODO: Price Unit should be set explicitly
        if _check:
            _bundles = [y[2].get("product_id") for y in _check]
            lines += [(
                0, 0, {
                    "name": p.product_id.name,
                    "product_id": p.product_id.id,
                    "product_uom_qty": p.quantity,
                    "product_uom": self.env.ref("product.product_uom_unit").id
                }) for p in self.env["product.bundle.line"].search(
                [("product_bundle_id", "in", _bundles)]
            )]

            lines = list(filter(
                lambda y: self.env["product.product"].browse(y[2].get("product_id")).can_bundle_product is False,
                lines
            ))

        return lines

    @api.multi
    def do_consolidate_order_line(self, order_line=[]):
        """
        Method that consolidates possible duplicate Sale Order lines

        :param order_line: Dict of the Sale Order Lines
        :return: Dict of the consolidated Sale Order Lines
        """
        _res = []
        for j, grp in groupby(
                sorted(order_line, key=lambda a: a[2]["product_id"]),
                lambda a: a[2]["product_id"]):
            _grp = [g for g in grp]
            if _grp.__len__() > 1:
                _grp[0][2].update({"product_uom_qty": sum([x[2].get("product_uom_qty") for x in _grp])})
                _res.append(_grp[0])
            else:
                _res.append(_grp[0])

        return _res

    @api.multi
    def do_check_payment_required(self, values=False):
        """
        Method that changes the default init state of the Order depending
        on whether it's high value, lay-away etc

        :param values: dict of the Order values
        :return: dict of the Order values, modified at times
        :raises ValidationError: if values are False, ie not given
        """
        if not values:
            raise ValidationError(_(
                "Values not supplied to do_check_payment_required(), {}!".format(values)
            ))

        return values

    # Helper Methods for create()
    # TODO - Add email notification for Rejected Products
    @api.multi
    def action_send_sms(self):
        """
        Send an SMS per Sale Order constrained to the following validations

        (1) Draft (good) orders, send Agent and/or Customer
        (2) Rejected orders, send to Agent

        NOTE: This method will send an SMS even when write() or copy() calls create()

        :self: odoo.addons.sale.order Recordset
        :return: True
        """
        for o in self:
            # get the phone that ordered from context
            agent_phone = self._context.get("agent_phone", None)
            alt_msg = []
            if agent_phone:
                msg, receipients = None, list(set([agent_phone, o.customer_id.phone]))
            else:
                msg, receipients = None, list(set([o.partner_id.phone, o.customer_id.phone]))
            if o.state == "draft":
                if o.partner_id.is_agent and o.partner_id.agent_type_id == self.env.ref("copia_partner.conf_t_chama") \
                        and o.partner_id.partner_data[0].chama_member_ids and o.partner_id == o.customer_id:
                    for member in o.partner_id.partner_data[0].chama_member_ids:
                        receipients.append(member.phone)

                l_msg = ", ".join("%s for %s at KES %s" % (
                    l.name, l.product_uom_qty, l.price_unit * l.product_uom_qty
                ) for l in o.order_line if l.sms_include)
                msg = "Copia Order # %s for delivery on %s confirmed for %s." \
                      " Total: KES %s" % (o.name, o.date_delivery, l_msg, o.amount_total)
            elif o.state == "rejected":
                if o.reject_reason == "qty_exception":
                    l_msg = " ".join("[%s]" % l.product_id.default_code for l in o.order_line)
                    msg = "Sorry. The ordered quantity for Product code %s is wrong." \
                          " Kindly enter a valid quantity." % l_msg
                elif o.reject_reason == "stock_exception":
                    l_msg = ", ".join(
                        "[%s] is %s" % (l.product_id.default_code, l.product_id.max_sale_qty) for l in o.order_line)
                    msg = "Sorry. The maximum order quantity for product code %s." \
                          " Kindly order an alternative or contact your Sales Advisor for more information." % l_msg
                # Checks which products are out of stock and checks for their alternative products
                elif o.reject_reason == "out_of_stock":
                    alternatives_available = []
                    for l in o.order_line:
                        tmpl_id = l.product_id.product_tmpl_id.id
                        qty = l.product_uom_qty
                        alternatives = self.check_alternative_products(tmpl_id, int(qty))
                        if not alternatives:
                            a_msg = 'Sorry. %s is currently not available in the market. We are working to get '\
                            'you an alternative product as soon as possible.' % l.product_id.display_name
                            alt_msg.append(a_msg)
                        else:
                            alternatives_available.append(alternatives)
                            alt_string = ['%s %s' % (alt['product_name'], alt['product_code']) for alt in alternatives]
                            #_logger.info(alt_string)
                            alt_string = ', '.join(alt_string)
                            a_msg = 'Sorry. %s is currently not available in the market. Copia recommends %s instead!'\
                            % (l.product_id.display_name, alt_string)
                            alt_msg.append(a_msg)
                    #_logger.info('alternatives are %s', alternatives_available)
                    #_logger.info(alt_msg)
                else:
                    l_msg = " ".join("[%s]" % l.product_id.default_code for l in o.order_line)
                    msg = "Sorry. You have exceeded the daily maximum order quantity allowed for product code %s." \
                          " Kindly place your order again tomorrow." % l_msg
            else:
                # Unknown Issue or Bad state
                # raise UserError(_(
                #     "SMS could not be sent. Sale Order # %s has a state of %s, or is duplicated" % (o.name, o.state)
                # ))
                continue

            # Create the SMS and Submit to the outgoing_sms Queue
            # with_context(add_to_queue=True/False) helps in testing
            if msg is not None:
                for r in receipients:
                    _logger.info('%s--%s' % (r, msg))
                    self.env["sms.message"].with_context(add_to_queue=True).create({
                        "type": "outbox",
                        "from_num": "Copia",
                        "to_num": r,
                        "date": datetime.datetime.today().isoformat(),
                        "text": msg,
                        "note": "Order Created in %s" % o.mode,
                        "order_created": True,
                        "partner_id": o.partner_id.id
                    })
            
            for msg in alt_msg:
                for r in receipients:
                    _logger.info('%s--%s' % (r, msg))
                    self.env["sms.message"].with_context(add_to_queue=True).create({
                        "type": "outbox",
                        "from_num": "Copia",
                        "to_num": r,
                        "date": datetime.datetime.today().isoformat(),
                        "text": msg,
                        "note": "Order Created in %s" % o.mode,
                        "order_created": True,
                        "partner_id": o.partner_id.id
                    })

        return True

    @api.multi
    def get_sale_qty_today(self, customer_id=None, product_id=None):
        """
        Returns the total qty ordered by a partner(customer) today
        This helps to prevent a customer from ordering more than is allowed based on the business rules

        :param customer_id: Integer of the Customer's DB Id
        :param product_id: Integer of the Product's DB Id
        :return: Float of the total quantity ordered by the Customer that day
        """
        query = """
            SELECT
                coalesce(sum(product_uom_qty), 0) AS ordered_qty
            FROM sale_order_line l
            JOIN sale_order o ON o.id = l.order_id
            WHERE o.state IN ('draft', 'progress', 'done') AND customer_id = %s
            AND product_id = %s AND date(o.create_date) = date(now())
        """
        self._cr.execute(query, (customer_id, product_id,))
        return self._cr.fetchone()[0]

    # global variable to hold the weight of items
    # necessary when splitting orders
    split_weight = 0.0

    @api.model
    def get_route_type(self, product_id, product_uom_qty):
        '''
        Get's the route type for the order line
        There are two route types: special and normal
        If the route type is special, the order line should be split later
        '''
        # set route type to normal by default
        route_type = 'normal'
        _logger.info('In get_route_type method!')
        product_obj = self.env['product.product']
        prod_split_obj = self.env['product.split']
        split_list_obj = self.env['split.list']
        split_lists = split_list_obj.search([])
        split_lists = split_list_obj.search([]).read(['id', 'category_ids', \
                                                      'max_weight'])
        max_weight = False if not split_lists else split_lists[0]['max_weight']
        total_weight = 0.0
        _logger.info('split_lists are %s', split_lists)
        category_ids = []  # the ids of categories that should be split if max weight is passed
        if max_weight and split_lists:
            category_ids = split_lists[0]['category_ids']

        _logger.info('category_ids is %s', category_ids)
        # first we check if the product is on the split list
        product = product_obj.browse(product_id)
        prod_split_domain = []
        prod_split_domain.append(('product_id', '=', product_id))
        prod_split_domain.append(('quantity', '<=', product_uom_qty))
        prod_split_id = prod_split_obj.search(prod_split_domain)
        split_data = {}
        _logger.info('product.weight is %s', product.weight)
        line_weight = float(product_uom_qty * product.weight) if product.weight != 0.0 else 0.0
        split_data.update({'weight': product.weight, 'line_weight': line_weight})
        # to do: the category weight is not per line but for the categories
        # with need to be split i.e. B&C and Farm
        # so if mabati and feed we combine the lines and check the weight
        split_data.update({'category_id': product.categ_id.id})
        if product.categ_id and product.categ_id.id in category_ids:
            _logger.info('Line product in split categories for %s and %s', product.name, \
                         product.categ_id.id)
            update_dict = {'category_split_id': product.categ_id.id}
            split_data.update(update_dict)
        else:
            update_dict = {'category_split_id': False}
            split_data.update(update_dict)
        # if there is a rule for the product or the weight meets the criteria
        # we will remove the line an place in another order
        _logger.info('domains are %s', prod_split_domain)
        to_split = prod_split_id and True or False
        update_dict = {'split_by_product': to_split}
        split_data.update(update_dict)
        _logger.info('split_by_product is %s', to_split)
        route_type = prod_split_id and 'special' or 'normal'
        split_data['route_type'] = route_type
        return split_data

    @api.multi
    def split_order_lines(self, values, mode="create"):
        """
        Receive a Dict describing the values for a Sale Order and split it depending on the Delivery
        Dates & Product's Category Sale Type

        :param values: Dict of the Sale Orders values
        :param mode: String of the origin of the Sale order, create/write
        :return: List of the Sale Order(s) that were split and their Order Lines
        """
        res, res_lines, r = [], [], {}
        if mode == 'create':
            date_order = parse(values.get("date_order"))
        else:
            date_order = self.date_order
        split_ref = values.get("split_ref", False)
        partner = self.env["res.partner"].browse(values.get("partner_id"))
        customer = self.env["res.partner"].browse(values.get("customer_id"))

        # Add and/or Calculate stuff: SLA + delays, sale_types & rejection per line
        for line in values.get("order_line", []):
            # TODO: Should we suggest a default delay in the statement ...or 2?
            # Add Delay in max of SLA or Customer Lead Time, id split_exempt is True ignore
            # individual product SLAs
            if partner and partner.agent_type_id and partner.agent_type_id.split_exempt:
                _delay = partner and partner.agent_type_id and \
                         partner.agent_type_id.default_sla_days or 2
            else:
                _delay = self._get_product_delay(line[2].get("product_uom_qty"), line[2].get("product_id"))

            date_delivery = self._get_delivery_date(date_order, partner, _delay)

            # Get sale_type_id
            # TODO - do we always expect the product_id here? - WRITE MODE
            if line[2].get("product_id"):
                _product = self.env["product.product"].browse(line[2].get("product_id"))
                sale_type_id = _product.product_tmpl_id and _product.product_tmpl_id.categ_id and \
                               _product.product_tmpl_id.categ_id.product_categ_sale_type_id and \
                               _product.product_tmpl_id.categ_id.product_categ_sale_type_id.id or False

                # Check & Modify Order Lines on stock and quantity for reject_reason - only in create mode
                # Marks the line as either ok, invalid_qty or out_of_stock for splitting below
                if mode == "create" and customer.exists():
                    self.do_prepare_order_line_stock(line[2], customer.id)
            else:
                # TODO: Defaulting sale_type_id to False may be broken, if there are other scenarios
                # Obtain the sale_type_id for lines that didn't change the product_id but in write
                # mode we have their order_line_id as l[1]
                if mode == "write":
                    _line_product = self.env["sale.order.line"].browse(line[1]).product_id
                    sale_type_id = _line_product.product_tmpl_id and _line_product.product_tmpl_id.categ_id and \
                                   _line_product.product_tmpl_id.categ_id.product_categ_sale_type_id and \
                                   _line_product.product_tmpl_id.categ_id.product_categ_sale_type_id.id or False
                else:
                    sale_type_id = False

            line[2].update({"date_delivery": date_delivery, "sale_type_id": sale_type_id})
            # get the route_type
            split_data = self.get_route_type(line[2].get("product_id"), line[2].get("product_uom_qty"))
            line[2].update({'split_data': split_data})
            res_lines.append(line)

        # check if there are items that should be on a special route
        for line in res_lines:
            if line[2]['split_data']['route_type'] == 'normal':
                # means the line is not split yet
                # check if any item in its category is in special route
                # also add the weight for special items to see if special route is needed
                similar_products = [a for a in res_lines if a[2]['split_data']['route_type'] == \
                                    'special' and a[2]['split_data']['category_id'] == line[2]['split_data'][
                                        'category_id']]
                if similar_products:
                    # means an item in the special route is in the same category as this one
                    # they should both be delivered together
                    line[2]['split_data'].update({'route_type': 'special', 'split_reason': 'similar_category'})
        # the weight we check to see if it exceeds allowed maximum
        # if it exceeds, the lines should be delivered together
        # we check for all lines that are in the category ids
        split_lists = self.env['split.list'].search([])

        split_cat_ids = split_lists.mapped(lambda x: x.category_ids.ids)
        _logger.info('split_cat_ids is %s', split_cat_ids)
        split_cat_ids = split_lists.category_ids.ids
        _logger.info('res_lines are %s', res_lines)
        if split_cat_ids:
            split_weight = 0.0
            splittable_lines = [l for l in res_lines if l[2]['split_data']['category_id'] in split_cat_ids]
            for line in splittable_lines:
                split_weight += line[2]['split_data']['line_weight']

        if split_lists and split_lists[0].max_weight < split_weight:
            # we split on weight
            for line in res_lines:
                if line[2]['split_data']['category_split_id'] and \
                        line[2]['split_data']['route_type'] == 'normal':
                    line[2]['split_data']['route_type'] = 'special'

        # set the route_type and remove the split_data key
        for line in res_lines:
            line[2]['route_type'] = line[2]['split_data']['route_type']
            del line[2]['split_data']

        # Split away the rejected Orders from ok res_lines, else do the usual
        if mode == "create":
            ok_res_lines, not_ok_res_lines = [], []
            for j, grp in groupby(
                    sorted(res_lines, key=lambda a: a[2]["reject_reason"]),
                    lambda a: a[2]["reject_reason"]):
                if j == "ok":
                    ok_res_lines = [g for g in grp]
                else:
                    not_ok_res_lines = [g for g in grp]

            if not_ok_res_lines:
                for k, grp in groupby(sorted(not_ok_res_lines, key=lambda a: a[2]["reject_reason"]),
                                      lambda a: a[2]["reject_reason"]):
                    rejected_order = copy.deepcopy(values)
                    _ol = []
                    for g in grp:
                        del g[2]["reject_reason"]
                        del g[2]["date_delivery"]
                        del g[2]["sale_type_id"]

                        _ol.append(g)

                    rejected_order.update({
                        "order_line": _ol,
                        "state": "rejected",
                        "reject_reason": k
                    })
                    res.append(rejected_order)
        else:
            ok_res_lines = res_lines

        # 1. Group by Route Types
        split_res = {}
        for j, grp in groupby(
                sorted(ok_res_lines, key=lambda a: a[2]["route_type"]),
                lambda a: a[2]["route_type"]):
            split_res[j] = [g for g in grp]

        _logger.info('split_res is %s', split_res)
        # TODO - vet this code!
        # 2. Group by Delivery Date & Compile split Sale Order(s)
        for route_type in split_res:
            for k, grp in groupby(
                    sorted(split_res.get(route_type), key=lambda a: a[2]["date_delivery"].__str__()),
                    lambda a: a[2]["date_delivery"].__str__()):
                _o = copy.deepcopy(values)
                _o.update({
                    "date_delivery": k,
                    "route_type": route_type,
                    "order_line": []
                })
                for g in grp:
                    g[2].pop("date_delivery", None)
                    g[2].pop("sale_type_id", None)
                    g[2].pop("reject_reason", None)

                    _o["order_line"].append(g)

                res.append(_o)

        if res.__len__() > 1:
            if not split_ref:
                split_ref = self.env["ir.sequence"].next_by_code("sale.order.split.reference")

            for r in res:
                r.update({
                    "split_ref": split_ref
                })

        return res

    @api.model
    def create(self, vals):
        """
        Override the create method so that we can check if the fore-casted delivery date will be the same for all lines.
        Fore-casted delivery date depends on:
        1. If the product SLA conditions are met i.e the minimum quantity then the product SLA minimum days is used
        2. If there is a customer lead time days on the product it is used
        3. Else the default fore-casted delivery date is order date + 2 days
        4. There is also some logic for Saturdays and Sundays and also for the time i.e. before 9.30
        (order confirmation time) and after 9.30

        Also send SMS Back on creation dependent on state or duplication of Sale Order
        - Duplicates: DO NOT send SMS
        - Rejected: send
        - Draft(ok): send

        :param vals: Dict of Sale Order creation values
        :return: Integer of the created Sale Order"s Database Id
        """

        # Validations
        agent = self.env["res.partner"].browse(vals.get("partner_id"))
        if bool(agent.exists()):
            if not agent.can_purchase:
                raise ValidationError(_(
                    "Agent {}, is not allowed to purchase !".format(agent.name)
                ))
        else:
            raise MissingError(_(
                "Partner for ID {}, could not be found !".format(vals.get("partner_id"))
            ))

        if "order_line" not in vals:
            raise UserError(_("No products selected. Please select a product(s) first"))

        # 1. Generate date_order
        if "date_order" not in vals:
            vals["date_order"] = self._get_date_order().__str__()

        # 2. Generate date_delivery
        if "date_delivery" not in vals:
            partner = self.env["res.partner"].browse(vals.get("partner_id"))
            vals["date_delivery"] = self._get_delivery_date(vals.get("date_order", False), partner, 2)

        # 3. Do product bundling
        vals["order_line"] = self.do_prepare_product_un_bundling(vals["order_line"])

        # 4. Consolidate the Order Lines
        if "order_line" in vals and vals.get("order_line").__len__() > 1:
            vals["order_line"] = self.do_consolidate_order_line(vals.get("order_line"))

        # Change init state for *special orders
        vals = self.do_check_payment_required(vals)

        res_orders = self.split_order_lines(vals)

        if res_orders:
            created_ids, set_delivery_charge = [], False
            for o in res_orders:
                # Check & Modify for Sale Order Duplication
                v = self.do_prepare_duplicate(o)

                # Set carrier_id in vals
                # FIXME: Make this work !
                if v.get("carrier_id", False):
                    if not set_delivery_charge:
                        set_delivery_charge = True
                    else:
                        v.update({"carrier_id": False})

                _sale_order = super(SaleOrder, self).create(v)
                created_ids.append(_sale_order)

                # Apply carrier_id
                if bool(_sale_order.carrier_id.exists()):
                    _sale_order.get_delivery_price()
                    _sale_order.set_delivery_line()
                    set_delivery_charge = True

            return created_ids[0]
        else:
            raise ValidationError("Cannot create a Sale Order with empty Sale Order Lines !")

    @api.multi
    def unlink(self):
        for order in self:
            if order.state == "rejected":
                raise UserError(_("You can not delete a sent quotation or a sales order! Try to cancel it before."))
        return super(SaleOrder, self).unlink()

    # TODO - Ensure that copy does not copy prepayments etc
    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        return super(SaleOrder, self).copy(default)

    @api.model
    def get_sale_associate_id(self, phone):
        '''
        Gets a sales associate given a phone number
        '''
        partner_obj = self.env['res.partner']
        res = partner_obj.search([('partner_type', '=', 'associate'), ('phone', '=', phone)])
        return res and res[0].id or False

    @api.model
    def create_out_sms(self, to_num, msg, agent_id=False):
        self.env["sms.message"].with_context(add_to_queue=True).create({
                      "type": "outbox",
                      "from_num": "Copia",
                      "partner_id": agent_id,
                      "to_num": to_num,
                      "date": datetime.datetime.today().isoformat(),
                      "text": msg,
                      "note": "Unrecognised Agent",
                      "order_created": False,
        })
        raise UserError(_(
            msg
        ))

    # Spec. API Methods
    @api.model
    def action_queue_create(self, vals):
        agent = self.env["res.partner"].search(
            ['|', ("phone", "=", vals.get("agent_phone")), ("mobile", "=", vals.get("agent_phone")),
             ("is_agent", "=", True), ("customer", "=", True), ('partner_type', '=', 'agent')]
        )
        customer = self.env["res.partner"].search(
            [("phone", "=", vals.get("customer_phone"))]
        )
        # just in case the customer and agent are more than one, no, it really happens though it shouldn't
        agent = agent[0] if agent else agent
        customer = customer[0] if customer else customer
        associate, associate_phone = (False, vals.get("associate_phone", False))
        # Check if associates number has been added
        if associate_phone:
            associate = self.env["res.partner"].search(
                ['|', ("phone", "=", vals.get("associate_phone")), ("mobile", "=", vals.get("associate_phone")),
                 ('partner_type', '=', 'associate')]
            )
            # associate_phone = associate[0] if associate else associate

        res, order_vals, result = [], {}, []
        try:
            wrong_codes = []
            wrong_qty = []
            max_qty = 10000
            # agent not found ...
            agent_id = agent.id if agent else False
            if not agent or not agent.can_purchase or not agent.active_agent:
                error_msg = "Sorry. Only a recognized Agent is permitted to place orders with Copia. " \
                            "Please contact us on 0798305527, for information on how to become an Agent."
                self.create_out_sms(vals.get("agent_phone"), error_msg,
                                    agent_id)

            # if the associate was not found...
            if associate_phone and not associate:
                error_msg = "Associate for number %s could not be found." % associate_phone
                self.create_out_sms(associate_phone, error_msg, agent_id)

            # if the customer was not found..
            if not bool(customer.exists()):
                customer = self.env["res.partner"].create({
                    "name": vals.get("customer_phone"),
                    "phone": vals.get("customer_phone"),
                    "agent_id": agent.id,
                    "partner_type": "customer",
                    "supplier": False
                })

            # Make the Sale Order - if we have Sale Order Lines
            _order_lines, carrier_id = [], False
            for l in vals.get("order_lines"):
                search_domain = ['|',('default_code', '=', l[0].upper()),
                                     ('old_default_code', '=', l[0].upper()),
                                     ('sale_ok', '=', True)]
                product = self.env["product.product"].search(search_domain, limit=1)
                if bool(product.exists()) and int(l[1]) <= max_qty:
                    carrier_id = self.env["delivery.carrier"].search([("product_id", "=", product.id)], limit=1)

                    if carrier_id and bool(carrier_id.exists()):
                        # Skip adding the delivery_carrier product it'll be added by 'Check Price', e.g HDL
                        order_vals.update({
                            "carrier_id": carrier_id.id,
                        })
                    else:
                        _order_lines.append([0, False, {
                            "product_id": product.id,
                            "product_uom_qty": int(l[1])
                        }])
                else:
                    if int(l[1]) > max_qty:
                        wrong_qty.append(l[0])
                    else:
                        wrong_codes.append(l[0])

            sale_associate_id = (associate and associate[0].id) or \
                                (agent.sale_associate_id and agent.sale_associate_id.id) or False
            order_vals.update({
                "partner_id": agent.id,
                "customer_id": customer.id,
                "order_line": _order_lines,
                "mode": vals.get("order_mode", "sms"),
                "sale_associate_id": sale_associate_id
            })
            # send message for the wrong product codes
            _logger.info('wrong_codes are %s', wrong_codes)
            if wrong_codes or wrong_qty:
                code_string = ' '.join('[%s]' % line for line in wrong_codes)
                wrong_string = ' '.join('[%s]' % line for line in wrong_qty)
                if wrong_codes:
                    error_msg = 'Sorry. No product exists for product code %s. Please enter product codes as' \
                                ' seen in the catalogue and send your order again.' % code_string
                if wrong_qty:
                    error_msg = 'Sorry. The quantity for product code %s is invalid. Please enter correct ' \
                                'qty and send your order again.' % wrong_string

                self.create_out_sms(vals.get("agent_phone"), error_msg, 
                                    agent.id)
                # _logger.info('error_msg is %s' % code_string)

            res = self.with_context(agent_phone=vals.get("agent_phone")).create(order_vals)

            if not res.split_ref:
                result = list(res)
            else:
                result = list(self.search([("split_ref", "=", res.split_ref)]))

            # Update the sms
            if vals.get("original_message_id", False):
                message = self.env["sms.message"].browse(vals.get("original_message_id"))
                if message:
                    message.write({
                        "order_created": True,
                        "partner_id": agent.id
                    })

            # Provide a "nice" response for Queue
            result = [
                "{} ({} {}) - {}".format(r.name, r.state, (r.is_duplicate and " duplicate" or "ok"), r.date_delivery)
                or False for r in result
            ]
        except (UserError, ValidationError, MissingError) as e:
            result = e.__str__()
        except Exception as e:
            result = e.__str__()
            raise e
        finally:
            return result

    @api.model
    def cancel_order_sms(self, so_number, sender):
        # make the so_number uppercase in case it isn't
        so_number = so_number.upper()
        so_obj = self.env['sale.order']
        search_domain = list()
        search_domain.append(('state', 'in', ('draft', 'progress', 'cancel')))
        search_domain.append(('name', '=', so_number))
        search_domain.append(('partner_id.phone', '=', sender))
        _logger.info('search_domain is %s' % search_domain)
        sale_orders = so_obj.search(search_domain)
        error_msg, msg = False, False
        if not sale_orders:
            error_msg = 'This order number is not correct. Please check the number and try again. '
        else:
            # check if it was already cancelled or confirmed
            for sale_order in sale_orders:
                if sale_order.state == 'cancel':
                    error_msg = 'This order has been successfully cancelled. Please replace another order.'
                elif sale_order.state == 'progress':
                    error_msg = "This order number has already been processed and is on it's way!" \
                                " Please have the amount payable ready. Thanks!"
                else:
                    res = sale_order.action_cancel()
        if not error_msg:
            msg = "This order has been successfully cancelled. Please replace another order."
            error_msg = msg

        self.env["sms.message"].with_context(add_to_queue=True).create({
            "type": "outbox",
            "from_num": "Copia",
            "to_num": sender,
            "date": datetime.datetime.today().isoformat(),
            "text": error_msg,
            "note": "Order cancellation response",
            "order_created": False,
        })
        return True

        # Checks if a product is in stock

    def check_stock(self, product_id):
        self.env.cr.execute("select get_expected_qoh(%s, %s)", (0, product_id))
        _x = self.env.cr.dictfetchall()
        return _x[0].get('get_expected_qoh')

    def check_alternative_products(self, product_id, qty_requested):
        """
        Gets alternative products that are in stock and can fullfil the order selected
        params product_id and qty_requested result lsit of alternative product codes available

        :param int product_id:
        :param float qty_requested:
        :return: str alt_products
        """
        self.env.cr.execute("SELECT product_id, product_code, product_name FROM get_alternativeproducts(%s, %s)", (product_id, qty_requested))
        alt_products = self.env.cr.dictfetchall()
        return alt_products

    def get_partner_pricelists(self, last_sync_date):
        """
        Method for CMS to fetch all agents' pricelists and pricelist items.
        """
        agent_pricelist = {}
        partner_ids = self.env['res.partner'].search([("partner_type", "=", 'agent'), ("can_purchase", "=", True),
                                                      ("active_agent", "=", True)])
        for partner in partner_ids:
            price_list_id = partner.property_product_pricelist
            if price_list_id:
                pricelist_item_fields = self.env['product.pricelist.item'].search([
                    ('pricelist_id', '=', price_list_id.id), ('write_date', '>=', last_sync_date),
                    ('price_surcharge', '!=', False)])
                pricelist_items = {}
                p_data = []

                for item in pricelist_item_fields:
                    if item.product_id:
                        product_id = item.product_id[0]
                        surcharge = item.price_surcharge
                        write_date = item.write_date
                        p_data.append(surcharge)
                        p_data.append(item.id)
                        p_data.append(write_date)
                        pricelist_items[str(product_id.id)] = p_data

                agent_pricelist[str(partner.id)] = pricelist_items
        return dumps(agent_pricelist)
