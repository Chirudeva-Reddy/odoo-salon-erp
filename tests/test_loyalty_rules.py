from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestSalonLoyaltyRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.env["ir.config_parameter"].sudo().set_param("salon_erp.point_value", 1.0)
        cls.partner = cls.env["res.partner"].create({"name": "Loyalty Customer"})
        cls.service = cls.env["salon.service"].create(
            {
                "name": "Loyalty Facial",
                "company_id": cls.company.id,
                "duration_min": 60,
                "price": 50.0,
                "loyalty_points": 20,
            }
        )
        cls.staff = cls.env["salon.staff"].create(
            {
                "name": "Loyalty Staff",
                "company_id": cls.company.id,
                "service_ids": [Command.link(cls.service.id)],
            }
        )

    def _create_booking(self, start_dt, loyalty_points_redeemed=0):
        return self.env["salon.booking"].create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "staff_id": self.staff.id,
                "start_dt": start_dt,
                "loyalty_points_redeemed": loyalty_points_redeemed,
                "service_line_ids": [
                    Command.create(
                        {
                            "service_id": self.service.id,
                            "qty": 1.0,
                            "duration_min": self.service.duration_min,
                            "price_unit": self.service.price,
                        }
                    )
                ],
            }
        )

    def test_paid_done_booking_earns_loyalty(self):
        booking = self._create_booking("2026-04-11 09:00:00")

        booking.action_confirm()
        booking.action_mark_paid()
        booking.action_check_in()
        booking.action_done()

        ledger_entries = self.env["salon.loyalty.ledger"].search(
            [("booking_id", "=", booking.id), ("reason", "=", "earn")]
        )
        self.assertEqual(len(ledger_entries), 1)
        self.assertEqual(ledger_entries.points, 20)
        self.assertEqual(self.partner.salon_loyalty_balance, 20)

    def test_redeem_and_cancel_restore_points(self):
        self.env["salon.loyalty.ledger"].sudo().create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "points": 30,
                "reason": "adjust",
                "ref": "Seed points",
            }
        )
        booking = self._create_booking("2026-04-11 11:00:00", loyalty_points_redeemed=10)

        booking.action_confirm()
        self.assertEqual(self.partner.salon_loyalty_balance, 20)

        booking.action_cancel()
        self.assertEqual(self.partner.salon_loyalty_balance, 30)

        invalid_booking = self._create_booking("2026-04-11 14:00:00", loyalty_points_redeemed=40)
        with self.assertRaises(ValidationError):
            invalid_booking.action_confirm()

    def test_refund_reverses_earned_points(self):
        booking = self._create_booking("2026-04-12 09:00:00")

        booking.action_confirm()
        booking.action_mark_paid()
        booking.action_check_in()
        booking.action_done()
        booking.action_mark_refunded()

        refund_entries = self.env["salon.loyalty.ledger"].search(
            [("booking_id", "=", booking.id), ("reason", "=", "refund"), ("points", "<", 0)]
        )
        self.assertEqual(len(refund_entries), 1)
        self.assertEqual(refund_entries.points, -20)
        self.assertEqual(self.partner.salon_loyalty_balance, 0)
