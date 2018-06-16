import logging
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestBulkProductPromotion(AccountingTestCase):
    def setUp(self):
        super(TestBulkProductPromotion, self).setUp()

        self.BulkOrder = self.env["bulk.orders"]
        self.SaleOrder = self.env["sale.order"]
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]

    def test_001_sale_order_line_append(self):
        # Insert a product promotion line
        customer = self.Partner.search([("customer", "=", True)], limit=1)
        product = self.Product.search([("default_code", "=", "FO38")])
        product_1 = self.Product.search([("default_code", "=", "FO78")])
        uom = self.env.ref("product.product_uom_unit")

        promo_vals = {
            "customer_id": customer.id,
            "product_id": product.id,
            "quantity": 4.0
        }
        promo = self.BulkOrder.create(promo_vals)

        # Create a Sale Order tagging the customer
        agent = self.Partner.search([("name", "=", "Fieldwork")], limit=1)
        order_vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": self.SaleOrder._get_date_order_2("2017-07-10 06:29:00"),
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
        order = self.SaleOrder.create(order_vals)

        # Assert that the order_lines are 2
        self.assertEquals(
            2, order.order_line.__len__(),
            "(fail) Order was not created with extra promo line added - %s" % order.order_line.__len__()
        )

        # Assert that the order_lines include the promo product
        _lines = [l.product_id.default_code for l in order.order_line]
        self.assertTrue(
            "FO38" in _lines,
            "(fail) Order does not include promo product - %s" % _lines
        )

        # Assert that the promo has been used
        promo_reload = self.BulkOrder.browse(promo.id)
        self.assertTrue(
            promo_reload.used, "(fail) Promotion was not used up - %s (%s)" % (promo.used, promo_reload.used)
        )

        # TODO - Assert that we can't find the promo again

    def test_002_promo_create_validation(self):
        # Insert a product promotion line
        customer_1 = self.Partner.search([("customer", "=", True)], limit=1)
        customer_2 = self.Partner.search(
            [("name", "=", "Fieldwork"), ("customer", "=", True)], limit=1)
        product_1 = self.Product.search([("default_code", "=", "FO38")])
        product_2 = self.Product.search([("default_code", "=", "FO78")])
        uom = self.env.ref("product.product_uom_unit")

        # Create for customer_1, product_1
        promo_vals = {
            "customer_id": customer_1.id,
            "product_id": product_1.id,
            "quantity": 1.0
        }
        promo_1 = self.BulkOrder.create(promo_vals)

        # Create for customer_2
        promo_vals = {
            "customer_id": customer_2.id,
            "product_id": product_1.id,
            "quantity": 1.0
        }
        promo_2 = self.BulkOrder.create(promo_vals)

        # Try to make promo_1 again
        promo_vals = {
            "customer_id": customer_1.id,
            "product_id": product_1.id,
            "quantity": 1.0
        }

        # Assert that a ValidationError() is raised
        with self.assertRaises(ValidationError):
            self.BulkOrder.create(promo_vals)
