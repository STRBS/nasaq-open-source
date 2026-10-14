# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models

# HAVA H1028 Q3: Billing reads assets; creating and changing them is finance's. OCA grants
# Billing crud on assets and their lines. Odoo 20 OR-s permissions, so a narrower row of ours
# would add nothing: OCA's own rows are narrowed instead. A FUNCTION, so it runs on every
# install and update of this module, which loads after OCA's (as nasaq_base's group links).
BILLING_READ_ONLY = (
    'account_asset_management.access_account_asset_invoice',
    'account_asset_management.access_account_asset_line_invoice',
)


class IrAccess(models.Model):
    _inherit = 'ir.access'

    @api.model
    def _nasaq_asset_billing_read_only(self):
        for xmlid in BILLING_READ_ONLY:
            access = self.env.ref(xmlid, raise_if_not_found=False)
            if access and access.operation != 'r':
                access.operation = 'r'
