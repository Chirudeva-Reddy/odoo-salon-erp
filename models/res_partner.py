from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    salon_loyalty_balance = fields.Integer(compute="_compute_salon_stats")
    salon_booking_count = fields.Integer(compute="_compute_salon_stats")
    salon_loyalty_entry_count = fields.Integer(compute="_compute_salon_stats")

    @api.depends_context("uid")
    def _compute_salon_stats(self):
        partner_ids = self.ids
        booking_counts = {}
        ledger_counts = {}
        loyalty_balances = {}
        if partner_ids:
            booking_grouped = self.env["salon.booking"].sudo()._read_group(
                [("partner_id", "in", partner_ids)],
                ["partner_id"],
                ["__count"],
            )
            booking_counts = {partner.id: count for partner, count in booking_grouped}
            ledger_count_grouped = self.env["salon.loyalty.ledger"].sudo()._read_group(
                [("partner_id", "in", partner_ids)],
                ["partner_id"],
                ["__count"],
            )
            ledger_counts = {partner.id: count for partner, count in ledger_count_grouped}
            ledger_balance_grouped = self.env["salon.loyalty.ledger"].sudo()._read_group(
                [("partner_id", "in", partner_ids)],
                ["partner_id"],
                ["points:sum"],
            )
            loyalty_balances = {partner.id: points_sum for partner, points_sum in ledger_balance_grouped}
        for partner in self:
            partner.salon_booking_count = booking_counts.get(partner.id, 0)
            partner.salon_loyalty_entry_count = ledger_counts.get(partner.id, 0)
            partner.salon_loyalty_balance = int(round(loyalty_balances.get(partner.id, 0)))

    def action_view_salon_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_booking_action")
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action

    def action_view_salon_loyalty(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_loyalty_action")
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action
