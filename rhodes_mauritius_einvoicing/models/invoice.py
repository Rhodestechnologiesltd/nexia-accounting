from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)
from .mra_einvoicing import (
    MRAEinvocing
)
import base64
import qrcode
from PIL import Image
from io import BytesIO

TYPE_REVERSE_MAP = {
    'entry': 'entry',
    'out_invoice': 'out_refund',
    'out_refund': 'entry',
    'in_invoice': 'in_refund',
    'in_refund': 'entry',
    'out_receipt': 'out_refund',
    'in_receipt': 'in_refund',
}

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move=move)
        res['refund_reason'] = self.reason
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    enable_mra_api = fields.Boolean(string="MRA e-Invoicing", related='company_id.enable_mra_api', copy=False)
    counter = fields.Integer(string="Counter No.")
    qr_code = fields.Binary(string="QR code", copy=False)
    qr_code_encoded = fields.Text(string="QR code", copy=False)
    irn = fields.Char(string="IRN", copy=False, tracking=True)
    eInvoice_status = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Status", copy=False, tracking=True)
    is_mra_fiscalised = fields.Boolean(string="Fiscalised with MRA", copy=False, tracking=True)

    transaction_type = fields.Selection(related="partner_id.transaction_type", readonly=False, string="Transaction Type", copy=False)
    # transaction_type = fields.Selection([('B2B', 'B2B'), ('B2G', 'B2G'),('B2C', 'B2C')], string="Transaction Type", copy=False)
    invoice_type_desc = fields.Selection([('STD', 'Standard Invoice'),
                                          ('PRF', 'Proforma Invoice'),
                                          ('TRN', 'Training'),
                                          ('CRN', 'Credit Note'),
                                          ('DRN', 'Debit Note')],
                                         compute="_compute_invoice_type", store=True,
                                         string="Invoice Type", readonly=False, copy=False, tracking=True)
    refund_reason = fields.Char(string="Reason", copy=False)
    mode_of_payment = fields.Selection([('CASH', 'Cash'), ('BNKTRANSFER', 'Bank Transfer'), ('CHEQUE', 'Cheque'), ('CARD', 'Card'), ('CREDIT', 'Credit')], tracking=True, string="Mode of Payment")

    def copy(self, default=None):
        default = dict(default or {})
        default.update({ 'qr_code': False, })
        return super(AccountMove, self).copy(default)
    
    @api.depends('move_type')
    def _compute_invoice_type(self):
        types = {'out_invoice': 'STD',
                 'out_refund': 'CRN',
                 'in_refund': 'DRN',}
        for rec in self:
            if rec.move_type:
                rec.invoice_type_desc = types.get(rec.move_type)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]

        for move, default_values in zip(self, default_values_list):
            invoice_type_desc = False
            if TYPE_REVERSE_MAP[move.move_type] == 'out_refund':
                invoice_type_desc = 'CRN'
            elif TYPE_REVERSE_MAP[move.move_type] == 'in_refund':
                invoice_type_desc = 'DRN'
            else:
                invoice_type_desc = 'STD'

            default_values.update({
                'invoice_type_desc': invoice_type_desc,
            })
        return super(AccountMove, self)._reverse_moves(default_values_list=default_values_list,cancel=cancel)

    def _get_valication_check(self):
        for rec in self:
            if not rec.transaction_type:
                raise ValidationError("Please mention Transaction Type before sending for fiscalisation to the MRA.")
            if not rec.invoice_type_desc:
                raise ValidationError("Please mention Invoice Type before sending for fiscalisation to the MRA.")
            if not self.mode_of_payment:
                raise ValidationError("Please mention Mode of payment before sending for fiscalisation to the MRA.")
            if rec.invoice_type_desc in ['CRN', 'DRN']:
                if not rec.refund_reason:
                    raise ValidationError("For Credit note or Debit note Invoice Type please mention Reason for sending for fiscalisation to the MRA.")
                if not rec.reversed_entry_id:
                    raise ValidationError("For Credit note or Debit note Invoice Type please mention Reversal of Invoice for sending for fiscalisation to the MRA.")


    def action_mra_fiscalise(self):
        self._get_valication_check()
        rhodes_mra_invoicing = MRAEinvocing(self)
        response, api_logs = rhodes_mra_invoicing._get_invoice_transmission_data(self)
        if api_logs:
            self.env['mra.logs'].sudo().create(api_logs)

        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'SUCCESS':
                fiscalisedInvoices = result.get('fiscalisedInvoices')[0]
                self.qr_code_encoded = fiscalisedInvoices.get('qrCode')
                self.irn = fiscalisedInvoices.get('irn')
                self.eInvoice_status = 'success'
                self.is_mra_fiscalised = True
                # Remove Reset button after fiscalisation
                self.show_reset_to_draft_button = False
                self._generate_qrcode(self.qr_code_encoded)
                msg_body = _("This invoice has been successfully fiscalised with the MRA by: %s." % (self.env.user.name))
                self.message_post(body=msg_body, message_type='comment')
                self.company_id.global_count += 1
                self.counter = self.company_id.global_count
                if self.invoice_type_desc == 'STD':
                    self.company_id.std_count += 1
                elif self.invoice_type_desc == 'PRF':
                    self.company_id.prf_count += 1
                elif self.invoice_type_desc == 'CRN':
                    self.company_id.crn_count += 1
                elif self.invoice_type_desc == 'DRN':
                    self.company_id.drn_count += 1
                elif self.invoice_type_desc == 'TRN':
                    self.company_id.trn_count += 1
                return {
                    'effect': {
                    'fadeout': 'slow',
                    'message': 'Invoice fiscalised successfully!',
                    'type': 'rainbow_man',
                    }
                }
            else:
                fiscalisedInvoices = result.get('fiscalisedInvoices')
                if len(fiscalisedInvoices) == 0:
                    raise ValidationError(_(
                        "Transmission API failed. \nStatus code: %s \nMessage: %s", response.status_code, str(fiscalisedInvoices[0].get('errorMessages'))
                    ))
                else:
                    msg = 'Transmission API failed.'
                    for inv in fiscalisedInvoices:
                        invoice_indentifier = inv.get('invoiceIdentifier')
                        msg += _("\nFor invoice %s \nerror message: %s" , invoice_indentifier, str(inv.get('errorMessages')))
                    raise ValidationError(msg)
        else:
            result = response.json()
            raise ValidationError(_(
                "Transmission API failed. \nStatus code: %s \nMessage: %s", response.status_code, str(result.get('errorMessages'))
            ))

    def _generate_qrcode(self, qr_code_encoded):
        self.sudo().write({'qr_code': qr_code_encoded})
        # base64_string = qr_code_encoded
        # image_data = base64.b64decode(base64_string)

        # # Step 2: Create QR Code Image
        # qr = qrcode.QRCode(
        #     version=1,
        #     error_correction=qrcode.constants.ERROR_CORRECT_L,
        #     box_size=10,
        #     border=4,
        # )
        # qr.add_data(image_data)
        # qr.make(fit=True)
        # qr_img = qr.make_image(fill_color="black", back_color="white")

        # # Step 3: Convert image to byte array
        # img_byte_array = BytesIO()
        # qr_img.save(img_byte_array, format='PNG')
        # img_byte_array = img_byte_array.getvalue()

        # # Step 4: Assign byte array to binary field
        # self.sudo().write({'qr_code': base64.b64encode(img_byte_array)})


    def action_send_for_invocies(self):
        return {
            'name': _('Multi MRA eInvoicing'),
            'res_model': 'multi.mra.einvoicing',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {
                'default_account_move_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }