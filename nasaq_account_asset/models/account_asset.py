# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

from .account_move import POSTING


# What OCA's account.move._prepare_asset_vals sets (plus the analytic, stripped above): a Billing
# clerk's asset is made from these and nothing else.
CLERK_FIELDS = {'name', 'code', 'profile_id', 'purchase_value', 'partner_id', 'date_start', 'analytic_distribution'}


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    source_fund_id = fields.Many2one(
        'account.analytic.account', string="Funded by", index=True, tracking=True,
        domain="[('root_plan_id', '=', company_fund_plan_id)]",
        help="The restricted fund that paid for this asset, taken from the bill line. The fund is "
             "charged once, at purchase; depreciation and disposal never charge it again. It may "
             "stay empty for an asset owned before the system.")
    company_fund_plan_id = fields.Many2one(related='company_id.asset_fund_plan_id')

    # ------------------------------------------------------------------ the fund comes off

    @api.model
    def _split_fund(self, distribution, company):
        """-> (distribution without `company`'s Funds plan, the fund it named or an empty record).

        A key may join several analytic accounts ('12,15' is one line on two plans). The fund's
        account is removed from each key; a key left empty is dropped; equal keys are merged.
        An asset is paid by ONE fund: a distribution naming two is refused (H1042 F3)."""
        Account = self.env['account.analytic.account']
        plan = company.asset_fund_plan_id
        if not distribution or not plan:
            return distribution, Account
        ids = [int(a) for key in distribution for a in str(key).split(',') if a]
        funds = {str(a.id): a for a in Account.sudo().browse(ids).exists() if a.root_plan_id == plan}
        if not funds:
            return distribution, Account
        kept, found = {}, Account
        for key, share in distribution.items():
            parts = [a for a in str(key).split(',') if a]
            found |= Account.browse([funds[a].id for a in parts if a in funds])
            rest = ','.join(a for a in parts if a not in funds)
            if rest:
                kept[rest] = kept.get(rest, 0.0) + share
        if len(found) > 1:
            raise UserError(_("An asset is paid by one fund, but this line names %(funds)s. Buy it on one "
                              "fund, or split the purchase into one line per fund.",
                              funds=', '.join(found.sudo().mapped('display_name'))))
        return kept or False, found

    def _check_fund_settable(self):
        """Funded by is set while it is empty and before the first posted depreciation (DIGITAL,
        HAVA). Trusted bypass: superuser only, never a context flag (H1042 F2)."""
        if self.env.su:
            return
        for asset in self:
            if asset.depreciation_line_ids.filtered(
                    lambda l: l.type == 'depreciate' and l.move_id and l.move_id.state == 'posted'):
                raise UserError(_("%s already has posted depreciation: set Funded by before the first one.",
                                  asset.display_name))

    # ------------------------------------------------------------------ CRUD

    def _is_clerk_bill(self):
        """True only while THIS cursor posts the move named in the context (account_move.POSTING)
        and the user may not create assets: a Billing clerk's asset bill (HAVA 06:34Z)."""
        ctx = self.env.context
        return bool(ctx.get('create_asset_from_move_line') and not self.env.su
                    and ctx.get('move_id') in self.env.cr.cache.get(POSTING, ())
                    and not self.has_access('create'))

    @api.model_create_multi
    def create(self, vals_list):
        funds = []
        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
            if 'analytic_distribution' in vals:
                vals['analytic_distribution'], fund = self._split_fund(vals['analytic_distribution'], company)
            else:
                fund = self.env['account.analytic.account']
            funds.append(fund)
        if self._is_clerk_bill():
            # Created as superuser, ALWAYS in draft for finance to confirm, and shaped ONLY by the bill:
            # the fields OCA's _prepare_asset_vals sets, the bill's company, and no caller default_*
            # (SHIELD H1040 C1 + R1: a context is whatever the caller sends).
            move = self.env['account.move'].sudo().browse(self.env.context['move_id'])
            vals_list = [dict({k: v for k, v in vals.items() if k in CLERK_FIELDS},
                              state='draft', company_id=move.company_id.id) for vals in vals_list]
            ctx = dict(clean_context(self.env.context), create_asset_from_move_line=True, move_id=move.id,
                       asset_validate_from_write=True)
            assets = super(AccountAsset, self.sudo().with_context(ctx)).create(vals_list)
        else:
            assets = super().create(vals_list)
        for asset, fund in zip(assets, funds):
            if fund and not asset.source_fund_id:
                asset.sudo().source_fund_id = fund
        return assets

    def write(self, vals):
        if 'source_fund_id' in vals and not self.env.su:
            for asset in self:
                if asset.source_fund_id and asset.source_fund_id.id != vals['source_fund_id']:
                    raise UserError(_("%(asset)s is already funded by %(fund)s: the fund that paid for an "
                                      "asset does not change.", asset=asset.display_name,
                                      fund=asset.source_fund_id.display_name))
            self._check_fund_settable()
        if 'analytic_distribution' not in vals:
            return super().write(vals)
        for asset in self:
            asset_vals = dict(vals)
            asset_vals['analytic_distribution'], fund = self._split_fund(vals['analytic_distribution'], asset.company_id)
            super(AccountAsset, asset).write(asset_vals)
            if fund and not asset.source_fund_id:
                asset._check_fund_settable()
                asset.sudo().source_fund_id = fund
        return True

    @api.depends('profile_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for asset in self:
            asset.analytic_distribution = self._split_fund(asset.analytic_distribution, asset.company_id)[0]
