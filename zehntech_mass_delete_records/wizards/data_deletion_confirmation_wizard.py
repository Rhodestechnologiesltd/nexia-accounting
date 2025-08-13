import logging
from odoo import models, fields, api,_
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class DataDeletionConfirmationWizard(models.TransientModel):
    _name = 'data.deletion.confirmation.wizard'
    _description = 'Data Deletion Confirmation Wizard'

    wizard_id = fields.Many2one('mass.clean.wizard', string="Parent Wizard", help="Links this confirmation wizard to its associated mass clean wizard for data deletion.")
    confirmation_message = fields.Text(string=_("Confirmation Message"),  readonly=True,  default=lambda self: _("Are you sure you want to delete all data across all modules? This action cannot be undone."),help="Displays a confirmation message to warn users about the consequences of the deletion action.")

    def action_confirm(self):
        """If confirmed, proceed with the deletion process."""
        if self.wizard_id:
            # Only proceed with deletion if the wizard ID exists
            self._perform_deletion(self.wizard_id)
            # After deletion, close the wizard
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Deletion successful for all modules!'),
                    'type': 'success',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_window_close'  # Close the wizard after the notification
                    }
                }
             }

    def _perform_deletion(self, wizard):
        """Perform the deletion operations, reusing the logic in wizard."""
        data_counts = {}
        if wizard.clean_all:
            # Count data in each module
            data_counts['sales'] = wizard.env['sale.order'].search_count([])
            data_counts['purchases'] = wizard.env['purchase.order'].search_count([])
            data_counts['projects'] = wizard.env['project.project'].search_count([])
            data_counts['tasks'] = wizard.env['project.task'].search_count([])
            data_counts['bom'] = wizard.env['mrp.bom'].search_count([])
            data_counts['manufacturing_orders'] = wizard.env['mrp.production'].search_count([])
            data_counts['journal_entries'] = wizard.env['account.journal'].search_count([])
            data_counts['transfers'] = wizard.env['stock.picking'].search_count([])
            data_counts['invoicing'] = wizard.env['account.payment'].search_count([])

            # Check if there is any data to delete
            any_data_to_delete = any(count > 0 for count in data_counts.values())
            print("Data counts before deletion:", data_counts)
            print("Any data to delete:", any_data_to_delete)

            # If there's no data to delete, display a failure message and exit
            if not any_data_to_delete:
                raise UserError(_("No data found to delete across the modules. Deletion cannot proceed."))
            # Execute the same deletion process as in the parent wizard
            wizard.env['mass.clean.model'].clean_sales()
            wizard._create_audit_log('clean_sales', 'Cleaned all sales and transfers data')
            wizard.env['mass.clean.model'].clean_purchases()
            wizard._create_audit_log('clean_purchases', 'Cleaned all purchase orders and transfers data')
            wizard.env['mass.clean.model'].clean_projects()
            wizard._create_audit_log('clean_projects', f"Cleaned projects. Project IDs: {', '.join(map(str, wizard.project_ids.ids))}")
            wizard.env['mass.clean.model'].clean_inventory()
            wizard.env['mass.clean.model'].clean_tasks()
            wizard._create_audit_log('clean_tasks', f"Cleaned tasks. Task IDs: {', '.join(map(str, wizard.task_ids.ids))}")
            wizard.env['mass.clean.model'].clean_bom()
            wizard._create_audit_log('clean_bom', 'Cleaned BOM and manufacturing orders data')
            wizard.env['mass.clean.model'].clean_manufacturing_orders()
            wizard._create_audit_log('clean_manufacturing_orders', 'Cleaned all manufacturing orders')
            wizard.env['mass.clean.model'].clean_journal_entries()
            wizard._create_audit_log('clean_journal_entries', 'Cleaned journal entries')
            wizard.env['mass.clean.model'].clean_transfers()
            wizard._create_audit_log('clean_transfers', 'Cleaned all transfers')
            wizard.env['mass.clean.model'].clean_invoicing()
            wizard._create_audit_log('clean_invoicing', 'Cleaned all invoicing, payments, and related journal entries')

    def action_cancel(self):
        """Cancel the operation and close the wizard."""
        return {'type': 'ir.actions.act_window_close'}