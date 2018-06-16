import logging
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderCreation(AccountingTestCase):
    def setUp(self):
        super(SaleOrderCreation, self).setUp()

        self.SaleOrder = self.env["sale.order"]
        self.AgentType = self.env["agent.type"]
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]

    def post_setup_data(self):
        # Agent Type
        self.agent_type = self.AgentType.create({
            "name": "T_Field",
            "split_exempt": False,
            "default_sla_days": 2
        })

        # Agent
        self.agent = self.Partner.create({
            "name": "Test Agent",
            "is_agent": True,
            "agent_type_id": self.agent_type.id,
            "phone": "+254789003445",
            "country_id": self.env.ref("base.main_company").country_id.id
        })

        # Customer
        self.customer = self.Partner.create({
            "name": "Test Customer",
            "is_agent": False,
            "phone": "+254789003444",
            "country_id": self.env.ref("base.main_company").country_id.id
        })

    def test_001_sale_order_duplication(self):
        self.post_setup_data()

        product_1 = self.Product.search([("name", "like", "Oil")], limit=1)
        uom = self.env.ref("product.product_uom_unit")

        _vals = {
            "partner_id": self.agent.id,
            "customer_id": self.customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": self.SaleOrder._get_date_order_2("2017-07-10"),
            "order_line": [
                (0, 0, {
                    "name": product_1.name,
                    "product_id": product_1.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom.id,
                    "price_unit": 508.0
                })
            ]
        }

        order_1 = self.SaleOrder.create(_vals)
        self.assertFalse(order_1.is_duplicate, "Sale Order IS NOT a duplicate ! %s" % order_1.is_duplicate)

        order_2 = self.SaleOrder.create(_vals)
        self.assertTrue(order_2.is_duplicate, "Sale Order IS a duplicate ! %s" % order_2.is_duplicate)

        _vals["order_line"].append((0, 0, {
            "name": product_1.name,
            "product_id": product_1.id,
            "product_uom_qty": 2.0,
            "product_uom": uom.id,
            "price_unit": 508.0
        }))
        order_3 = self.SaleOrder.create(_vals)
        self.assertFalse(order_3.is_duplicate, "Sale Order IS NOT a duplicate ! %s" % order_3.is_duplicate)
