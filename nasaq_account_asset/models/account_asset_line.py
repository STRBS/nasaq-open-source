# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models, _


class AccountAssetLine(models.Model):
    _inherit = 'account.asset.line'

    def _setup_move_data(self, depreciation_date):
        """HAVA 07:20Z: Odoo re-dates an entry out of a locked period to the first open day. Such a
        depreciation entry names the month it covers, so the register and the auditor can match it."""
        vals = super()._setup_move_data(depreciation_date)
        asset = self.asset_id
        journal = asset.profile_id.journal_id
        if asset.company_id._get_violated_lock_dates(depreciation_date, False, journal):
            vals['ref'] = '%s · %s' % (vals.get('ref') or asset.name, _(
                "Depreciation %(month)s (posted after lock)", month=depreciation_date.strftime('%Y-%m')))
        return vals
