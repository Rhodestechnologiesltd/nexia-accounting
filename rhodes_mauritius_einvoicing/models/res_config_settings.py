from odoo import api, fields, models
import requests
import json
import os
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
import secrets
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.Signature import pkcs1_15
from Cryptodome.PublicKey import RSA
from Cryptodome.Util import asn1
from base64 import b64decode
from datetime import datetime
import pytz

class ResConfigSettings(models.TransientModel):
    """Class foe adding qr code generation configuration"""
    _inherit = 'res.config.settings'

    is_user_login = fields.Boolean(string='User Login ?')
    user_login = fields.Char(string='User Name')
    user_password = fields.Char(string='User Password')
    user_ebsMraId = fields.Char(string='EBS MRA Id')

    @api.model
    def get_values(self):
        """Get the current configuration values."""
        res = super().get_values()
        res.update(
            is_user_login=self.env['ir.config_parameter'].sudo().get_param(
                'account_customization_morses.is_user_login'),
            user_login=self.env['ir.config_parameter'].sudo().get_param(
                'account_customization_morses.user_login'),
            user_password=self.env['ir.config_parameter'].sudo().get_param(
                'account_customization_morses.user_password'),
            user_ebsMraId=self.env['ir.config_parameter'].sudo().get_param(
                'account_customization_morses.user_ebsMraId'),
        )
        return res

    def set_values(self):
        """Set the configuration values."""
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('account_customization_morses.is_user_login',self.is_user_login or '')
        param.set_param('account_customization_morses.user_login',self.user_login or '')
        param.set_param('account_customization_morses.user_password',self.user_password or '')
        param.set_param('account_customization_morses.user_ebsMraId',self.user_ebsMraId or '')


    def action_login(self):
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        token_url = 'https://vfiscportal.mra.mu/einvoice-token-service/token-api/generate-token'
        vals ={}
        headers_login = {
            'Content-type': 'Application/json'
        }
        data_login_header =  {"username":self.user_login, "ebsMraId":self.user_ebsMraId}
        vals.update(data_login_header)
        # request_payload = {"data": {"username":self.user_login, "ebsMraId":self.user_ebsMraId,'password':self.user_password,"encryptKey":}}
        # data_new_login_header = json.dumps(data_login_header).replace(" ", "")
        # print("<<<>>>>>data_new_login>>>>>..",data_new_login)

        #trying to  Generate a random 32-byte key AES symmetric
        # key = secrets.token_bytes(32)
        aes_key = os.urandom(32)
        # trying to encode key with base 64
        # encode_key = base64.b64encode(key).decode('utf-8')
        base64_encoded_aes_key = base64.b64encode(aes_key).decode('utf-8')
       
        vals.update({'requestId':dt_string})
        # request_payload = {"username":self.user_login, "ebsMraId":self.user_ebsMraId,'password':self.user_password,"encryptKey":encode_key,"refreshToken":"false"}
        request_payload = {"data": {"username":self.user_login, "ebsMraId":self.user_ebsMraId,'password':self.user_password,"encryptKey":base64_encoded_aes_key,"refreshToken":"false"}}
        json_dump_request_payload = json.dumps(request_payload).replace(" ", "")

        with open('/home/datahat/Downloads/PublicKey.crt', 'rb') as f:
            cert_data = f.read()
        # cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        cert = RSA.importKey(cert_data)
        public_key = cert.public_key()
        cipher_rsa = PKCS1_OAEP.new(public_key)
        encrypted_message = cipher_rsa.encrypt(json_dump_request_payload.encode('utf-8'))
        encoded_encrypted_message = base64.b64encode(encrypted_message).decode('utf-8')
        decrypt_message = base64.b64decode(encoded_encrypted_message)

        vals.update({
            'payload':encoded_encrypted_message,
            })
       
        response = requests.post(token_url,headers=headers_login,data=vals)
