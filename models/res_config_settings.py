from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    salon_point_value = fields.Float(
        string="Point Value",
        config_parameter="salon_erp.point_value",
        default=1.0,
    )
    salon_reminder_hours = fields.Integer(
        string="Reminder Lead Time",
        config_parameter="salon_erp.reminder_hours",
        default=24,
    )
