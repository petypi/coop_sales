import logging
from itertools import product
from odoo.addons.account.tests.account_test_classes import AccountingTestCase

_logger = logging.getLogger(__name__)


class TestSaleOrderDeliveryDateCalc(AccountingTestCase):

    def setUp(self):
        """
        The test requires that:

        (1) Agents
        - An Institutional (Institutional) with +4 day default SLA
        - A TBC agent (TBC) with +3 day default SLA
        - A Field agent (Fieldwork) with  +2 day default SLA

        (2) Product
        - FO28: sla_qty=0.0, sla_days=2
        - FO29: sla_qty=0.0, sla_days=2
        - FO38: sla_qty=0.0, sla_days=2
        - FO39: sla_qty=3.0, sla_days=4
        - FO48: sla_qty=0.0, sla_days=2
        - FO49: sla_qty=0.0, sla_days=2
        - FO78: sla_qty=2.0, sla_days=3
        - CBC2: sla_qty=2.0, sla_days=3, B&C

        :return: Object
        """
        super(TestSaleOrderDeliveryDateCalc, self).setUp()

        self.SaleOrder = self.env["sale.order"]
        self.ResPartner = self.env["res.partner"]
        self.Product = self.env["product.product"]
        self.ProductUoM = self.env["product.uom"]

    def xtest_00_field_0_lead_2_dy_sla_dates(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_id = self.Product.search([("default_code", "=", "FO28")], limit=1)

        # Below are the Date Test Cases as (time_of_order, order_date, delivery_date)
        dates = [
            ("2017-07-10 06:29:00", "2017-07-08", "2017-07-11"),
            ("2017-07-10 06:31:00", "2017-07-10", "2017-07-12"),
            ("2017-07-11 06:29:00", "2017-07-10", "2017-07-12"),
            ("2017-07-11 06:31:00", "2017-07-11", "2017-07-13"),
            ("2017-07-12 06:29:00", "2017-07-11", "2017-07-13"),
            ("2017-07-12 06:31:00", "2017-07-12", "2017-07-14"),
            ("2017-07-13 06:29:00", "2017-07-12", "2017-07-14"),
            ("2017-07-13 06:31:00", "2017-07-13", "2017-07-15"),
            ("2017-07-14 06:29:00", "2017-07-13", "2017-07-15"),
            ("2017-07-14 06:31:00", "2017-07-14", "2017-07-17"),
            ("2017-07-15 06:29:00", "2017-07-14", "2017-07-17"),
            ("2017-07-15 06:31:00", "2017-07-15", "2017-07-18"),
            ("2017-07-16 06:29:00", "2017-07-15", "2017-07-18"),
            ("2017-07-16 06:31:00", "2017-07-15", "2017-07-18"),
        ]
        n = 1
        for ct, od, dd in dates:
            vals = {
                "partner_id": agent.id,
                "customer_id": customer.id,
                "pricelist_id": 1,
                "fiscal_position_id": False,
                "date_order": self.SaleOrder._get_date_order_2(ct),
                "order_line": [
                    (0, 0, {
                        "name": product_id.name,
                        "product_id": product_id.id,
                        "product_uom_qty": 1.0,
                        "product_uom": uom_id.id,
                        "price_unit": 508.0
                    })
                ]
            }
            order_id = self.env["sale.order"].create(vals)

            # Order Date
            self.assertEqual(
                order_id.date_order, od,
                "(fail: %s) Actual Order Date - %s, %s : SLA %s day(s), %s Lead Day(s)" % (
                    n, od, order_id.date_order, product_id.sla_days, product_id.sale_delay
                )
            )

            # Delivery Date
            self.assertEqual(
                order_id.date_delivery, dd,
                "(fail: %s) Actual Delivery Date - %s, %s : SLA %s day(s), %s Lead Day(s)" % (
                    n, dd, order_id.date_delivery, product_id.sla_days, product_id.sale_delay
                )
            )
            n += 1

    def xtest_01_institution_0_lead_3_dy_sla_dates(self):
        agent = self.ResPartner.search([("name", "=", "TBC")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_id = self.Product.search([("default_code", "=", "FO28")], limit=1)

        # Below are the Date Test Cases as (time_of_order, order_date, delivery_date)
        dates = [
            ("2017-07-10 06:29:00", "2017-07-08", "2017-07-12"),
            ("2017-07-10 06:31:00", "2017-07-10", "2017-07-13"),
            ("2017-07-11 06:29:00", "2017-07-10", "2017-07-13"),
            ("2017-07-11 06:31:00", "2017-07-11", "2017-07-14"),
            ("2017-07-12 06:29:00", "2017-07-11", "2017-07-14"),
            ("2017-07-12 06:31:00", "2017-07-12", "2017-07-15"),
            ("2017-07-13 06:29:00", "2017-07-12", "2017-07-15"),
            ("2017-07-13 06:31:00", "2017-07-13", "2017-07-17"),
            ("2017-07-14 06:29:00", "2017-07-13", "2017-07-17"),
            ("2017-07-14 06:31:00", "2017-07-14", "2017-07-18"),
            ("2017-07-15 06:29:00", "2017-07-14", "2017-07-18"),
            ("2017-07-15 06:31:00", "2017-07-15", "2017-07-19"),
            ("2017-07-16 06:29:00", "2017-07-15", "2017-07-19"),
            ("2017-07-16 06:31:00", "2017-07-15", "2017-07-19"),
        ]
        n = 1
        for ct, od, dd in dates:
            vals = {
                "partner_id": agent.id,
                "customer_id": customer.id,
                "pricelist_id": 1,
                "fiscal_position_id": False,
                "date_order": self.SaleOrder._get_date_order_2(ct),
                "order_line": [
                    (0, 0, {
                        "name": product_id.name,
                        "product_id": product_id.id,
                        "product_uom_qty": 1.0,
                        "product_uom": uom_id.id,
                        "price_unit": 508.0
                    })
                ]
            }
            order_id = self.env["sale.order"].create(vals)

            # Order Date
            self.assertEqual(
                order_id.date_order, od,
                "(fail: %s) Actual Order Date - %s, %s : SLA %s day(s), %s Lead Day(s)" % (
                    n, od, order_id.date_order, product_id.sla_days, product_id.sale_delay
                )
            )

            # Delivery Date
            self.assertEqual(
                order_id.date_delivery, dd,
                "(fail: %s) Actual Delivery Date - %s, %s : SLA %s day(s), %s Lead Day(s)" % (
                    n, dd, order_id.date_delivery, product_id.sla_days, product_id.sale_delay
                )
            )

            n += 1

    def xtest_02_field_split_order_on_delivery_date(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO78", "FO28", "FO39"))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 3.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }

        res = self.SaleOrder.create(vals)
        res_orders = self.SaleOrder.search([("split_ref", "=", res.split_ref)])

        # Assert that split occurred into the expected 2 Sale Orders
        self.assertEqual(
            3, res_orders.__len__(),
            "(fail) Sale Orders did not split into 2 - %s" % res_orders.__len__()
        )

        # We expect the following delivery dates due to SLA
        # FO78 +2 SLA, FO38 +3 SLA, FO48 +4 on 2017-07-12
        d_dates = [("2017-07-14", "FO28"), ("2017-07-15", "FO78"), ("2017-07-17", "FO39")]

        # Match the expectations to what was done
        n = 0
        for x, y in product(d_dates, res_orders):
            if x[0] == y.date_delivery:
                for z in y.order_line:
                    if x[1] == z.product_id.default_code:
                        n += 1

        self.assertEqual(3, n, "(fail) n is not equal to 3 - %s" % n)

    def xtest_03_institution_split_order_on_delivery_date(self):
        agent = self.ResPartner.search([("name", "=", "TBC")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO78", "FO28", "FO39"))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 3.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }

        res = self.SaleOrder.create(vals)
        res_orders = [o for o in self.SaleOrder.search([("split_ref", "=", res.split_ref)])]

        # Assert that split occurred into the expected 3 Sale Orders
        self.assertEqual(
            3, res_orders.__len__(),
            "(fail) Sale Orders did not split into 3 - %s" % res_orders.__len__()
        )

        # We expect the following delivery dates due to SLA
        # FO28 +2 SLA, FO78 +3 SLA, FO39 +4 on 2017-07-12 +1 bcoz of TBC
        d_dates = [("2017-07-15", "FO28"), ("2017-07-17", "FO78"), ("2017-07-17", "FO39")]

        # Match the expectations to what was done
        n = 0
        for x, y in product(d_dates, res_orders):
            if x[0] == y.date_delivery:
                for z in y.order_line:
                    if x[1] == z.product_id.default_code:
                        n += 1

        self.assertEqual(2, n, "(fail) n is not equal to 3 - %s" % n)

    def xtest_04_field_write_change_delivery_date(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO38", "FO78"))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }

        res = self.SaleOrder.create(vals)

        # We expect a delivery date of 2017-07-14 and a single order
        self.assertFalse(res.split_ref, "Wrong splitting of Sale Order Lines - %s" % res.split_ref)

        # Change the qty on FO78 to be > 2.0
        write_vals = {
            "order_line": [
                (1, i.id, {"product_uom_qty": 4.0}) for i in res.order_line
                if i.product_id.default_code == "FO78"
            ]
        }

        # Add an additional line - normal SLA
        wp = self.Product.search([("default_code", "=", "FO39")])
        write_vals["order_line"].append(
            (0, False, {
                "name": wp.name,
                "product_id": wp.id,
                "product_uom_qty": 1.0,
                "product_uom": uom_id.id,
                "price_unit": 508.0
            })
        )

        res.write(write_vals)
        new_res = self.SaleOrder.search([("name", "=", res.name)])

        # Find the split orders we expect 2
        split_orders = self.SaleOrder.search([("split_ref", "=", res.split_ref)])
        self.assertEqual(
            2, split_orders.__len__(), "(fail) Split Ref. %s found too many/few orders -%s" % (
                new_res.split_ref, split_orders.__len__()
            )
        )

    def xtest_05_institution_write_change_delivery_date(self):
        agent = self.ResPartner.search([("name", "=", "TBC")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO38", "FO78"))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }

        res = self.SaleOrder.create(vals)

        # We expect a delivery date of 2017-07-14 and a single order
        self.assertFalse(res.split_ref, "Wrong splitting of Sale Order Lines - %s" % res.split_ref)

        # Change the qty on FO78 to be > 2.0, thus SLA +3
        write_vals = {
            "order_line": [
                (1, i.id, {"product_uom_qty": 4.0}) for i in res.order_line
                if i.product_id.default_code == "FO78"
            ]
        }
        res.write(write_vals)
        new_res = self.SaleOrder.search([("name", "=", res.name)])

        # Find the split orders we expect 2
        split_orders = self.SaleOrder.search([("split_ref", "=", res.split_ref)])
        self.assertEqual(
            2, split_orders.__len__(), "(fail) Split Ref. %s found too many/few orders -%s" % (
                new_res.split_ref, split_orders.__len__()
            )
        )

    def xtest_06_write_test(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO28", "FO38", "FO78"))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, False, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }

        res = self.SaleOrder.create(vals)

        # We expect a delivery date of 2017-07-14 and a single order
        self.assertFalse(res.split_ref, "Wrong splitting of Sale Order Lines - %s" % res.split_ref)

        # Change the qty on FO78 to be > 2.0
        write_vals = {
            "order_line": [
                (1, i.id, {"product_uom_qty": 4.0}) for i in res.order_line
                if i.product_id.default_code == "FO78"
            ]
        }

        # Change the product_id on FO28 to be FO29
        np = self.Product.search([("default_code", "=", "FO29")], limit=1)
        write_vals["order_line"].append([
            (1, i.id, {"product_id": np.id}) for i in res.order_line
            if i.product_id.default_code == "FO28"
            ][0])

        # Add an additional line - normal SLA
        wp = self.Product.search([("default_code", "=", "FO49")], limit=1)
        write_vals["order_line"].append(
            (0, False, {
                "name": wp.name,
                "product_id": wp.id,
                "product_uom_qty": 1.0,
                "product_uom": uom_id.id,
                "price_unit": 508.0
            })
        )

        # Add an additional line - abnormal SLA
        wp = self.Product.search([("default_code", "=", "FO39")], limit=1)
        write_vals["order_line"].append(
            (0, False, {
                "name": wp.name,
                "product_id": wp.id,
                "product_uom_qty": 3.0,
                "product_uom": uom_id.id,
                "price_unit": 508.0
            })
        )

        write_res = res.write(write_vals)
        new_res = self.SaleOrder.search([("name", "=", res.name)])

        # Find the split orders we expect 3
        split_orders = self.SaleOrder.search([("split_ref", "=", res.split_ref)])
        self.assertEqual(
            3, split_orders.__len__(), "(fail) Split Ref. %s found too many/few orders - %s" % (
                new_res.split_ref, split_orders.__len__()
            )
        )

        # Assert that they all have order_lines
        for o in split_orders:
            self.assertNotEqual(
                0, o.order_line.__len__(),
                "(fail) Order created without Order Lines - %s" % o.date_delivery
            )
            _logger.info("%s - %s" % (o.name, o.date_delivery))
            for l in o.order_line:
                _logger.info("[%s] %s - %s (%s : %s)" % (
                    l.product_id.default_code, l.product_id.name, l.product_uom_qty, l.product_id.sla_quantity,
                    l.product_id.sla_days
                ))

        # We expect split results as follows
        t_res = [
            ("2017-07-14", 3, ["FO49", "FO38", "FO29"]),
            ("2017-07-15", 1, ["FO78"]),
            ("2017-07-17", 1, ["FO39"])
        ]

        for o, r in product(split_orders, t_res):
            if o.date_delivery == r[0]:
                # Assert that the split numbers tally
                self.assertEquals(
                    r[1], o.order_line.__len__(),
                    "(fail) Sale Order (%s) did not split correctly - %s" % (o.date_delivery, o.order_line.__len__())
                )

                # Assert that the split occurred as expected
                _ol = [l.product_id.default_code for l in o.order_line]
                _logger.info("%s - %s, %s" % (
                    o.date_delivery, sorted([i.__str__() for i in _ol]), sorted(r[2])
                ))
                # self.assertAlmostEquals(
                #     _ol, r[2],
                #     "(fail) Split did not tally %s - %s" % (sorted([i.__str__() for i in _ol]), sorted(r[2]))
                # )

    def xtest_07_split_exempt(self):
        agent = self.ResPartner.search([("name", "=", "Institutional")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO28", "FO39", "FO78"))])

        # We add the lines with multiple different SLA days
        # Since, FO28 +2, FO39 +4, FO78 +3
        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 4.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }
        order = self.SaleOrder.create(vals)

        # Assert that no split happened
        self.assertFalse(order.split_ref, "(fail) Split occured on split_exempt %s" % order.split_ref)

        # We expect a delivery date of Institutional +4, 2017-07-17, coz of Sunday
        self.assertEquals(
            "2017-07-17", order.date_delivery,
            "(fail) Delivery Date not calculated properly - %s" % order.date_delivery
        )

    def xtest_08_hot_list(self):
        agent = self.ResPartner.search([("name", "=", "Institutional")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO28", "FO39", "FO78"))])

        # FO28 - hot_list: True, FO39, FO78 - hot_list: False
        #  hot_list
        vals_1 = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 4.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids
            ]
        }
        order_1 = self.SaleOrder.create(vals_1)

        # Assert that hot_list is True
        self.assertTrue(order_1.hot_list, "(fail) Order should be hot_list %s" % order_1.hot_list)

        # Non-hot_list
        vals_2 = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 4.0,
                    "product_uom": uom_id.id,
                    "price_unit": 508.0
                }) for p in product_ids if p.hot_list is False
            ]
        }
        order_2 = self.SaleOrder.create(vals_2)

        # Assert that hot_list is True
        self.assertFalse(order_2.hot_list, "(fail) Order should be hot_list %s" % order_2.hot_list)

    def xtest_09_sale_type_id(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("FO78", "FU7", "FO84"))])

        # FO78, FU7 - Foodstuff & Household: FO84 - Construction
        vals_1 = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                }) for p in product_ids
            ]
        }
        order_1 = self.SaleOrder.create(vals_1)
        orders = self.SaleOrder.search([("split_ref", "=", order_1.split_ref)])

        # Assert that that 2 orders were created
        self.assertEqual(2, orders.__len__(), "(fail) Orders should be 2, %s" % order_1.__len__())

        # Assert that orders have the proper sale_types
        _sale_type_orders = sorted([o.sale_type_id and o.sale_type_id.name or False for o in orders])
        self.assertEqual(
            sorted(["Foodstuff & Household", "Construction"]), 
            _sale_type_orders,
            "(fail) Orders should be in correct Sale types, %s" % _sale_type_orders
        )

    def xtest_10_rejected_orders(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("GKK11", "FU7", "FO28"))])

        # FO78, FU7 - Reject: GKK11 - Stock OK
        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 6.0,
                    "product_uom": uom_id.id,
                }) for p in product_ids
            ]
        }
        order = self.SaleOrder.create(vals)
        orders = self.SaleOrder.search([("split_ref", "=", order.split_ref)])

        # Assert that that 2 orders were created
        self.assertEqual(2, orders.__len__(), "(fail) Orders should be 2, %s" % order.__len__())

        _states = sorted([o.state for o in orders])
        self.assertEqual(
            sorted(["draft", "rejected"]), 
            _states,
            "(fail) Orders should be in correct Sale States, %s" % _states
        )

    def xtest_11_delivery_priority(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("GKK11", "F078", "FO84", "HDL"))])

        # GKK11, FU7 - Food: FO84 - Construction
        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                }) for p in product_ids
            ]
        }
        order = self.SaleOrder.create(vals)
        _logger.info("> %s" % order.split_ref)
        orders = self.SaleOrder.search([("split_ref", "=", order.split_ref)])
        for o in orders:
            _logger.info("======> %s\t-\t%s\t-\t%s" % (o.state, o.date_delivery, o.sale_type_id))
            for l in o.order_line:
                _logger.info("-> %s\t%s" % (l.product_id.default_code, l.product_id.name))

        # Assert that that 2 orders were created
        self.assertEqual(2, orders.__len__(), "(fail) Orders should be 2, %s" % order.__len__())

        # Assert that the Home Delivery is on the cosntruction Orders
        _order = [o for o in orders if o.sale_type_id.name == "Construction"][0]
        self.assertEqual(
            _order.carrier_id.id, 
            2,
            "(fail) Construction Order should have HDL (%s), %s" % (_order.sale_type_id.name, _order.carrier_id.name)
        )

    def test_12_order_line_consolidation(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Ben")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("GKK11", "F078", "FO84",))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                }) for p in product_ids
            ]
        }

        # Assert no changes
        _order_line_1 = self.SaleOrder.do_consolidate_order_line(vals.get("order_line"))
        self.assertEquals(
            vals.get("order_line").__len__(), _order_line_1.__len__(),
            "Original Order Lines - %s don't match new Order lines - %s" % (vals.get("order_line"), _order_line_1)
        )

        # Insert duplicates
        product_ids_2 = self.Product.search([("default_code", "in", ("GKK11", "FO84",))])
        for p in product_ids_2:
            vals.get("order_line").append((0, 0,
                {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 2.0,
                    "product_uom": uom_id.id,
                })
            )

        _order_line_2 = self.SaleOrder.do_consolidate_order_line(vals.get("order_line"))
        _orig = sorted([(k[2].get("name"), 3.0) for k in vals.get("order_line") if k[2].get("name")])
        _new = sorted([(l[2].get("name"), l[2].get("product_uom_qty")) for l in _order_line_2])
        self.assertEquals(
            set(_orig), set(_new),
            "Consolidation Failure, Expected Order Line - %s, does not match New Order Lines - %s" % (_orig, _new)
        )

    def test_13_order_line_consolidation_on_create(self):
        agent = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        customer = self.ResPartner.search([("name", "=", "Fieldwork")], limit=1)
        uom_id = self.ProductUoM.search([("name", "=", "Unit(s)")], limit=1)
        product_ids = self.Product.search([("default_code", "in", ("GKK11", "FO48", "FO28",))])

        vals = {
            "partner_id": agent.id,
            "customer_id": customer.id,
            "pricelist_id": 1,
            "fiscal_position_id": False,
            "date_order": "2017-07-12",
            "order_line": [
                (0, 0, {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 1.0,
                    "product_uom": uom_id.id,
                }) for p in product_ids
            ]
        }

        # Insert duplicates
        product_ids_2 = self.Product.search([("default_code", "in", ("GKK11", "FO28",))])
        for p in product_ids_2:
            vals.get("order_line").append((0, 0,
                {
                    "name": p.name,
                    "product_id": p.id,
                    "product_uom_qty": 2.0,
                    "product_uom": uom_id.id,
                })
            )

        self.assertEquals(5, vals.get("order_line").__len__(), "Duplicates not appended to vals - %s" % vals)

        # Create the Sale Order
        sale_order = self.SaleOrder.create(vals)

        # We expect the consolidation to produce 3 lines max
        self.assertEquals(
            3, sale_order.order_line.__len__(),
            "Consolidation Failure, Expected consolidation did not occur -%s" % sale_order.order_line
        )

        # We expect the products in product_ids_2 to sum up to 3.0 on product_uom_qty
        self.assertEquals(
            3.0, [k.product_uom_qty for k in sale_order.order_line if k.product_id.default_code == "GKK11"][0],
            "Consolidation sum does not add up to the expected 3.0 for GKK11"
        )
        self.assertEquals(
            3.0, [k.product_uom_qty for k in sale_order.order_line if k.product_id.default_code == "FO28"][0],
            "Consolidation sum does not add up to the expected 3.0 for FO84"
        )
