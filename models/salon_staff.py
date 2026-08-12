from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SalonStaff(models.Model):
    _name = "salon.staff"
    _description = "Salon Staff"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    user_id = fields.Many2one("res.users", string="Related User")
    resource_calendar_id = fields.Many2one("resource.calendar", string="Working Hours")
    color = fields.Integer()
    service_ids = fields.Many2many("salon.service", string="Services")
    booking_ids = fields.One2many("salon.booking", "staff_id", string="Bookings")
    booking_count = fields.Integer(compute="_compute_booking_count")

    _name_company_uniq = models.Constraint(
        "UNIQUE(name, company_id)",
        "A staff member must be unique per company.",
    )

    @api.depends("booking_ids")
    def _compute_booking_count(self):
        grouped = self.env["salon.booking"].with_context(active_test=False)._read_group(
            [("staff_id", "in", self.ids)],
            ["staff_id"],
            ["__count"],
        )
        counts = {staff.id: count for staff, count in grouped}
        for staff in self:
            staff.booking_count = counts.get(staff.id, 0)

    @api.constrains("company_id", "service_ids")
    def _check_service_companies(self):
        for staff in self:
            if any(service.company_id != staff.company_id for service in staff.service_ids):
                raise ValidationError(
                    _("Staff services must belong to the same company as the staff member.")
                )

    def action_view_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_booking_action")
        action["domain"] = [("staff_id", "=", self.id)]
        action["context"] = {
            "default_staff_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action
