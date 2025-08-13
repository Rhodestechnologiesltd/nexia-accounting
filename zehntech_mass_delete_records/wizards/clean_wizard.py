import logging
from odoo import models, fields,api,_
from odoo.exceptions import ValidationError, UserError,AccessError
from psycopg2 import errors
_logger = logging.getLogger(__name__)

class MassCleanWizard(models.TransientModel):
    _name = 'mass.clean.wizard'
    _description = 'Mass Clean Wizard'

    # Fields declaration
    clean_all = fields.Boolean("Clean All Data",help="Select this option to clean all data across all modules.")
    clean_sales = fields.Boolean("Sales & All Transfers", help="Delete all sales orders and their associated transfers.")
    clean_purchases = fields.Boolean("Purchase & All Transfers", help="Delete all purchase orders and their associated transfers.")
    clean_only_transfers = fields.Boolean("Only Transfers",help="Delete only transfer records without affecting other data.")
    clean_projects = fields.Boolean("Project, Tasks & Timesheets", help="Delete all projects, tasks, and timesheet entries.")
    clean_only_tasks = fields.Boolean("Only Tasks & Timesheets", help="Delete only task and timesheet entries, leaving projects intact.")
    clean_customers_vendors = fields.Boolean("Customers & Vendors",help="Delete all customer and vendor records.")
    clean_bom = fields.Boolean("BOM & Manufacturing Orders",help="Delete all Bill of Materials and associated manufacturing orders.")
    clean_only_manufacturing = fields.Boolean("Only Manufacturing Orders", help="Delete only manufacturing orders, leaving BOMs intact.")
    clean_invoicing = fields.Boolean("All Invoicing, Payments & Journal Entries",help="Delete all invoicing data, including payments and journal entries.")
    clean_only_journal_entries = fields.Boolean("Only Journal Entries",help="Delete only journal entries, leaving invoicing and payment data intact.")
    clean_chart_of_accounts = fields.Boolean("Chart of Accounts & All Accounting Data",help="Delete the chart of accounts and all associated accounting data.")
    project_ids = fields.Many2many('project.project', string="Select Projects to Clean",help="Manually select specific projects to clean.")
    task_ids = fields.Many2many('project.task', string="Select Tasks to Clean",help="Manually select specific tasks to clean.")
    summary_text = fields.Text("Summary of Records to be Deleted", readonly=True,help="Displays a summary of records that will be deleted based on selected options.")
    @api.onchange('clean_all')
    def _onchange_clean_all(self):
        """Automatically select/deselect related options when 'Clean All Data' is toggled."""
        if self.clean_all:
            self.clean_sales = True
            self.clean_purchases = True
            self.clean_projects = True
            self.clean_only_transfers = True
            self.clean_only_tasks = True
            self.clean_customers_vendors = True
            self.clean_bom = True
            self.clean_only_manufacturing = True
            self.clean_invoicing = True
            self.clean_only_journal_entries = True
            self.clean_chart_of_accounts = True
        else:
            self.clean_sales = False
            self.clean_purchases = False
            self.clean_projects = False
            self.clean_only_transfers = False
            self.clean_only_tasks = False
            self.clean_customers_vendors = False
            self.clean_bom = False
            self.clean_only_manufacturing = False
            self.clean_invoicing = False
            self.clean_only_journal_entries = False
            self.clean_chart_of_accounts = False
    # Existing fields...
    clean_manufacturing_option = fields.Selection([
        ('delete_ongoing', 'Delete Ongoing Orders'),
        ('archive_done', 'Archive Done Orders'),
    ], string="Select Action", help="Choose what to do with manufacturing orders.")
    def _create_audit_log(self, action, description):
        """Helper method to create an audit log entry."""
        self.env['audit.log'].create({
            'user_id': self.env.user.id,
            'action_type': 'delete',
            # 'description': description,
            'model_name': 'mass.clean.wizard',
        })



    def action_clean_data(self):
        """Method to trigger cleaning based on the selected options."""
        summary = {
            'projects': len(self.project_ids),
            'tasks': len(self.task_ids),
        }
        # Check if "Clean All" is selected, then log the action
        if self.clean_all:
            return {
            'name': _('Confirm Deletion'),
            'type': 'ir.actions.act_window',
            'res_model': 'data.deletion.confirmation.wizard',  # Updated model name
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,  # Pass the current wizard ID
            },
        }
        else:
            selected_options = [
            self.clean_sales, self.clean_purchases, self.clean_projects,
            self.clean_only_transfers, self.clean_only_tasks, self.clean_customers_vendors,
            self.clean_bom, self.clean_only_manufacturing, self.clean_invoicing,
            self.clean_only_journal_entries, self.clean_chart_of_accounts
        ]
                # Check if Projects or Tasks are selected
            if self.project_ids:
                selected_options.append(True)  # Indicating that Projects are selected
            else:
                selected_options.append(False)

            if self.task_ids:
                selected_options.append(True)  # Indicating that Tasks are selected
            else:
                selected_options.append(False)

            
        
            _logger.info("Selected options: %s", selected_options)
            if sum(selected_options) > 1 and sum(selected_options) < len(selected_options):
                # Call the _perform_selected_modules_deletion function
                return {
                    'type': 'ir.actions.act_window',
                    'name':  _('Confirm Deletion'),
                    'res_model': 'confirm.deletion.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_wizard_id': self.id,  # To associate the wizard with this action
                    }
                }
                    # Check if no options are selected
            if not (self.clean_all or self.clean_sales or self.clean_only_transfers or self.clean_purchases or self.clean_bom or self.task_ids or self.project_ids or
                    self.clean_only_manufacturing or self.clean_only_journal_entries or self.clean_only_tasks or self.clean_chart_of_accounts or self.clean_invoicing):
                raise UserError(_("Please select at least one option to proceed with the data cleaning."))
            # Prepare summary text
            summary_text = []

            if self.project_ids or self.task_ids:
                # Create summaries for projects and tasks
                if self.project_ids:
                    # Check if the user is a 'Project Manager'
                        is_project_manager = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

                        # Log the result of the group check
                        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager)

                        # Step 0: Check if the user has access
                        if not is_project_manager:
                            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
                            raise AccessError(_("You do not have permission to delete projects or tasks."))
                        project_names = ', '.join(project.name for project in self.project_ids)
                        summary_text.append(_("Projects to delete/archive: %(count)s - %(names)s") % {'count': len(self.project_ids),'names': project_names})
                        # Log the successful check and attempt to clean projects
                        self.env['audit.log'].create({
                            'user_id': self.env.user.id,
                            'action_type': 'delete',
                            'model_name': 'project.project',
                            'record_name': project_names,
                            'details': _("User %(user_name)s is attempting to delete/archive projects: %(project_names)s") % {'user_name': self.env.user.name,'project_names': project_names}

                        })
                if self.task_ids:
                    # Check if the user is a 'Project Manager'
                        is_project_manager = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

                        # Log the result of the group check
                        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager)

                        # Step 0: Check if the user has access
                        if not is_project_manager:
                            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
                            raise AccessError(_("You do not have permission to delete projects or tasks."))
                        task_names = ', '.join(task.name for task in self.task_ids)
                        summary_text.append(_("Tasks to delete/archive: %(count)s - %(names)s") % {'count': len(self.task_ids),'names': task_names})
                        # Log the successful check and attempt to clean tasks
                        self.env['audit.log'].create({
                            'user_id': self.env.user.id,
                            'action_type': 'delete',
                            'model_name': 'project.task',
                            'record_name': task_names,
                            'details': _("User %(user_name)s is attempting to delete/archive tasks: %(task_names)s") % {'user_name': self.env.user.name,'task_names': task_names}
                        })

                # Set summary text for display
                self.summary_text = "\n".join(summary_text)

                # Call deletion or archiving functionality
                self.confirm_delete_or_archive()

                    # Open confirmation dialog
                return {
                    'name':  _('Confirm Deletion'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.confirmation.wizard',  # Ensure the model name is correct
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'wizard_id': self.id,  # Pass current wizard ID
                        'summary_text': summary_text,  # Pass summary text
                    },
                }
            if self.clean_sales or self.clean_only_transfers:
                # self.env['mass.clean.model'].clean_transfers()
                # Confirmation dialog
                return {
                    'name':  _('Confirm Deletion'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'clean_sales': self.clean_sales,
                        'clean_only_transfers': self.clean_only_transfers,
                    },
                }
            if self.clean_purchases:
                # If clean_purchases is True, trigger the purchase wizard
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Clean Purchase Orders'),
                    'res_model': 'purchase.clean.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                }
            if self.project_ids:
                try:
                    self.project_ids.sudo().unlink()
                except Exception as e:
                    _logger.error("Error deleting selected projects: %s", e)
                    raise ValidationError(_("Failed to delete some selected projects. Check permissions or dependencies."))
            if self.task_ids:
                try:
                    self.task_ids.sudo().unlink()
                except Exception as e:
                    _logger.error("Error deleting selected tasks: %s", e)
                    raise ValidationError(_("Failed to delete some selected tasks. Check permissions or dependencies."))
            
            if self.clean_bom:
                self.env['mass.clean.model'].clean_bom()
                return {
                    'name': _('Select Manufacturing Order Action'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.manufacturing.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'wizard_id': self.id,
                    },
                }
            if self.clean_only_manufacturing:
                # Check if the user is a 'Manufacturing Manager'
                is_manufacturing_manager = self.env.user.has_group('zehntech_mass_delete_records.group_manufacturing_manager')

                # Log the result of the group check
                _logger.info("Manufacturing Manager group check for user %s: %s", self.env.user.name, is_manufacturing_manager)

                # Step 0: Check if the user has access
                if not is_manufacturing_manager:
                    _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
                    raise AccessError(_("You do not have permission to delete Manufacturing Orders."))
                # Log this action in the audit log
                self.env['audit.log'].create({
                        'user_id': self.env.user.id,
                        'action_type': 'delete',
                        'model_name': 'mrp.production',
                        'record_name': 'Manufacturing Orders',
                        'details': _("User %(user_name)s is authorized to delete Manufacturing Orders.") % {'user_name': self.env.user.name}
                })
                return {
                    'name': _('Select Manufacturing Order Action'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.manufacturing.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'wizard_id': self.id,
                    },
                }
            if self.clean_only_journal_entries:
                return {
                    'name': _('Confirm Deletion'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'clean_only_journal_entries': self.clean_only_journal_entries, 
                    },
                }
            if self.clean_only_transfers:
                _logger.info("Cleaning only transfers...")
                
                self.env['mass.clean.model'].clean_transfers()
                
                return {
                    'name':  _('Confirm Deletion'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'clean_sales': self.clean_only_transfers,
                    },
                }
            if self.clean_only_tasks:
                self.env['mass.clean.model'].clean_tasks()
            if self.clean_chart_of_accounts:
                self.env['mass.clean.model'].clean_accounting()
            if self.clean_invoicing:
                return {
                    'name':  _('Confirm Deletion'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mass.clean.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                                'clean_invoicing': True,
                    },
                }
                
        # Show success message and return an action to close the wizard after notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Deletion successful!'),
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close'  # Close the wizard after the notification
                }
            }
        }


    def _perform_selected_modules_deletion(self):
        no_data_modules = []

        if self.clean_sales:
            sales_data = self.env['sale.order'].search([])
            if sales_data:
                self.env['mass.clean.model'].clean_sales()
                self._create_audit_log('clean_sales', 'Cleaned all sales and transfers data')
            else:
                no_data_modules.append('Sales')

        if self.clean_purchases:
            purchase_data = self.env['purchase.order'].search([])
            if purchase_data:
                self.env['mass.clean.model'].clean_purchases()
                self._create_audit_log('clean_purchases', 'Cleaned all purchase orders and transfers data')
            else:
                no_data_modules.append('Purchases')

        if self.clean_bom:
            bom_data = self.env['mrp.bom'].search([])
            if bom_data:
                self.env['mass.clean.model'].clean_bom()
                self._create_audit_log('clean_bom', 'Cleaned BOM and manufacturing orders data')
            else:
                no_data_modules.append('BOM')

        if self.clean_only_manufacturing:
            manufacturing_data = self.env['mrp.production'].search([])
            if manufacturing_data:
                self.env['mass.clean.model'].clean_manufacturing_orders()
                self._create_audit_log('clean_manufacturing_orders', 'Cleaned all manufacturing orders')
            else:
                no_data_modules.append('Manufacturing Orders')

        if self.clean_invoicing:
            invoicing_data = self.env['account.move'].search([('move_type', '=', 'out_invoice')])
            if invoicing_data:
                self.env['mass.clean.model'].clean_invoicing()
                self._create_audit_log('clean_invoicing', 'Cleaned all invoicing, payments, and related journal entries')
            else:
                no_data_modules.append('Invoicing')

        if self.clean_only_journal_entries:
            journal_data = self.env['account.journal'].search_count([('active', '=', True)])
            if journal_data:
                self.env['mass.clean.model'].clean_journal_entries()
                self._create_audit_log('clean_journal_entries', 'Cleaned journal entries')
            else:
                no_data_modules.append('Journal Entries')

        if self.clean_only_transfers:
            transfer_data = self.env['stock.picking'].search([])
            if transfer_data:
                self.env['mass.clean.model'].clean_transfers()
                self._create_audit_log('clean_transfers', 'Cleaned all transfers')
            else:
                no_data_modules.append('Transfers')
        if self.project_ids:
                    # Check if the user is a 'Project Manager'
                        is_project_manager = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

                        # Log the result of the group check
                        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager)

                        # Step 0: Check if the user has access
                        if not is_project_manager:
                            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
                            raise AccessError(_("You do not have permission to delete projects or tasks."))
                        project_names = ', '.join(project.name for project in self.project_ids)
                        # Log the successful check and attempt to clean projects
                        self.env['audit.log'].create({
                            'user_id': self.env.user.id,
                            'action_type': 'delete',
                            'model_name': 'project.project',
                            'record_name': project_names,
                            'details': _("User %(user_name)s is attempting to delete/archive projects: %(project_names)s") % {'user_name': self.env.user.name,'project_names': project_names}

                        })
                            # Delete the projects
                        self.project_ids.sudo().unlink()
                        _logger.info("Projects deleted successfully.")
        if self.task_ids:
            # Check if the user is a 'Project Manager'
                is_project_manager = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

                # Log the result of the group check
                _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager)

                # Step 0: Check if the user has access
                if not is_project_manager:
                    _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
                    raise AccessError(_("You do not have permission to delete projects or tasks."))
                task_names = ', '.join(task.name for task in self.task_ids)
                # Log the successful check and attempt to clean tasks
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'delete',
                    'model_name': 'project.task',
                    'record_name': task_names,
                    'details': _("User %(user_name)s is attempting to delete/archive tasks: %(task_names)s") % {'user_name': self.env.user.name,'task_names': task_names}
                })
                    # Delete the projects
                    # Delete the tasks
                self.task_ids.sudo().unlink()
                _logger.info("Tasks deleted successfully.")
        
        return no_data_modules  # Return the list of modules with no data found


            # Check for no data in any selected module
    def confirm_delete_or_archive(self):
        """Attempt to delete selected projects and tasks; archive if deletion fails."""
        # Loop over each project
        for project in self.project_ids:
            try:
                # Attempt to delete the project
                pass
                # project.sudo().unlink()
            except errors.ForeignKeyViolation:
                # If deletion fails due to foreign key constraints, archive instead
                self.env.cr.rollback()
                _logger.warning(f"Project {project.name} could not be deleted due to foreign key constraints; archiving instead.")
                project.sudo().write({'active': False})  # Archive the project