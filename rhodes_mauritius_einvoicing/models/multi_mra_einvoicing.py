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

class MultiMRAEinvoicing(models.TransientModel):
    _name = "multi.mra.einvoicing"

    account_move_ids = fields.Many2many('account.move', string="Invoices")

    def action_mra_fiscalise(self):

        if self.account_move_ids:
            invoice_states = self.account_move_ids.mapped('state')
            if all(state == "posted" for state in invoice_states):
                pass
            else:
                raise ValidationError("All Invoices must be Posted. Draft invoice can't be eInvoice.")

        for move in self.account_move_ids:
            move._get_valication_check()

        rhodes_mra_invoicing = MRAEinvocing(self)
        response, api_logs = rhodes_mra_invoicing._get_invoice_transmission_data(self.account_move_ids)
        if api_logs:
            self.env['mra.logs'].sudo().create(api_logs)

        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'SUCCESS':
                fiscalisedInvoices = result.get('fiscalisedInvoices')
                for inv in fiscalisedInvoices:
                    invoice_indentifier = inv.get('invoiceIdentifier')
                    invoice_id = self.env['account.move'].sudo().search([('name', '=', invoice_indentifier)], limit=1)
                    if invoice_id:
                        invoice_id.qr_code_encoded = inv.get('qrCode')
                        invoice_id.irn = inv.get('irn')
                        invoice_id.eInvoice_status = 'success'
                        invoice_id.is_mra_fiscalised = True
                        # Remove Reset button after fiscalisation
                        invoice_id.show_reset_to_draft_button = False
                        invoice_id.qr_code = invoice_id.qr_code_encoded
                        # invoice_id.qr_code = self._generate_qrcode(invoice_id.qr_code_encoded)
                        msg_body = _("This invoice has been successfully fiscalised with the MRA by: %s." % (self.env.user.name))
                        invoice_id.message_post(body=msg_body, message_type='comment')
                        invoice_id.company_id.global_count += 1
                        invoice_id.counter = invoice_id.company_id.global_count
                        if invoice_id.invoice_type_desc == 'STD':
                            invoice_id.company_id.std_count += 1
                        elif invoice_id.invoice_type_desc == 'PRF':
                            invoice_id.company_id.prf_count += 1
                        elif invoice_id.invoice_type_desc == 'CRN':
                            invoice_id.company_id.crn_count += 1
                        elif invoice_id.invoice_type_desc == 'DRN':
                            invoice_id.company_id.drn_count += 1
                        elif invoice_id.invoice_type_desc == 'TRN':
                            invoice_id.company_id.trn_count += 1
                    else:
                        raise ValidationError("%s not found." %(invoice_indentifier))
                return {
                    'effect': {
                    'fadeout': 'slow',
                    'message': 'Invoices fiscalised successfully!',
                    'type': 'rainbow_man',
                    }
                }
            else:
                result = response.json()
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
                "Transmission API failed. \nStatus code: %s \nMessage: %s", response.status_code, result.get('errorMessages')
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
        # return base64.b64encode(img_byte_array)


    def action_send_for_invocies(self):
        return {
            'name': _('Multi MRA eInvoicing'),
            'res_model': 'multi.mra.eInvoicing',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }