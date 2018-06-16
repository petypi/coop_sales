import logging
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestChamaaOrder(AccountingTestCase):
    def setUp(self):
        super(TestChamaaOrder, self).setUp()

        self.SaleOrder = self.env["sale.order"]
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]

    def test_001_chamaa_order(self):
        # Create Partner
        agent = self.Partner.create({
            "name": "Chamaa Test Partner",
            "phone": "+254720234567",
            "country_id": self.env.ref("base.main_company").country_id.id,
            "is_agent": True,
            "agent_type_id": self.env.ref("copia_commission.conf_t_field").id,
            "partner_data": [
                (0, 0, {
                    "warehouse_id": self.env["stock.warehouse"].search([("name", "=", "Magana")], limit=1).id,
                    "pin": "A90878",
                    "is_chama": True,
                    "chamaa_member_ids": [
                        (4, p.id, False) for p in
                        self.Partner.search([("customer", "=", True), ("is_agent", "=", False)], limit=4)
                    ]
                })
            ]
        })
        self.assertTrue(
            agent.partner_data.__len__() == 1, "Chamaa creation failure ! %s" % [a.name for a in agent.partner_data]
        )

        # Create Sale Order
        product_1 = self.Product.search([("name", "like", "Oil")], limit=1)
        uom = self.env.ref("product.product_uom_unit")

        self.SaleOrder.create({
            "partner_id": agent.id,
            "customer_id": agent.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": self.SaleOrder._get_date_order_2("2017-11-05"),
            "order_line": [
                (0, 0, {
                    "name": product_1.name,
                    "product_id": product_1.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom.id,
                    "price_unit": 508.0
                })
            ]
        })

        # Check SMS
        _recipients = [p.id for p in agent.partner_data[0].chamaa_member_ids]
        _recipients.append(agent.id)

        _sms = self.env["sms.message"].search([("partner_id", "in", _recipients)])
        self.assertTrue(
            _sms.__len__() == 5, "Messages don't match Chamaa members ! %s vs. %s" % (
                sorted([p.name for p in agent.partner_data[0].chamaa_member_ids]),
                sorted([q.partner_id.name for q in _sms])
            )
        )

    def test_002_chamaa_sale_order_create(self):
        # Create Partner
        agent = self.Partner.create({
            "name": "Chamaa Test Partner",
            "phone": "+254720234567",
            "country_id": self.env.ref("base.main_company").country_id.id,
            "is_agent": True,
            "agent_type_id": self.env.ref("copia_commission.conf_t_field").id,
            "partner_data": [
                (0, 0, {
                    "warehouse_id": self.env["stock.warehouse"].search([("name", "=", "Magana")], limit=1).id,
                    "pin": "A90878",
                    "is_chama": True,
                    "chamaa_member_ids": [
                        (4, p.id, False) for p in
                        self.Partner.search([("customer", "=", True), ("is_agent", "=", False)], limit=4)
                    ]
                })
            ]
        })
        self.assertTrue(
            agent.partner_data.__len__() == 1, "Chamaa creation failure ! %s" % [a.name for a in agent.partner_data]
        )

        # Create the needed products
        _categ = self.env["product.category"].search([("name", "=", "Promotions")], limit=1)

        # Normal Products
        prod_a_1 = self.Product.create({
            "name": "Test Product #A1",
            "categ_id": _categ.id,
            "sla_quantity": 0,
            "sla_days": 0,
            "sale_delay": 2,
            "type": "product",
            "standard_price": 20.00,
            "list_price": 24.00
        })

        prod_a_2 = self.Product.create({
            "name": "Test Product #A2",
            "categ_id": _categ.id,
            "sla_quantity": 0,
            "sla_days": 0,
            "sale_delay": 2,
            "type": "product",
            "standard_price": 120.00,
            "list_price": 140.00
        })

        prod_b_1 = self.Product.create({
            "name": "Test Product #B1",
            "categ_id": _categ.id,
            "sla_quantity": 3,
            "sla_days": 4,
            "sale_delay": 2,
            "type": "product",
            "standard_price": 200.00,
            "list_price": 300.00
        })

        # Bundle product
        bundle_prod_1 = self.Product.create({
            "name": "Bundle Test #001",
            "categ_id": _categ.id,
            "sla_quantity": 0,
            "sla_days": 0,
            "sale_delay": 2,
            "type": "consu",
            "can_bundle_product": True,
            "standard_price": 1.00,
            "list_price": 1.00,
            "product_bundle_line_ids": [
                (0, 0, {"product_id": p.id, "quantity": 2}) for p in
                [prod_a_1, prod_a_2, prod_b_1]
            ]
        })
        self.assertTrue(
            bundle_prod_1.product_bundle_line_ids.__len__() == 3,
            "Bundle's Product Lines are not valid ! %s" % [
                (x.product_id and x.product_id.name or "/", x.quantity or "0.0") for x in
                bundle_prod_1.product_bundle_line_ids
            ]
        )

        # Create Sale Order
        uom = self.env.ref("product.product_uom_unit")

        sale_order_1 = self.SaleOrder.create({
            "partner_id": agent.id,
            "customer_id": agent.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": self.SaleOrder._get_date_order_2("2017-11-05"),
            "order_line": [
                (0, 0, {
                    "name": bundle_prod_1.name,
                    "product_id": bundle_prod_1.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom.id
                })
            ]
        })
        self.assertTrue(
            sale_order_1.order_line.__len__() == 3, "Sale order not bundled correctly ! %s" % [
                (l.name, l.product_uom_qty) for l in sale_order_1.order_line
            ]
        )
