import logging
from odoo import models,api,_
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError,AccessError

class MassCleanModel(models.Model):
    _name = 'mass.clean.model'
    _description = 'Mass Clean Data for Odoo Modules'
    

    # def clean_sales(self):
    #     """Cleans sales orders based on their state, ensuring only cancellable orders are deleted."""
    #     # Search for sales orders that are cancellable
    #     sales_orders = self.env['sale.order'].search([
    #         ('state', 'not in', ['sent', 'sale'])  # Exclude sent and confirmed orders
    #     ])

    #     # Iterate over each order and cancel if not already cancelled
    #     for order in sales_orders:
    #         if order.state not in ['cancel']:  # Only cancel if it's not already cancelled
    #             order.action_cancel()  # Use action_cancel to cancel the order

    #     # Now unlink (delete) the cancellable sales orders
    #     sales_orders.sudo().unlink()
    def clean_sales(self):
        user_groups = self.env.user.groups_id.mapped('name')
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, user_groups)

        # Log the result of each group check
        is_system_group = self.env.user.has_group('base.group_system')
        is_sales_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_sales_manager')

        _logger.info("System group check for user %s: %s", self.env.user.name, is_system_group)
        _logger.info("Sales Manager group check for user %s: %s", self.env.user.name, is_sales_manager_group)
                # Step 0: Check if the user has access
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
        if not (is_sales_manager_group):
           _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
           raise AccessError(_("You do not have permission to delete Sales orders."))
        
        # Step 1: Identify orders to delete (states other than 'sent' and 'sale')
        sales_orders_to_delete = self.env['sale.order'].search([
            ('state', 'not in', ['sent', 'sale'])  # Exclude 'sent' and 'sale' orders from deletion
        ])
        
        # Step 2: Cancel and delete orders that are cancellable
        for order in sales_orders_to_delete:
            if order.state != 'cancel':  # Ensure order is not already canceled
                order.action_cancel()  # Cancel the order
            try:
                self.env['audit.log'].create({
                'user_id': self.env.user.id,
                'action_type': 'delete',
                'model_name': 'sale.order',
                'record_name': order.name,
                'details': _("Sales Order %(order_name)s deleted by %(user_name)s") % {'order_name': order.name,'user_name': self.env.user.name}
            })
                order.sudo().unlink()  # Delete the order
                _logger.info("Successfully deleted sale order: %s", order.id)
            except Exception as e:
                _logger.error("Error deleting sale order %s: %s", order.id, str(e))
        
        # Step 3: Archive orders in 'sent' and 'sale' states
        sales_orders_to_archive = self.env['sale.order'].search([
            ('state', 'in', ['sent', 'sale'])
        ])
        
        for order in sales_orders_to_archive:
            try:
                order.sudo().write({'active': False})  # Archive the order
                _logger.info("Successfully archived sale order: %s", order.id)
                # Log the archiving in audit log
                self.env['audit.log'].create({
                'user_id': self.env.user.id,
                'action_type': 'archive',
                'model_name': 'sale.order',
                'record_name': order.name,
                'details': _("Sales Order %(order_name)s archived by %(user_name)s") % {'order_name': order.name,'user_name': self.env.user.name}
            })
            except Exception as e:
                _logger.error("Error archiving sale order %s: %s", order.id, str(e))
        
        _logger.info("Completed cleaning of sales orders.")

    def clean_purchases(self, delete_all=True, status=None):
        """Clean purchase orders based on the user input."""
        user_groups = self.env.user.groups_id.mapped('name')
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, user_groups)

        # Log the result of each group check
        is_system_group = self.env.user.has_group('base.group_system')
        is_sales_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_sales_manager')

        _logger.info("System group check for user %s: %s", self.env.user.name, is_system_group)
        _logger.info("Sales Manager group check for user %s: %s", self.env.user.name, is_sales_manager_group)
                # Step 0: Check if the user has access
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
        if not (is_sales_manager_group):
           _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
           raise AccessError(_("You do not have permission to delete Purchase orders."))
        if delete_all:
            # Delete all purchase orders
            purchase_orders = self.env['purchase.order'].search([])
        else:
            # Delete only purchase orders with the specific status
            purchase_orders = self.env['purchase.order'].search([('state', '=', status)])

        # Cancel and delete the found purchase orders
        for order in purchase_orders:
            if order.state not in ['cancel']:
                order.sudo().button_cancel()  # Cancel the purchase order
        purchase_orders.sudo().unlink()  # Delete the purchase orders

    def clean_purchases(self, delete_all=True, status=None):
        """Clean purchase orders based on the user input."""
        user_groups = self.env.user.groups_id.mapped('name')
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, user_groups)

        # Log the result of each group check
        is_system_group = self.env.user.has_group('base.group_system')
        is_sales_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_sales_manager')

        _logger.info("System group check for user %s: %s", self.env.user.name, is_system_group)
        _logger.info("Sales Manager group check for user %s: %s", self.env.user.name, is_sales_manager_group)
                # Step 0: Check if the user has access
        _logger.info("User %s is attempting to clean sales orders with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
        if not (is_sales_manager_group):
           _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
           raise AccessError(_("You do not have permission to delete Purchase orders."))
        purchase_orders = self.env['purchase.order'].search([] if delete_all else [('state', '=', status)])
        for order in purchase_orders:
            if order.state not in ['cancel']:
                order.sudo().button_cancel()
        purchase_orders.sudo().unlink()

    def clean_projects(self):
        """Deletes all projects, with logging for any that cannot be deleted."""
         # Check if the user is a 'Project Manager'
        is_project_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

        # Log the result of the group check
        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager_group)

        # Step 0: Check if the user has access
        if not (is_project_manager_group):
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete projects."))
        projects = self.env['project.project'].search([])
        try:
            projects.sudo().unlink()
        except Exception as e:
            _logger.error("Error deleting projects: %s", e)
            raise ValidationError(_("Some projects could not be deleted. Check dependencies or permissions."))

    def clean_tasks(self):
        """Deletes all tasks, with logging for any that cannot be deleted."""
         # Check if the user is a 'Project Manager'
        is_project_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

        # Log the result of the group check
        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager_group)

        # Step 0: Check if the user has access
        if not is_project_manager_group:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete projects."))
        tasks = self.env['project.task'].search([])
        try:
            tasks.sudo().unlink()
        except Exception as e:
            _logger.error("Error deleting tasks: %s", e)
            raise ValidationError(_("Some tasks could not be deleted. Check dependencies or permissions."))


    def get_summary(self):
        """Returns a summary of records to be deleted for confirmation."""
         # Check if the user is a 'Project Manager'
        is_project_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_project_manager')

        # Log the result of the group check
        _logger.info("Project Manager group check for user %s: %s", self.env.user.name, is_project_manager_group)

        # Step 0: Check if the user has access
        if not is_project_manager_group:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete projects."))
        summary = {
            'projects': len(self.project_ids or self.env['project.project'].search([])),
            'tasks': len(self.task_ids or self.env['project.task'].search([])),
        }
        return summary



    # def clean_inventory(self):
    #     """Cleans all inventory records."""
    #     self.env['stock.picking'].search([]).unlink()

    def clean_tasks(self):
        """Cleans all tasks."""
        self.env['project.task'].search([]).unlink()

    def clean_accounting(self):
        """Cleans all accounting records."""
        self.env['account.move'].search([]).unlink()

    # def clean_bom(self):
    #     # Get all BOMs
    #     boms = self.env['mrp.bom'].search([])

    #     for bom in boms:
    #         # Cancel related manufacturing orders
    #         manufacturing_orders = self.env['mrp.production'].search([('bom_id', '=', bom.id)])
    #         for order in manufacturing_orders:
    #             if order.state not in ['cancel']:
    #                 order.sudo().action_cancel()  # Cancel the manufacturing order
            
    #         try:
    #             # Delete the BOM
    #             bom.sudo().unlink()
    #         except Exception as e:
    #             _logger.error("Error deleting BOM %s: %s", bom.id, str(e))
    def clean_bom(self):
        """Archives BOMs and cancels related manufacturing orders, logging the process."""
        _logger.info("Starting the BOM cleaning process.")
            # Check if the user is a 'Manufacturing Manager'
        is_manufacturing_manager = self.env.user.has_group('zehntech_mass_delete_records.group_manufacturing_manager')

        # Log the result of the group check
        _logger.info("Manufacturing Manager group check for user %s: %s", self.env.user.name, is_manufacturing_manager)

        # Step 0: Check if the user has access
        if not is_manufacturing_manager:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete BOMs."))
        
        # Get all BOMs
        boms = self.env['mrp.bom'].search([])
        _logger.debug("Found %d BOMs to process.", len(boms))

        for bom in boms:
            # Cancel related manufacturing orders
            manufacturing_orders = self.env['mrp.production'].search([('bom_id', '=', bom.id)])
            for order in manufacturing_orders:
                if order.state not in ['cancel']:
                    try:
                        
                        order.sudo().action_cancel()  # Cancel the manufacturing order
                        _logger.info("Canceled manufacturing order: %s", order.id)
                    except Exception as e:
                        _logger.error("Error canceling manufacturing order %s: %s", order.id, str(e))

            try:
                # Archive the BOM (set active to False)
                bom.sudo().write({'active': False})
                _logger.info("Successfully archived BOM: %s", bom.id)

                    # Log archiving in audit log
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'archive',
                    'model_name': 'mrp.bom',
                    'record_name': bom.display_name,
                   'details': _("BOM %(bom_name)s archived by %(user_name)s") % {'bom_name': bom.display_name,'user_name': self.env.user.name}
                })

            except Exception as e:
                _logger.error("Error archiving BOM %s: %s", bom.id, str(e))

        _logger.info("Completed cleaning BOMs.")

    def clean_manufacturing_orders(self):
        """Cleans all manufacturing orders."""
         # Log this action in the audit log
        self.env['audit.log'].create({
                        'user_id': self.env.user.id,
                        'action_type': 'delete',
                        'model_name': 'mrp.production',
                        'record_name': 'Manufacturing Orders',
                        'details': _("User %(user_name)s is authorized to delete Manufacturing Orders.") % {'user_name': self.env.user.name}
                })
        self.env['mrp.production'].search([]).unlink()

    @api.model
    def clean_journal_entries(self):
        """Archive all records from account.journal without affecting related invoices or moves."""
                # Step 0: Check if the user is an 'Invoice Manager'
        is_invoice_manager = self.env.user.has_group('zehntech_mass_delete_records.group_invoice_manager')

        # Log the result of the group check
        _logger.info("Invoice Manager group check for user %s: %s", self.env.user.name, is_invoice_manager)

        # Step 1: Check if the user has access
        if not is_invoice_manager:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to clean invoicing, payments and journal entries."))
        journals = self.env['account.journal'].search([])

        for journal in journals:
            # Remove the default property if set
            default_props = self.env['ir.property'].search([('value_reference', '=', f'account.journal,{journal.id}')])
            default_props.sudo().unlink()  # Remove default property links

            # Archive the journal without touching related invoices or moves
            try:
                journal.sudo().write({'active': False})  # Archive the journal
                _logger.info("Successfully archived journal: %s", journal.id)

                    # Log the successful archiving in the audit log
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'archive',
                    'model_name': 'account.journal',
                    'record_name': 'Journal Entry',
                    'details': _("Successfully archived journal: %(journal_name)s") % {'journal_name': journal.name}
                })

                # Log archiving in audit log
                self.env['account.deletion.audit.log'].create({
                    'record_type': 'journal',
                    'record_id': journal.id,
                    'state': journal.state,
                    'additional_info': f'Journal reference: {journal.name}'
                })

            except Exception as e:
                _logger.error("Error archiving journal %s: %s", journal.id, e)
    def clean_transfers(self):
        # Define search criteria to find both outgoing (delivery) and incoming (return) transfers
        # Check if the user is a Sales Manager
        is_sales_manager = self.env.user.has_group('zehntech_mass_delete_records.group_sales_manager')

        # Log the result of the group check
        _logger.info("Sales Manager group check for user %s: %s", self.env.user.name, is_sales_manager)

        # Step 0: Check if the user has access
        if not is_sales_manager:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete transfers."))
        transfer_types = ['outgoing', 'incoming']
        transfers = self.env['stock.picking'].search([
            ('picking_type_id.code', 'in', transfer_types)
        ])
        _logger.info("Found %s transfers (outgoing & incoming) to clean", len(transfers))

        for transfer in transfers:
            try:
                    # Log the start of the action
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'delete',
                    'model_name': 'stock.picking',
                    'record_name': transfer.name,
                    'details': _("User %(user_name)s is attempting to clean transfer %(transfer_name)s.") % {'user_name': self.env.user.name,'transfer_name': transfer.name}
                })
                # If transfer is in 'done' state, archive it by setting the active field to False
                if transfer.state == 'done':
                    # Archive the transfer by setting 'active' field to False
                    transfer.write({'active': False})
                    _logger.info("Successfully archived transfer: %s", transfer.id)

                # If transfer is not 'done' state, proceed with cancellation and deletion
                elif transfer.state != 'cancel':
                    transfer.action_cancel()

                # Finally, delete the transfer if it's in 'cancel' state
                if transfer.state == 'cancel':
                     # Log the successful deletion in the audit log
                    self.env['audit.log'].create({
                        'user_id': self.env.user.id,
                        'action_type': 'delete',
                        'model_name': 'stock.picking',
                        'record_name': transfer.name,
                        'details': _("User %(user_name)s successfully deleted transfer %(transfer_name)s.") % {'user_name': self.env.user.name,'transfer_name': transfer.name}
                    })
                    transfer.sudo().unlink()
                    _logger.info("Successfully deleted transfer: %s", transfer.id)

            except Exception as e:
                _logger.error("Error processing transfer %s: %s", transfer.id, str(e))
    def clean_invoicing(self):
        """Cleans invoicing, payments, and journal entries with detailed logs."""
        
        _logger.info("Starting the cleaning process.")
            # Step 0: Check if the user is an 'Invoice Manager'
        is_invoice_manager = self.env.user.has_group('zehntech_mass_delete_records.group_invoice_manager')

        # Log the result of the group check
        _logger.info("Invoice Manager group check for user %s: %s", self.env.user.name, is_invoice_manager)

        # Step 1: Check if the user has access
        if not is_invoice_manager:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to clean invoicing, payments and journal entries."))

                # Step 1: Handle Invoices
        invoices = self.env['account.move'].search([('move_type', 'in', ['out_invoice', 'in_invoice'])])
        _logger.debug("Found %d invoices to process.", len(invoices))
        
        for invoice in invoices:
            try:
                # Check the state of the invoice and perform actions accordingly
                if invoice.state in ['draft', 'cancel']:
                    # Delete draft and canceled invoices
                    invoice.sudo().unlink()
                    _logger.info("Successfully deleted invoice: %s", invoice.id)
                    # Log deletion in audit log
                    self.env['account.deletion.audit.log'].create({
                        'record_type': 'invoice',
                        'record_id': invoice.id,
                        'state': invoice.state,
                        'additional_info': f'Invoice reference: {invoice.name}'
                    })

                elif invoice.state == 'posted':
                    # Archive posted invoices (set active to False)
                    invoice.sudo().write({'active': False})
                    _logger.info("Successfully archived posted invoice: %s", invoice.id)

                    # Log archiving in audit log
                    self.env['account.deletion.audit.log'].create({
                        'record_type': 'invoice',
                        'record_id': invoice.id,
                        'state': 'archived',
                        'additional_info': f'Invoice reference: {invoice.name}'
                    })

            except Exception as e:
                _logger.error("Error processing invoice %s: %s", invoice.id, e)

        # Step 2: Archive Payment Terms
        _logger.info("Archiving payment terms.")
        payment_terms = self.env['account.payment.term'].search([('active', '=', True)])
        _logger.debug("Found %d active payment terms for archiving.", len(payment_terms))
        for term in payment_terms:
            try:
                term.sudo().write({'active': False})
                _logger.info("Successfully archived payment term: %s", term.id)

                 # Add debug log before creating audit entry
                _logger.debug("Creating audit log for payment term %s", term.id)
                    # Log archiving in the audit log
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,  # Log the user performing the action
                    'action_type': 'archive',  # Action type - archiving
                    'model_name': 'account.payment.term',  # Model name
                    'record_name': 'Payment Term',  # Record label
                    'details': _("Successfully archived payment term: %(term_name)s with ID: %(term_id)s") % {'term_name': term.name,'term_id': term.id}
                })

                # Log archiving in audit log
                self.env['account.deletion.audit.log'].create({
                    'record_type': 'payment_term',
                    'record_id': term.id,
                    'additional_info': f'Payment Term name: {term.name}'
                })

            except Exception as e:
                _logger.error("Error archiving payment term %s: %s", term.id, e)

        # Step 3: Archive Journal Entries
        _logger.info("Archiving journals.")
        journals = self.env['account.journal'].search([('active', '=', True)])
        _logger.debug("Found %d journals for archiving.", len(journals))
        for journal in journals:
            try:
                journal.sudo().write({'active': False})
                _logger.info("Successfully archived journal: %s", journal.id)
                _logger.debug("Creating audit log for journal %s", journal.id)
                     # Log the successful archiving in the audit log
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'archive',
                    'model_name': 'account.journal',
                    'record_name': 'Journal Entry',
                    'details': _("Successfully archived journal: %(journal_name)s") % {'journal_name': journal.name}
                })


                # Log archiving in audit log
                # self.env['account.deletion.audit.log'].create({
                #     'record_type': 'journal',
                #     'record_id': journal.id,
                #     'state': 'archived',
                #     'additional_info': f'Journal reference: {journal.name}'
                # })

            except Exception as e:
                _logger.error("Error archiving journal %s: %s", journal.id, e)

        _logger.info("Completed cleaning invoicing, payment terms, and journals.")
    def clean_inventory(self):
        """Handles inventory cleaning by archiving records in 'done' state."""
        stock_picking_model = self.env['stock.picking']
        
        # Search for all 'done' pickings to be archived
        done_pickings = stock_picking_model.search([('state', '=', 'done')])

        try:
            # Archive 'done' pickings by setting active to False
            done_pickings.sudo().write({'active': False})
            _logger.info("Archived all pickings in 'done' state.")
        except Exception as e:
            _logger.error("Error archiving 'done' pickings: %s", e)
            raise ValidationError(_("Some 'done' pickings could not be archived. Check dependencies or permissions."))