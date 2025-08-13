from odoo import models, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    active = fields.Boolean(default=True,help="Indicates whether this bom is active.")
