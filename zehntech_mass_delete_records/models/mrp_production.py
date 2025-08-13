from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    active = fields.Boolean(default=True,help="Indicates whether this Manufacturing orders is active.")
