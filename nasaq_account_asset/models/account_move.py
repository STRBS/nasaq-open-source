# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from dateutil.relativedelta import relativedelta

from odoo import models

# The moves THIS cursor is posting right now, filled only by action_post below. The asset's
# superuser path (a Billing clerk's bill) trusts this set, never the context: a context is
# whatever an RPC caller sends (IMPLEMENTER H1042 F1).
POSTING = 'nasaq_account_asset.posting_move_ids'


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        posting = self.env.cr.cache.setdefault(POSTING, set())
        added = set(self.ids) - posting
        posting |= added
        try:
            return super().action_post()
        finally:
            posting -= added

    def _prepare_asset_vals(self, aml):
        """HAVA H1028 Q2: depreciation starts in the first full month AFTER the asset is placed
        in service, nothing in the month it was bought. With OCA's prorata on (forced for monthly
        profiles, and meaning 'start from the start date'), that is a start date on the 1st of
        the next month."""
        vals = super()._prepare_asset_vals(aml)
        if vals.get('date_start'):
            vals['date_start'] = vals['date_start'] + relativedelta(months=1, day=1)
        return vals
