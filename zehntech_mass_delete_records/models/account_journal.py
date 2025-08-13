from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    active = fields.Boolean(default=True,help="Indicates whether this journal is active. Set to False to archive the journal and hide it from operational views.")
