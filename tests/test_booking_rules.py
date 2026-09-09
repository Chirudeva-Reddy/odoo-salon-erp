from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestSalonBookingRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Reminder Customer"})
        cls.service = cls.env["salon.service"].create(
            {
                "name": "Reminder Blowout",
                "company_id": cls.company.id,
                "duration_min": 30,
                "price": 25.0,
                "loyalty_points": 5,
            }
        )
        cls.staff = cls.env["salon.staff"].create(
            {
                "name": "Reminder Staff",
                "company_id": cls.company.id,
                "service_ids": [Command.link(cls.service.id)],
            }
        )

    def _create_booking(self, start_dt):
        return self.env["salon.booking"].create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "staff_id": self.staff.id,
                "start_dt": start_dt,
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

    def test_reminder_cron_notifies_once_inside_lead_time(self):
        self.env["ir.config_parameter"].sudo().set_param("salon_erp.reminder_hours", 24)
        soon = self._create_booking(fields.Datetime.add(fields.Datetime.now(), hours=2))
        later = self._create_booking(fields.Datetime.add(fields.Datetime.now(), days=5))
        soon.action_confirm()
        later.action_confirm()

        self.env["salon.booking"]._cron_send_booking_reminders()

        self.assertTrue(soon.reminder_sent)
        self.assertFalse(later.reminder_sent)

        # A second run must not notify the same booking again.
        before = len(soon.message_ids)
        self.env["salon.booking"]._cron_send_booking_reminders()
        self.assertEqual(len(soon.message_ids), before)

    def test_rescheduling_rearms_the_reminder(self):
        booking = self._create_booking(fields.Datetime.add(fields.Datetime.now(), hours=2))
        booking.action_confirm()
        self.env["salon.booking"]._cron_send_booking_reminders()
        self.assertTrue(booking.reminder_sent)

        booking.write({"start_dt": fields.Datetime.add(fields.Datetime.now(), hours=6)})
        self.assertFalse(booking.reminder_sent)

    def test_canceled_booking_cannot_be_marked_paid(self):
        booking = self._create_booking(fields.Datetime.add(fields.Datetime.now(), days=1))
        booking.action_confirm()
        booking.action_cancel()

        with self.assertRaises(UserError):
            booking.action_mark_paid()

    def test_refunded_booking_cannot_be_marked_paid_again(self):
        booking = self._create_booking(fields.Datetime.add(fields.Datetime.now(), days=2))
        booking.action_confirm()
        booking.action_mark_paid()
        booking.action_mark_refunded()

        with self.assertRaises(UserError):
            booking.action_mark_paid()
