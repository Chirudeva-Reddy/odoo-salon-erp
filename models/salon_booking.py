from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


ACTIVE_BOOKING_STATES = ("confirmed", "in_service", "done")


class SalonBooking(models.Model):
    _name = "salon.booking"
    _description = "Salon Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_dt desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one("res.partner", required=True, index=True, tracking=True)
    phone = fields.Char(related="partner_id.phone")
    staff_id = fields.Many2one("salon.staff", required=True, index=True, tracking=True)
    start_dt = fields.Datetime(required=True, index=True, tracking=True)
    end_dt = fields.Datetime(compute="_compute_amounts", store=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("in_service", "In Service"),
            ("done", "Done"),
            ("canceled", "Canceled"),
            ("no_show", "No-Show"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    service_line_ids = fields.One2many("salon.booking.line", "booking_id", string="Services")
    total_duration_min = fields.Integer(compute="_compute_amounts", store=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)
    amount_untaxed = fields.Monetary(compute="_compute_amounts", store=True)
    loyalty_redemption_value = fields.Monetary(compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(compute="_compute_amounts", store=True)
    payment_state = fields.Selection(
        [
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
        ],
        default="unpaid",
        tracking=True,
    )
    payment_ref = fields.Char(copy=False)
    loyalty_points_redeemed = fields.Integer(default=0, tracking=True)
    loyalty_points_earned = fields.Integer(compute="_compute_loyalty_points_earned", store=True)
    cancel_reason = fields.Text(copy=False)
    canceled_at = fields.Datetime(copy=False)
    note = fields.Text()
    loyalty_ledger_count = fields.Integer(compute="_compute_stat_buttons")
    customer_booking_count = fields.Integer(compute="_compute_stat_buttons")
    has_loyalty_redeemed = fields.Boolean(default=False, copy=False, readonly=True)
    has_loyalty_earned = fields.Boolean(default=False, copy=False, readonly=True)
    has_redemption_restored = fields.Boolean(default=False, copy=False, readonly=True)
    has_earn_refunded = fields.Boolean(default=False, copy=False, readonly=True)

    _check_redeemed_points = models.Constraint(
        "CHECK(loyalty_points_redeemed >= 0)",
        "Redeemed loyalty points cannot be negative.",
    )

    @api.depends(
        "service_line_ids.qty",
        "service_line_ids.duration_min",
        "service_line_ids.subtotal",
        "start_dt",
        "loyalty_points_redeemed",
    )
    def _compute_amounts(self):
        point_value = self._get_point_value()
        for booking in self:
            total_duration = sum(line.duration_min * line.qty for line in booking.service_line_ids)
            booking.total_duration_min = int(round(total_duration))
            booking.end_dt = (
                fields.Datetime.add(booking.start_dt, minutes=booking.total_duration_min)
                if booking.start_dt and booking.total_duration_min > 0
                else False
            )
            booking.amount_untaxed = sum(booking.service_line_ids.mapped("subtotal"))
            booking.loyalty_redemption_value = booking.loyalty_points_redeemed * point_value
            booking.amount_total = max(
                booking.amount_untaxed - booking.loyalty_redemption_value,
                0.0,
            )

    @api.depends("service_line_ids.service_id", "service_line_ids.qty")
    def _compute_loyalty_points_earned(self):
        for booking in self:
            total_points = sum(line.service_id.loyalty_points * line.qty for line in booking.service_line_ids)
            booking.loyalty_points_earned = int(round(total_points))

    @api.depends("partner_id", "partner_id.salon_booking_count")
    def _compute_stat_buttons(self):
        loyalty_grouped = self.env["salon.loyalty.ledger"].sudo()._read_group(
            [("booking_id", "in", self.ids)],
            ["booking_id"],
            ["__count"],
        )
        loyalty_counts = {booking.id: count for booking, count in loyalty_grouped}
        for booking in self:
            booking.loyalty_ledger_count = loyalty_counts.get(booking.id, 0)
            booking.customer_booking_count = booking.partner_id.salon_booking_count

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("salon.booking") or _("New")
        return super().create(vals_list)

    @api.constrains("staff_id", "company_id")
    def _check_staff_company(self):
        for booking in self:
            if booking.staff_id and booking.staff_id.company_id != booking.company_id:
                raise ValidationError(
                    _("The selected staff member must belong to the same company as the booking.")
                )

    @api.constrains("start_dt", "end_dt")
    def _check_start_before_end(self):
        for booking in self:
            if booking.start_dt and booking.end_dt and booking.end_dt <= booking.start_dt:
                raise ValidationError(_("Booking end time must be after the start time."))

    @api.constrains("start_dt", "end_dt", "staff_id", "company_id", "state")
    def _check_no_overlap(self):
        for booking in self.filtered(
            lambda record: (
                record.staff_id
                and record.start_dt
                and record.end_dt
                and record.state in ACTIVE_BOOKING_STATES
            )
        ):
            overlap_domain = [
                ("id", "!=", booking.id),
                ("company_id", "=", booking.company_id.id),
                ("staff_id", "=", booking.staff_id.id),
                ("state", "in", ACTIVE_BOOKING_STATES),
                ("start_dt", "<", booking.end_dt),
                ("end_dt", ">", booking.start_dt),
            ]
            if self.search_count(overlap_domain):
                raise ValidationError(
                    _("Booking conflict: the selected staff member is already booked during this time.")
                )

    def _get_point_value(self):
        return float(
            self.env["ir.config_parameter"].sudo().get_param("salon_erp.point_value", default=1.0)
        )

    def _check_before_confirmation(self):
        for booking in self:
            if not booking.service_line_ids:
                raise ValidationError(_("Add at least one service before confirming a booking."))
            if booking.total_duration_min <= 0 or not booking.end_dt:
                raise ValidationError(_("Booking duration must be positive before confirmation."))
            if booking.loyalty_points_redeemed > booking.partner_id.salon_loyalty_balance:
                raise ValidationError(_("The customer does not have enough loyalty points to redeem."))
            if booking.loyalty_redemption_value > booking.amount_untaxed:
                raise ValidationError(_("Redeemed loyalty points cannot exceed the booking amount."))

    def _create_loyalty_move(self, points, reason, ref):
        self.ensure_one()
        if not points:
            return
        self.env["salon.loyalty.ledger"].sudo().create(
            {
                "company_id": self.company_id.id,
                "partner_id": self.partner_id.id,
                "booking_id": self.id,
                "points": points,
                "reason": reason,
                "ref": ref,
                "user_id": self.env.user.id,
            }
        )

    def _restore_redeemed_points(self):
        for booking in self.filtered(
            lambda record: record.has_loyalty_redeemed
            and not record.has_redemption_restored
            and record.loyalty_points_redeemed
        ):
            booking._create_loyalty_move(
                booking.loyalty_points_redeemed,
                "refund",
                _("Redemption restored for %s") % booking.name,
            )
            booking.has_redemption_restored = True

    def _earn_loyalty_points(self):
        for booking in self.filtered(
            lambda record: record.state == "done"
            and record.payment_state == "paid"
            and record.loyalty_points_earned
            and not record.has_loyalty_earned
        ):
            booking._create_loyalty_move(
                booking.loyalty_points_earned,
                "earn",
                _("Points earned for %s") % booking.name,
            )
            booking.has_loyalty_earned = True

    def _refund_earned_points(self):
        for booking in self.filtered(
            lambda record: record.has_loyalty_earned
            and not record.has_earn_refunded
            and record.loyalty_points_earned
        ):
            booking._create_loyalty_move(
                -booking.loyalty_points_earned,
                "refund",
                _("Points reversed for %s") % booking.name,
            )
            booking.has_earn_refunded = True

    def _check_state_transition(self, allowed_states, target_label):
        for booking in self:
            if booking.state not in allowed_states:
                raise UserError(
                    _("Only bookings in %s can be moved to %s.")
                    % (", ".join(allowed_states), target_label)
                )

    def action_confirm(self):
        self._check_state_transition(("draft",), _("Confirmed"))
        self._check_before_confirmation()
        self.write({"state": "confirmed"})
        for booking in self:
            if booking.loyalty_points_redeemed and not booking.has_loyalty_redeemed:
                booking._create_loyalty_move(
                    -booking.loyalty_points_redeemed,
                    "redeem",
                    _("Points redeemed for %s") % booking.name,
                )
                booking.has_loyalty_redeemed = True
            booking.message_post(body=_("Booking confirmed."))
        return True

    def action_check_in(self):
        self._check_state_transition(("confirmed",), _("In Service"))
        self.write({"state": "in_service"})
        for booking in self:
            booking.message_post(body=_("Customer checked in."))
        return True

    def action_done(self):
        self._check_state_transition(("in_service",), _("Done"))
        self.write({"state": "done"})
        self._earn_loyalty_points()
        for booking in self:
            booking.message_post(body=_("Booking completed."))
        return True

    def action_cancel(self):
        self._check_state_transition(("draft", "confirmed", "in_service"), _("Canceled"))
        now = fields.Datetime.now()
        self.write({"state": "canceled", "canceled_at": now})
        self._restore_redeemed_points()
        for booking in self:
            booking.message_post(body=_("Booking canceled."))
        return True

    def action_no_show(self):
        self._check_state_transition(("confirmed", "in_service"), _("No-Show"))
        now = fields.Datetime.now()
        self.write({"state": "no_show", "canceled_at": now})
        self._restore_redeemed_points()
        for booking in self:
            booking.message_post(body=_("Booking marked as no-show."))
        return True

    def action_mark_paid(self):
        self.write({"payment_state": "paid"})
        self._earn_loyalty_points()
        for booking in self:
            booking.message_post(body=_("Payment marked as paid."))
        return True

    def action_mark_refunded(self):
        for booking in self:
            if booking.payment_state != "paid":
                raise UserError(_("Only paid bookings can be refunded."))
        self.write({"payment_state": "refunded"})
        self._refund_earned_points()
        for booking in self:
            booking.message_post(body=_("Payment marked as refunded."))
        return True

    def action_view_loyalty_ledger(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_loyalty_action")
        action["domain"] = [("booking_id", "=", self.id)]
        action["context"] = {
            "default_partner_id": self.partner_id.id,
            "default_booking_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action

    def action_view_customer_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_booking_action")
        action["domain"] = [("partner_id", "=", self.partner_id.id)]
        action["context"] = {"default_partner_id": self.partner_id.id}
        return action
