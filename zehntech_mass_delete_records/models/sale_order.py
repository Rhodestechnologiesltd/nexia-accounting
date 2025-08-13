from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    active = fields.Boolean(default=True,help="Indicates whether this sale order is active.")
