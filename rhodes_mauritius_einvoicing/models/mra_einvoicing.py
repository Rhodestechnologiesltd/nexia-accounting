import requests

from odoo import _, fields
from odoo.exceptions import UserError, ValidationError
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
import base64
import os
from datetime import datetime, timedelta
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import re

class MRAEinvocing(object):

    def __init__(self, res_object):
        mra_authentication_url = res_object.env['ir.config_parameter'].sudo().get_param('rhodes_mauritius_einvoicing.mra_authentication_url')
        mra_invoice_transmission_url = res_object.env['ir.config_parameter'].sudo().get_param('rhodes_mauritius_einvoicing.mra_invoice_transmission_url')

        self.mra_authentication_url =  mra_authentication_url and mra_authentication_url or False
        self.mra_invoice_transmission_url = mra_invoice_transmission_url and mra_invoice_transmission_url or False

    def _send_api_request(self, request_type, url, data=None, skip_auth=False):
        if data is None:
            data = {}
        try:
            auth = {}
            if request_type == "GET":
                res = requests.get(url=url, headers=auth, timeout=60)
            elif request_type == "POST":
                res = requests.post(url=url, json=data.get('json'), headers=data.get('headers'), timeout=60)
            else:
                raise UserError(
                    _("Unsupported request type, please only use 'GET' or 'POST'")
                )
            # res.raise_for_status()
            # dhl_parcel_last_request = ("Request type: {}\nURL: {}\nData: {}").format(
            #     request_type, url, data
            # )
            # self.carrier_id.log_xml(dhl_parcel_last_request, "dhl_parcel_last_request")
            # self.carrier_id.log_xml(res.text or "", "dhl_parcel_last_response")
        except requests.exceptions.Timeout as e:
            raise UserError(
                _("Timeout: the server did not reply within 60s\n%(text)s")
                % {"text": str(e)}
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise UserError(
                _("Server not reachable, please try again later\n%(text)s")
                % {"text": str(e)}
            ) from e
        except requests.exceptions.HTTPError as e:
            raise UserError(
                _("%(text)s\n%(message)s")
                % {
                    "text": e,
                    "message": res.json().get("Message", "") if res.text else "",
                }
            ) from e
        return res

    def _get_new_auth_token(self, username, password, ebsMraId):
        aes_key = self._get_aes_key()  # Step 1: Generate a 256-bit AES symmetric key
        encoded_key = self._get_base64encode_string(aes_key) # Encode the AES key to Base64 string
        # Step 2: Create a JSON payload
        payload = {
            "username": username,
            "password": password,
            "encryptKey": encoded_key,
            "refreshToken": "false"
        }

        json_string = json.dumps(payload) # Step 3: Convert the JSON payload to a string

        # Step 4: Encrypt the string using RSA with ECB mode and PKCS padding
        # Load RSA public key from file or any other source
        from odoo.modules.module import get_module_resource
        public_key_path = get_module_resource('rhodes_mauritius_einvoicing', 'static/src/MRA/public_key_1.pem')
        with open(public_key_path, "rb") as file:
            public_key = RSA.import_key(file.read())

        # Encrypt the JSON string
        encrypted_json = self.encrypt_rsa(json_string, public_key)

        authentication_request_json = {
            "requestId": self.generate_request_id(),
            "payload": encrypted_json
        }

        headers = {
            "username": username,
            "ebsMraId": ebsMraId,
        }

        res = self._send_api_request(
            request_type="POST",
            url=self.mra_authentication_url,
            data={"json": authentication_request_json, "headers": headers},
            skip_auth=True,
        )
        api_logs = self._generate_api_logs(api_type="authentication_api", request_type="POST", url=self.mra_authentication_url, data={"json": authentication_request_json, "headers": headers}, response=res)

        return res, api_logs, encoded_key

    def _generate_api_logs(self, api_type, request_type, url, data, response):
        request_json = {
            'request_type': request_type,
            'url': url,
            'headers': data.get('headers'),
            'json': data.get('json')
        }

        values = {
            'api_type': api_type,
            'request_id': response.json().get('requestId'),
            'request_json': request_json,
            'response_id': response.json().get('responseId'),
            'response_status_code': response.status_code,
            'response_json': response.json(),
        }

        return values

    def generate_request_id(self):
        now = datetime.now()
        request_id = now.strftime("%Y%m%d%H%M%S%f")
        return request_id

 
    def _get_aes_key(self):
        # Generate random AES key
        return os.urandom(32) # 256 bits

    def _get_base64encode_string(self, data):
        # Encode the passed data to Base64 string
        return base64.b64encode(data).decode('utf-8')

    def clean_and_validate_phone_number(self, phone_number):
        # Remove all whitespace characters
        phone_number = re.sub(r'\s+', '', phone_number)

        # Validate the phone number
        if re.fullmatch(r'\+\d+', phone_number):
            return phone_number
        else:
            raise ValueError("Invalid phone number. The phone number must start with '+' followed by digits only.")


    def encrypt_rsa(self, message, public_key):
        cipher_rsa = PKCS1_v1_5.new(public_key)
        ciphertext = cipher_rsa.encrypt(message.encode())
        return self._get_base64encode_string(ciphertext)

    def _validate_token(self, invoice):
        if invoice.company_id.enable_mra_api and invoice.company_id.token_status == 'success':
            now = datetime.now() + timedelta(hours=4) #current mauritius time
            token_expiry_date = invoice.company_id.token_expiry_date
            if now >= token_expiry_date:
                return False
            else:
                return True
        else:
            return False

    def remove_padding(self, data):
        padding_len = data[-1]
        return data[:-padding_len]


    def decrypt_key(self, encrypted_key_base64, random_aes_key_base64):
        # Decode base64 strings
        encrypted_key = base64.b64decode(encrypted_key_base64)
        random_aes_key = base64.b64decode(random_aes_key_base64)

        # Create AES cipher object
        cipher = AES.new(random_aes_key, AES.MODE_ECB)

        # Decrypt the key
        decrypted_key = cipher.decrypt(encrypted_key)

        # Remove PKCS7 padding
        decrypted_key = self.remove_padding(decrypted_key)

        return decrypted_key

    def encrypt_invoice(self, json_invoice_str, decrypted_key):
        decrypted_key = base64.b64decode(decrypted_key)
        backend = default_backend()
        cipher = Cipher(algorithms.AES(decrypted_key), modes.ECB(), backend=backend)
        encryptor = cipher.encryptor()

        # Add padding to the data
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(json_invoice_str) + padder.finalize()

        # Encrypt the padded data
        encrypted_invoice = encryptor.update(padded_data) + encryptor.finalize()
        return encrypted_invoice

    def generate_payload(self, username, ebs_mra_id, token, areaCode):
        payload = {
            "username": username,
            "ebsMraId": ebs_mra_id,
            "areaCode": areaCode,
            "token": token
        }
        return payload

    def _compute_address(self, partner):
        res = [partner.street, partner.street2,
               partner.city, partner.state_id.name, partner.country_id.name,
               partner.zip]
        address = ', '.join(filter(bool, res))
        return address


    def _get_invoice_transmission_data(self, invoice):
        valid_token = self._validate_token(invoice)
        if not valid_token:
            invoice.company_id.action_generate_token()

        token = invoice.company_id.token
        encoded_key = invoice.company_id.encoded_key
        encrypted_key = invoice.company_id.encrypted_key

        decrypted_key = self.decrypt_key(encrypted_key, encoded_key)

        mra_invoice_template = self._generate_invoice_template(invoice)
        json_invoice_str = json.dumps(mra_invoice_template).encode('utf-8')
        encrypted_invoice = self.encrypt_invoice(json_invoice_str, decrypted_key)
        encoded_invoice = self._get_base64encode_string(encrypted_invoice)
        payload = self.generate_payload(invoice.company_id.username, invoice.company_id.ebs_mra_id, token, invoice.company_id.area_code)
        # Get the current date and time
        current_datetime = datetime.now()
        # Format the current date and time
        formatted_datetime = current_datetime.strftime("%Y%m%d %H:%M:%S")
        request_id = self.generate_request_id()

        invoice_request_json = {
            "requestId": request_id,
            "requestDateTime": formatted_datetime,
            "signedHash": "",
            "encryptedInvoice": encoded_invoice,
        }
        res = self._send_api_request(
            request_type="POST",
            url=self.mra_invoice_transmission_url,
            data={"json": invoice_request_json, "headers": payload},
            skip_auth=True,
        )
        api_logs = self._generate_api_logs(api_type="transmission_api", request_type="POST", url=self.mra_invoice_transmission_url, data={"json": invoice_request_json, "headers": payload}, response=res)

        return res, api_logs

    def _generate_invoice_template(self, invoices):
        sample_invoice = []
        count = 0
        for invoice in invoices:
            totalAmtWoVatMur = False
            if invoice.currency_id.name != 'MUR':
                mur_currency_id = invoice.env.ref('base.MUR')
                totalAmtWoVatMur = invoice.currency_id._convert(invoice.amount_untaxed, mur_currency_id, invoice.company_id, invoice.invoice_date or invoice.date)
            else:
                totalAmtWoVatMur = invoice.amount_untaxed

            if not invoice.invoice_type_desc:
                raise ValidationError("Transaction Type is Mandatory.")
            if not invoice.transaction_type:
                raise ValidationError("Invoice Type is Mandatory.")
            if invoice.transaction_type in ['CRN', 'DRN']:
                if not invoice.reversed_entry_id:
                    raise ValidationError("For Credit notes Reversal of Invoice field is Mandatory.")
                if not invoice.refund_reason:
                    raise ValidationError("For Credit notes Refund Reason is Mandatory.")

            seller_id = False
            buyer_id = False
            if invoice.move_type == 'out_invoice' or invoice.move_type == 'out_refund':
                seller_id = invoice.company_id.partner_id
                buyer_id = invoice.partner_id
            elif invoice.move_type == 'in_invoice' or invoice.move_type == 'in_refund':
                seller_id = invoice.company_id.partner_id
                buyer_id = invoice.partner_id

            seller_data = self._get_seller_data(seller_id)
            buyer_data = self._get_buyer_data(buyer_id, invoice.invoice_type_desc)
            item_list_data = []
            line_count = 0
            for invoice_line in invoice.invoice_line_ids:
                if invoice_line.display_type not in ('line_section', 'line_note'):
                    line_count += 1
                    line_dict = self._get_list_data(invoice_line, line_count)
                    item_list_data.append(line_dict)

            count = invoice.company_id.global_count + 1
            
            data = {
                "invoiceCounter": count,
                "transactionType": invoice.transaction_type,
                "personType": invoice.company_id.partner_id.buyer_type,
                "invoiceTypeDesc": invoice.invoice_type_desc,
                "currency": invoice.currency_id.name,
                "invoiceIdentifier": invoice.name,
                "invoiceRefIdentifier": invoice.reversed_entry_id.name if invoice.reversed_entry_id else '',
                "previousNoteHash": "prevNote",
                "reasonStated": invoice.refund_reason,
                "totalVatAmount": round(invoice.amount_tax),
                "totalAmtWoVatCur": round(invoice.amount_untaxed),
                "totalAmtWoVatMur": round(totalAmtWoVatMur),
                "totalAmtPaid": round(invoice.amount_total),
                "invoiceTotal": round(invoice.amount_total),
                "dateTimeInvoiceIssued": invoice.invoice_date.strftime("%Y%m%d %H:%M:%S"),
                "seller": seller_data,
                "buyer": buyer_data,
                "itemList": item_list_data,
                "salesTransactions": invoice.mode_of_payment,
            }
            # raise UserError(invoice.company_id.partner_id.buyer_type)
            sample_invoice.append(data)
            print(data)
        return sample_invoice

    def _get_seller_data(self, partner):
        phone_number = False
        if not partner.name:
            raise ValidationError("Seller name is Mandatory.")
        if not partner.vat:
            raise ValidationError("Seller's TAN is Mandatory.")
        if not partner.brn:
            raise ValidationError("Seller's BRN is Mandatory.")
        if not partner.phone:
            if not partner.mobile:
                raise ValidationError("Seller's Phone is Mandatory.")
            else:
                phone_number = partner.mobile
        else:
            phone_number = partner.phone

        businessPhoneNo = self.clean_and_validate_phone_number(phone_number)

        return {
            "name": partner.name,
            "tradeName": partner.trade_name,
            "tan": partner.vat,
            "brn": partner.brn,
            "businessAddr": self._compute_address(partner),
            "businessPhoneNo": businessPhoneNo,
            "ebsCounterNo": "",
        }

    def _get_buyer_data(self, partner, transaction_type):
        if transaction_type in ['B2B', 'B2G']:
            if not partner.name:
                raise ValidationError("Buyer's name is Mandatory.")
            if not partner.vat and transaction_type != 'B2G':
                raise ValidationError("Buyer's TAN is Mandatory.")
            if not partner.brn:
                raise ValidationError("Buyer's BRN is Mandatory.")

        return {
            "name": partner.name,
            "tan": partner.vat if partner.vat else None,
            "brn": partner.brn if partner.brn else None,
            "businessAddr": self._compute_address(partner),
            "buyerType": partner.buyer_type,
            "nic": "",
        }

    def _get_list_data(self, invoice_line, line_count):
        totalAmtWoVatMur = False
        if invoice_line.move_id.currency_id.name != 'MUR':
            mur_currency_id = invoice_line.env.ref('base.MUR')
            totalAmtWoVatMur = invoice_line.move_id.currency_id._convert(invoice_line.price_subtotal, mur_currency_id, invoice_line.move_id.company_id, invoice_line.move_id.invoice_date or invoice_line.move_id.date)
        else:
            totalAmtWoVatMur = invoice_line.price_subtotal

        if not invoice_line.product_id.tax_code:
            raise ValidationError("For product %s Tax code is Mandatory."  %(invoice_line.product_id.name))

        return {
            "itemNo": line_count,
            "taxCode": invoice_line.product_id.tax_code,
            "nature": "GOODS" if invoice_line.product_id.detailed_type != 'service' else "SERVICES",
            "productCodeMra": "",
            "productCodeOwn": invoice_line.product_id.default_code,
            "itemDesc": invoice_line.product_id.display_name,
            "quantity": invoice_line.quantity,
            "unitPrice": round(invoice_line.price_unit),
            "discount": round(invoice_line.discount),
            "discountedValue": round(invoice_line.price_total),
            "amtWoVatCur": round(invoice_line.price_subtotal),
            "amtWoVatMur": round(totalAmtWoVatMur, 2),
            "vatAmt": round(invoice_line.price_total - invoice_line.price_subtotal, 2),
            "totalPrice": round(invoice_line.price_total),
        }
