from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # Add the active field to enable archiving
    active = fields.Boolean(default=True,help="Indicates whether this transfers is active.")