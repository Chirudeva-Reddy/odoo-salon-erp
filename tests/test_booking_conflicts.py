from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user


class TestSalonBookingConflicts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Salon Branch B"})
        cls.partner = cls.env["res.partner"].create({"name": "Booking Test Customer"})
        cls.service_a = cls.env["salon.service"].create(
            {
                "name": "Test Haircut",
                "company_id": cls.company_a.id,
                "duration_min": 60,
                "price": 40.0,
                "loyalty_points": 12,
            }
        )
        cls.service_b = cls.env["salon.service"].create(
            {
                "name": "Branch B Haircut",
                "company_id": cls.company_b.id,
                "duration_min": 60,
                "price": 45.0,
                "loyalty_points": 12,
            }
        )
        cls.reception_user = new_test_user(
            cls.env,
            login="salon_reception",
            groups="base.group_user,salon_erp.group_salon_user",
            company_id=cls.company_a.id,
        )
        cls.staff_user = new_test_user(
            cls.env,
            login="salon_staff",
            groups="base.group_user,salon_erp.group_salon_staff",
            company_id=cls.company_a.id,
        )
        cls.staff_a = cls.env["salon.staff"].create(
            {
                "name": "Staff A",
                "company_id": cls.company_a.id,
                "user_id": cls.staff_user.id,
                "service_ids": [Command.link(cls.service_a.id)],
            }
        )
        cls.staff_a_other = cls.env["salon.staff"].create(
            {
                "name": "Staff A Other",
                "company_id": cls.company_a.id,
                "service_ids": [Command.link(cls.service_a.id)],
            }
        )
        cls.staff_b = cls.env["salon.staff"].create(
            {
                "name": "Staff B",
                "company_id": cls.company_b.id,
                "service_ids": [Command.link(cls.service_b.id)],
            }
        )

    def _create_booking(self, start_dt, staff, partner=None, company=None):
        company = company or staff.company_id
        service = self.service_a if company == self.company_a else self.service_b
        partner = partner or self.partner
        return self.env["salon.booking"].create(
            {
                "company_id": company.id,
                "partner_id": partner.id,
                "staff_id": staff.id,
                "start_dt": start_dt,
                "service_line_ids": [
                    Command.create(
                        {
                            "service_id": service.id,
                            "qty": 1.0,
                            "duration_min": service.duration_min,
                            "price_unit": service.price,
                        }
                    )
                ],
            }
        )

    def test_overlapping_confirmed_bookings_are_blocked(self):
        first = self._create_booking("2026-04-08 10:00:00", self.staff_a)
        second = self._create_booking("2026-04-08 10:30:00", self.staff_a)

        first.action_confirm()
        with self.assertRaises(ValidationError):
            second.action_confirm()

    def test_overlapping_draft_bookings_are_allowed(self):
        first = self._create_booking("2026-04-08 12:00:00", self.staff_a)
        second = self._create_booking("2026-04-08 12:30:00", self.staff_a)

        self.assertEqual(first.state, "draft")
        self.assertEqual(second.state, "draft")

    def test_lifecycle_flow(self):
        booking = self._create_booking("2026-04-09 09:00:00", self.staff_a)

        booking.action_confirm()
        booking.action_check_in()
        booking.action_done()

        self.assertEqual(booking.state, "done")

    def test_calendar_style_reschedule_uses_same_overlap_rule(self):
        first = self._create_booking("2026-04-09 13:00:00", self.staff_a)
        second = self._create_booking("2026-04-09 15:00:00", self.staff_a)
        first.action_confirm()
        second.action_confirm()

        with self.assertRaises(ValidationError):
            second.write({"start_dt": "2026-04-09 13:30:00"})

    def test_record_rules_limit_company_and_staff_visibility(self):
        own_booking = self._create_booking("2026-04-10 09:00:00", self.staff_a)
        other_same_company = self._create_booking("2026-04-10 11:00:00", self.staff_a_other)
        other_company = self._create_booking(
            "2026-04-10 14:00:00",
            self.staff_b,
            company=self.company_b,
        )

        reception_visible = self.env["salon.booking"].with_user(self.reception_user).search([])
        staff_visible = self.env["salon.booking"].with_user(self.staff_user).search([])

        self.assertIn(own_booking, reception_visible)
        self.assertIn(other_same_company, reception_visible)
        self.assertNotIn(other_company, reception_visible)

        self.assertIn(own_booking, staff_visible)
        self.assertNotIn(other_same_company, staff_visible)
        self.assertNotIn(other_company, staff_visible)
