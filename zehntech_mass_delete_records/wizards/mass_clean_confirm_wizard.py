import logging
from odoo import models, fields, _

_logger = logging.getLogger(__name__)

class MassCleanConfirmWizard(models.TransientModel):
    _name = 'mass.clean.confirm.wizard'
    _description = 'Confirmation for Mass Clean'

    def action_confirm(self):
        """Confirm deletion action with a pre-check for the number of orders."""
        # Default message in case no deletions happen
        message = _('Action on invoicing and journal performed.')

        # Flags to check if specific deletions are done
        sales_and_transfers_deleted = False
        transfers_deleted = False
        invoicing_deleted = False
        journal_entries_deleted = False

        # Pre-check for records before deletion
        sales_count = self.env['sale.order'].search_count([])
        transfers_count = self.env['stock.picking'].search_count([])
        invoice_count = self.env['account.move'].search_count([('move_type', 'in', ['out_invoice', 'in_invoice'])])
        payment_count = self.env['account.payment'].search_count([])  # Count payments, not payment terms
        journal_count = self.env['account.journal'].search_count([('active', '=', True)])

        # Check for journal entries, only active ones
        journal_entries_count = self.env['account.journal'].search_count([('active', '=', True)])

        # Log journal entry count for debugging
        _logger.info("Journal Entries Count (Pre-Deletion): %d", journal_entries_count)

        # If no relevant records, show a warning notification and exit
        if self.env.context.get('clean_sales') and sales_count == 0:
            return self._show_warning(_('No Sales Orders found to delete.'))
        if self.env.context.get('clean_only_transfers') and transfers_count == 0:
            return self._show_warning(_('No Transfers found to delete.'))
        if self.env.context.get('clean_invoicing') and invoice_count == 0 and payment_count == 0 and journal_count == 0:
            return self._show_warning(_('No Invoices found to delete.'))
        if self.env.context.get('clean_only_journal_entries') and journal_entries_count == 0:
            return self._show_warning(_('No Journal Entries found to delete.'))

        # Perform deletion actions based on context
        if self.env.context.get('clean_sales'):
            self.env['mass.clean.model'].clean_sales()
            if self.env.context.get('clean_only_transfers'):
                self.env['mass.clean.model'].clean_transfers()
                sales_and_transfers_deleted = True
            else:
                sales_and_transfers_deleted = True

        if self.env.context.get('clean_only_transfers') and not self.env.context.get('clean_sales'):
            self.env['mass.clean.model'].clean_transfers()
            transfers_deleted = True

        if self.env.context.get('clean_invoicing'):
            # Check if there are any invoices, payments, or journal entries before deletion
            invoice_count = self.env['account.move'].search_count([('move_type', 'in', ['out_invoice', 'in_invoice'])])
            payment_count = self.env['account.payment'].search_count([])  # Count payments, not payment terms
            journal_count = self.env['account.journal'].search_count([('active', '=', True)])

            _logger.info("Invoice Count before deletion: %d", invoice_count)
            _logger.info("Payment Count before deletion: %d", payment_count)
            _logger.info("Journal Count before deletion: %d", journal_count)

            # If any of the invoice, payment, or journal exists, proceed with deletion
            if invoice_count > 0 or payment_count > 0 or journal_count > 0:
                self.env['mass.clean.model'].clean_invoicing()  # Assuming you have a method for this
                invoicing_deleted = True
            else:
                # Show warning if no invoicing, payment, or journal entries to delete
                return self._show_warning(_('No invoices, payments, or journal entries to delete.'))

        if self.env.context.get('clean_only_journal_entries'):
            # Before cleaning journal entries, check if any are left
            if journal_entries_count > 0:
                self.env['mass.clean.model'].clean_journal_entries()
                journal_entries_deleted = True
            else:
                # Show warning if no journal entries to delete
                return self._show_warning(_('No journal entries to delete.'))

        # Check the count again after deletion to ensure it's updated
        journal_entries_count_after = self.env['account.journal'].search_count([('active', '=', True)])

        # Log journal entry count after deletion for debugging
        _logger.info("Journal Entries Count (Post-Deletion): %d", journal_entries_count_after)

        # Determine the success message based on deletion type
        if sales_and_transfers_deleted:
            message = _('Sales and all transfers deleted!')
        elif transfers_deleted:
            message =  _('Transfers deleted!')
        elif invoicing_deleted:
            message = _('Invoicing, payments & journal entries deleted!')
        elif journal_entries_deleted:
            message = _('Only journal entries deleted!')

        # Show success message after deletion
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }

    def action_cancel(self):
        """Cancel the deletion and close the wizard without proceeding with any data deletion."""
        return {
            'type': 'ir.actions.act_window_close'
        }

    def _show_warning(self, message):
        """Helper method to show a warning notification."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Warning'),
                'message': message,
                'type': 'warning',
                'sticky': True,
            }
        }
