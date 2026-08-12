from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SalonBookingLine(models.Model):
    _name = "salon.booking.line"
    _description = "Salon Booking Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    booking_id = fields.Many2one("salon.booking", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", related="booking_id.company_id", store=True, index=True)
    currency_id = fields.Many2one("res.currency", related="booking_id.currency_id", store=True)
    service_id = fields.Many2one("salon.service", required=True)
    qty = fields.Float(default=1.0, required=True)
    duration_min = fields.Integer(required=True, default=30)
    price_unit = fields.Monetary(required=True, default=0.0)
    discount_pct = fields.Float(default=0.0)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)
    notes = fields.Char()

    _check_qty = models.Constraint("CHECK(qty > 0)", "Quantity must be positive.")
    _check_duration = models.Constraint(
        "CHECK(duration_min > 0)",
        "Duration must be positive.",
    )

    @api.depends("qty", "price_unit", "discount_pct")
    def _compute_subtotal(self):
        for line in self:
            discount_factor = 1 - (line.discount_pct / 100.0)
            line.subtotal = line.qty * line.price_unit * discount_factor

    @api.onchange("service_id")
    def _onchange_service_id(self):
        for line in self:
            if line.service_id:
                line.duration_min = line.service_id.duration_min
                line.price_unit = line.service_id.price
                line.notes = line.service_id.description

    @api.constrains("discount_pct")
    def _check_discount_pct(self):
        for line in self:
            if line.discount_pct < 0 or line.discount_pct > 100:
                raise ValidationError(_("Discount must stay between 0 and 100 percent."))

    @api.constrains("service_id", "company_id")
    def _check_service_company(self):
        for line in self:
            if line.service_id and line.company_id and line.service_id.company_id != line.company_id:
                raise ValidationError(
                    _("Booking lines can only use services from the same company as the booking.")
                )

    def action_reload_service_defaults(self):
        for line in self:
            if line.service_id:
                line.write(
                    {
                        "duration_min": line.service_id.duration_min,
                        "price_unit": line.service_id.price,
                        "notes": line.service_id.description,
                    }
                )
        return True
