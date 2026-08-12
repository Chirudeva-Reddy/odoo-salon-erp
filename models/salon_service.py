from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SalonServiceCategory(models.Model):
    _name = "salon.service.category"
    _description = "Salon Service Category"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    service_ids = fields.One2many("salon.service", "category_id", string="Services")
    service_count = fields.Integer(compute="_compute_service_count")

    _name_company_uniq = models.Constraint(
        "UNIQUE(name, company_id)",
        "A service category must be unique per company.",
    )

    @api.depends("service_ids")
    def _compute_service_count(self):
        grouped = self.env["salon.service"].with_context(active_test=False)._read_group(
            [("category_id", "in", self.ids)],
            ["category_id"],
            ["__count"],
        )
        counts = {category.id: count for category, count in grouped}
        for category in self:
            category.service_count = counts.get(category.id, 0)

    def action_view_services(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("salon_erp.salon_service_action")
        action["domain"] = [("category_id", "=", self.id)]
        action["context"] = {
            "default_category_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action


class SalonService(models.Model):
    _name = "salon.service"
    _description = "Salon Service"
    _order = "name, id"

    name = fields.Char(required=True, index=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
    )
    duration_min = fields.Integer(required=True, default=30)
    price = fields.Monetary(required=True, default=0.0)
    category_id = fields.Many2one("salon.service.category", string="Category")
    loyalty_points = fields.Integer(default=0)

    _name_company_uniq = models.Constraint(
        "UNIQUE(name, company_id)",
        "A service must be unique per company.",
    )
    _check_duration = models.Constraint(
        "CHECK(duration_min >= 5)",
        "Service duration must be at least 5 minutes.",
    )
    _check_price = models.Constraint(
        "CHECK(price >= 0)",
        "Service price must be positive.",
    )
    _check_loyalty_points = models.Constraint(
        "CHECK(loyalty_points >= 0)",
        "Loyalty points must be positive.",
    )

    @api.constrains("company_id", "category_id")
    def _check_category_company(self):
        for service in self:
            if service.category_id and service.category_id.company_id != service.company_id:
                raise ValidationError(
                    _("Service category must belong to the same company as the service.")
                )
