from odoo import models, fields, api,_

class MassCleanConfirmationWizard(models.TransientModel):
    _name = 'mass.clean.confirmation.wizard'
    _description = 'Confirmation Wizard for Mass Clean Operations'

    summary_text = fields.Text("Summary of Records to be Deleted", readonly=True, help="Provides an overview of the records that will be deleted during the mass clean operation. This field is read-only and auto-populated for review.")

    @api.model
    def default_get(self, fields):
        res = super(MassCleanConfirmationWizard, self).default_get(fields)
        res['summary_text'] = self.env.context.get('summary_text', '')  # Get summary text from context
        return res

    def action_confirm_deletion(self):
        # Perform deletion logic here
        wizard = self.env['mass.clean.wizard'].browse(self.env.context.get('wizard_id'))
        if wizard:
            if wizard.project_ids:
                wizard.project_ids.sudo().unlink()
            if wizard.task_ids:
                wizard.task_ids.sudo().unlink()
         # Retrieve summary text from the context or wizard for the success message
        summary_text = self.env.context.get('summary_text', 'No records selected for deletion.')
 
         # Return success message with summary
        return {
             'type': 'ir.actions.client',
             'tag': 'display_notification',
             'params': {
                 'title': _('Deletion Successful'),
	             'message': _('Deletion complete! %s') % summary_text, 
                 'type': 'success',
                 'sticky': True,
                 'next': {
                     'type': 'ir.actions.act_window_close'
                 }
             }
         }
