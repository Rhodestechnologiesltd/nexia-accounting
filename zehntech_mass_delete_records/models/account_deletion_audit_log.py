from odoo import models, fields

class AccountDeletionAuditLog(models.Model):
    _name = 'account.deletion.audit.log'
    _description = 'Audit Log for Deleted Records'

    record_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('journal_entry', 'Journal Entry')
    ], required=True,help="Specifies the type of record that was deleted (Invoice, Payment, or Journal Entry).")
    record_id = fields.Integer(string="Record ID", required=True,help="The unique identifier (ID) of the record that was deleted.")
    deletion_date = fields.Datetime(string="Deletion Date", default=fields.Datetime.now, required=True)
    state = fields.Char(string="State at Deletion", required=True,help="The exact date and time when the record was deleted.")
    additional_info = fields.Text(string="Additional Information",help="Any additional details or comments related to the deleted record.")
