from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SalonLoyaltyLedger(models.Model):
    _name = "salon.loyalty.ledger"
    _description = "Salon Loyalty Ledger"
    _order = "move_dt desc, id desc"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one("res.partner", required=True, index=True)
    booking_id = fields.Many2one("salon.booking", index=True, ondelete="set null")
    move_dt = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    points = fields.Integer(required=True)
    reason = fields.Selection(
        [
            ("earn", "Earn"),
            ("redeem", "Redeem"),
            ("adjust", "Adjust"),
            ("refund", "Refund"),
        ],
        required=True,
    )
    ref = fields.Char()
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)

    _check_points_nonzero = models.Constraint(
        "CHECK(points != 0)",
        "Loyalty points must be non-zero.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        entries = super().create(vals_list)
        entries._invalidate_related_caches()
        return entries

    def write(self, vals):
        # An empty recordset must stay a no-op: the ORM calls write()/unlink()
        # on empty sets as a matter of course, and raising there breaks it.
        if self:
            raise UserError(_("Loyalty ledger entries cannot be modified."))
        return super().write(vals)

    def unlink(self):
        if self:
            raise UserError(_("Loyalty ledger entries cannot be deleted."))
        return super().unlink()

    def _invalidate_related_caches(self):
        partners = self.partner_id
        if partners:
            partners.invalidate_recordset(
                ["salon_loyalty_balance", "salon_loyalty_entry_count"]
            )
        bookings = self.booking_id
        if bookings:
            bookings.invalidate_recordset(["loyalty_ledger_count"])
