# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models

ASSET_READERS = 'account.group_account_invoice,account.group_account_user,account.group_account_manager'


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    funded_asset_ids = fields.One2many('account.asset', 'source_fund_id', string="Funded Assets",
                                       groups=ASSET_READERS)
    funded_asset_count = fields.Integer(compute='_compute_funded_asset_count', groups=ASSET_READERS)

    def _compute_funded_asset_count(self):
        counts = dict(self.env['account.asset']._read_group(
            [('source_fund_id', 'in', self.ids)], ['source_fund_id'], ['__count']))
        for account in self:
            account.funded_asset_count = counts.get(account, 0)

    def action_view_funded_assets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account_asset_management.account_asset_action')
        action['domain'] = [('source_fund_id', '=', self.id)]
        action['context'] = {'default_source_fund_id': self.id}
        return action
