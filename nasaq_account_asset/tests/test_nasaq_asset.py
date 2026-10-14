# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestNasaqAsset(TransactionCase):
    """HAVA H1027/H1028 on OCA's register, with OCA + core only (LAWYER H1035): an asset bought
    on a restricted fund is charged to it ONCE, at purchase. The funds are the accounts of the
    analytic plan the company names; here a test plan, on Nasaq its Funds plan."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, lang='en_US'))
        cls.company = cls.env.company
        Acc = cls.env['account.account']
        cls.a_asset = Acc.create({'code': '121901', 'name': 'Vehicles', 'account_type': 'asset_fixed'})
        cls.a_dep = Acc.create({'code': '225901', 'name': 'Accumulated depreciation', 'account_type': 'asset_fixed'})
        cls.a_exp = Acc.create({'code': '413901', 'name': 'Depreciation', 'account_type': 'expense_depreciation'})
        cls.a_gain = Acc.create({'code': '312901', 'name': 'Gain on disposal', 'account_type': 'income_other'})
        cls.a_loss = Acc.create({'code': '414901', 'name': 'Loss on disposal', 'account_type': 'expense'})
        cls.bank = Acc.search([('account_type', '=', 'asset_cash'), ('company_ids', 'in', cls.company.ids)], limit=1) \
            or Acc.search([('account_type', '=', 'asset_current'), ('company_ids', 'in', cls.company.ids)], limit=1)
        cls.misc = cls.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', cls.company.id)], limit=1)
        cls.purchase = cls.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', cls.company.id)], limit=1)
        Plan, Analytic = cls.env['account.analytic.plan'], cls.env['account.analytic.account']
        cls.fund_plan = Plan.create({'name': 'Funds (test)'})
        cls.fund = Analytic.create({'name': 'Ambulance grant', 'plan_id': cls.fund_plan.id})
        cls.other_fund = Analytic.create({'name': 'Orphans', 'plan_id': cls.fund_plan.id})
        cls.programme = Analytic.create({'name': 'Emergency care', 'plan_id': Plan.create({'name': 'Programmes (test)'}).id})
        cls.company.asset_fund_plan_id = cls.fund_plan
        cls.profile = cls.env['account.asset.profile'].create({
            'name': 'Vehicles 12 months', 'account_asset_id': cls.a_asset.id,
            'account_depreciation_id': cls.a_dep.id, 'account_expense_depreciation_id': cls.a_exp.id,
            'account_plus_value_id': cls.a_gain.id, 'account_min_value_id': cls.a_loss.id,
            'journal_id': cls.misc.id, 'method': 'linear', 'method_number': 12,
            'method_period': 'month', 'method_time': 'number'})
        cls.vendor = cls.env['res.partner'].create({'name': 'Car dealer'})
        cls.accountant = new_test_user(cls.env, login='asset_accountant', groups='base.group_user,account.group_account_user')
        cls.billing = new_test_user(cls.env, login='asset_billing', groups='base.group_user,account.group_account_invoice')
        cls.both = {'%s,%s' % (cls.programme.id, cls.fund.id): 100.0}   # one line, two plans

    def _bill(self, when, distribution=None, user=None, amount=12000.0, post_context=None):
        Move = self.env['account.move'].with_user(user) if user else self.env['account.move']
        bill = Move.create({
            'move_type': 'in_invoice', 'partner_id': self.vendor.id, 'journal_id': self.purchase.id,
            'invoice_date': when, 'date': when, 'invoice_line_ids': [(0, 0, {
                'name': 'Ambulance', 'account_id': self.a_asset.id, 'price_unit': amount, 'quantity': 1,
                'tax_ids': [(6, 0, [])], 'asset_profile_id': self.profile.id,
                'analytic_distribution': self.both if distribution is None else distribution})]})
        bill.with_context(**(post_context or {})).action_post()
        return self.env['account.asset'].search([('code', '=', bill.name)])

    def _carries(self, move, account):
        return any(str(account.id) in str(k).split(',') for l in move.line_ids for k in (l.analytic_distribution or {}))

    def _first(self, asset):
        return asset.depreciation_line_ids.filtered(lambda l: l.type == 'depreciate' and not l.init_entry).sorted('line_date')[0]

    # ------------------------------------------------------------------ the fund is charged once

    def test_fund_charged_at_purchase_and_never_again(self):
        asset = self._bill('2026-02-10')
        bill_line = self.env['account.move.line'].search([('asset_id', '=', asset.id), ('account_id', '=', self.a_asset.id)])
        self.assertEqual(bill_line.analytic_distribution, self.both, "the purchase is charged to the fund")
        self.assertEqual(asset.source_fund_id, self.fund, "Funded by comes from the bill line")
        self.assertEqual(asset.analytic_distribution, {str(self.programme.id): 100.0},
                         "the asset keeps the programme and loses the fund")
        asset.validate()
        asset.compute_depreciation_board()
        first = self._first(asset)
        first.create_move()
        self.assertEqual(first.move_id.state, 'posted')
        self.assertFalse(self._carries(first.move_id, self.fund), "depreciation never charges the fund")
        self.assertTrue(self._carries(first.move_id, self.programme), "the programme carries the cost")

    def test_an_asset_entered_by_hand_or_from_a_profile_never_holds_the_fund(self):
        by_hand = self.env['account.asset'].create({
            'name': 'Generator', 'profile_id': self.profile.id, 'purchase_value': 6000.0, 'date_start': '2026-03-01',
            'method_time': 'number', 'method_number': 12, 'method_period': 'month', 'analytic_distribution': self.both})
        self.assertEqual(by_hand.source_fund_id, self.fund, "a fund in the analytic becomes Funded by")
        self.assertEqual(by_hand.analytic_distribution, {str(self.programme.id): 100.0})
        self.profile.analytic_distribution = self.both
        from_profile = self.env['account.asset'].create({
            'name': 'Laptop', 'profile_id': self.profile.id, 'purchase_value': 1200.0, 'date_start': '2026-03-01',
            'method_time': 'number', 'method_number': 12, 'method_period': 'month'})
        self.assertEqual(from_profile.analytic_distribution, {str(self.programme.id): 100.0},
                         "a profile's fund never reaches the asset's depreciation")

    def test_without_a_funds_plan_nothing_changes(self):
        self.company.asset_fund_plan_id = False
        asset = self._bill('2026-02-10')
        self.assertFalse(asset.source_fund_id)
        self.assertEqual(asset.analytic_distribution, self.both, "OCA's own behaviour, untouched")

    def test_depreciation_starts_the_month_after_purchase(self):
        for bought, start, first_line in (('2026-02-10', date(2026, 3, 1), date(2026, 3, 31)),
                                          ('2026-01-31', date(2026, 2, 1), date(2026, 2, 28)),
                                          ('2026-02-01', date(2026, 3, 1), date(2026, 3, 31))):
            asset = self._bill(bought)
            self.assertEqual(asset.date_start, start, "bought %s" % bought)
            asset.validate()
            asset.compute_depreciation_board()
            lines = asset.depreciation_line_ids.filtered(lambda l: l.type == 'depreciate').sorted('line_date')
            self.assertEqual(len(lines), 12)
            self.assertEqual(lines[0].line_date, first_line, "nothing in the month of purchase (%s)" % bought)
            self.assertEqual(set(lines.mapped('amount')), {1000.0}, "twelve full months (%s)" % bought)

    def test_disposal_never_charges_the_fund(self):
        asset = self._bill('2026-02-10')
        asset.validate()
        asset.compute_depreciation_board()
        self._first(asset).create_move()
        wizard = self.env['account.asset.remove'].with_context(active_id=asset.id, active_ids=asset.ids).create({
            'date_remove': '2026-04-15', 'posting_regime': 'gain_loss_on_sale', 'sale_value': 5000.0,
            'account_sale_id': self.bank.id, 'account_plus_value_id': self.a_gain.id,
            'account_min_value_id': self.a_loss.id})
        wizard.remove()
        removal = asset.depreciation_line_ids.filtered(lambda l: l.type == 'remove').move_id
        self.assertTrue(removal)
        self.assertFalse(self._carries(removal, self.fund), "the gain or loss line never carries the fund")
        self.assertTrue(self._carries(removal, self.programme))

    # ------------------------------------------------------------------ the opening register

    def test_opening_asset_posts_nothing_and_takes_its_fund_by_hand(self):
        moves_before = self.env['account.move'].search_count([])
        asset = self.env['account.asset'].create({
            'name': 'Old van', 'profile_id': self.profile.id, 'purchase_value': 24000.0,
            'date_start': '2024-01-01', 'method_time': 'number', 'method_number': 48, 'method_period': 'month'})
        self.env['account.asset.line'].create({'asset_id': asset.id, 'amount': 12000.0, 'line_date': '2025-12-31',
                                               'type': 'depreciate', 'init_entry': True})
        asset.compute_depreciation_board()
        self.assertEqual(self.env['account.move'].search_count([]), moves_before, "the opening register posts nothing")
        self.assertFalse(asset.source_fund_id, "may stay empty: unknown, before the system")
        with self.assertRaises(AccessError):   # Billing reads assets only (the access rows)
            asset.with_user(self.billing).write({'source_fund_id': self.fund.id})
        asset.with_user(self.accountant).write({'source_fund_id': self.fund.id})
        self.assertEqual(asset.source_fund_id, self.fund)
        with self.assertRaises(UserError):
            asset.with_user(self.accountant).source_fund_id = self.other_fund   # the fund that paid does not change
        other = self.env['account.asset'].create({
            'name': 'Old car', 'profile_id': self.profile.id, 'purchase_value': 1200.0, 'date_start': '2026-01-01',
            'method_time': 'number', 'method_number': 12, 'method_period': 'month'})
        other.validate()
        other.compute_depreciation_board()
        self._first(other).create_move()
        as_accountant = other.with_user(self.accountant)
        with self.assertRaises(UserError):
            as_accountant.source_fund_id = self.fund   # too late: depreciation is posted
        with self.assertRaises(UserError):     # H1042 F2: no context flag opens it
            as_accountant.with_context(asset_fund_from_bill=True).write({'source_fund_id': self.fund.id})
        with self.assertRaises(UserError):     # nor a fund arriving through the analytic
            as_accountant.write({'analytic_distribution': {str(self.fund.id): 100.0}})
        with self.assertRaises(UserError):     # and a funded asset's fund never moves
            asset.with_user(self.accountant).with_context(asset_fund_from_bill=True).write(
                {'source_fund_id': self.other_fund.id})

    # ------------------------------------------------------------------ Billing (HAVA 06:34Z, DIGITAL)

    def test_billing_reads_assets_and_its_bill_is_never_blocked(self):
        self.profile.open_asset = True   # even then, the clerk's asset waits in draft for finance
        asset = self._bill('2026-02-10', user=self.billing)
        self.assertTrue(asset, "the clerk's bill posted and created the asset")
        self.assertEqual(asset.state, 'draft', "finance confirms it")
        self.assertEqual(asset.source_fund_id, self.fund)
        self.assertEqual(asset.analytic_distribution, {str(self.programme.id): 100.0})
        self.assertTrue(asset.with_user(self.billing).read(['name']))
        with self.assertRaises(AccessError):
            asset.with_user(self.billing).write({'name': 'renamed'})
        with self.assertRaises(AccessError):
            self.env['account.asset'].with_user(self.billing).create(
                {'name': 'x', 'profile_id': self.profile.id, 'purchase_value': 1.0})
        asset.with_user(self.accountant).validate()
        self.assertEqual(asset.state, 'open')

    def test_a_forged_context_never_creates_as_superuser(self):
        """IMPLEMENTER H1042 F1: the clerk's superuser path is gated on the move THIS cursor is
        posting, never on the context an RPC caller sends."""
        posted = self._bill('2026-02-10')
        bill = self.env['account.move'].search([('name', '=', posted.code)])
        forged = self.env['account.asset'].with_user(self.billing).with_context(
            create_asset_from_move_line=True, move_id=bill.id)
        with self.assertRaises(AccessError):
            forged.create({'name': 'Forged', 'profile_id': self.profile.id, 'purchase_value': 5000.0, 'state': 'open'})

    def test_the_clerks_context_never_shapes_the_asset(self):
        """SHIELD H1040 R1: the clerk posts their OWN bill but adds default_* keys. The asset still
        carries the bill's fund, the bill's company and OCA's own depreciation basis."""
        other_company = self.env['res.company'].create({'name': 'Elsewhere'})
        asset = self._bill('2026-02-10', user=self.billing, post_context={
            'default_source_fund_id': self.other_fund.id, 'default_company_id': other_company.id,
            'default_salvage_value': 9000.0, 'default_method_number': 1})
        self.assertEqual(asset.source_fund_id, self.fund, "the bill's fund, never the caller's")
        self.assertEqual(asset.company_id, self.company, "the bill's company")
        self.assertEqual(asset.salvage_value, 0.0)
        self.assertEqual(asset.method_number, self.profile.method_number, "the profile's basis, not the caller's")
        self.assertEqual(asset.state, 'draft')

    def test_the_clerks_asset_takes_only_the_bills_fields(self):
        """SHIELD H1040 C1: on the superuser path the vals are whitelisted to what a bill gives,
        whatever an override of _prepare_asset_vals (another module's) adds."""
        from unittest.mock import patch  # noqa: PLC0415
        Move = type(self.env['account.move'])
        original = Move._prepare_asset_vals

        def widened(move, aml):
            return dict(original(move, aml), salvage_value=9000.0, method_number=1)
        with patch.object(Move, '_prepare_asset_vals', widened):
            asset = self._bill('2026-02-10', user=self.billing)
        self.assertEqual(asset.salvage_value, 0.0)
        self.assertEqual(asset.method_number, self.profile.method_number)

    def test_two_funds_on_one_line_are_refused(self):
        """H1042 F3: one asset, one fund; never a silent pick."""
        split = {str(self.fund.id): 60.0, str(self.other_fund.id): 40.0}
        with self.assertRaises(UserError):
            self._bill('2026-02-10', distribution=split)

    def test_accountant_bill_follows_the_profile(self):
        self.profile.open_asset = True
        asset = self._bill('2026-02-10', user=self.accountant)
        self.assertEqual(asset.state, 'open', "OCA's own open_asset, for finance's own bills")

    # ------------------------------------------------------------------ controls

    def test_a_locked_period_never_receives_depreciation(self):
        """HAVA H1027 (b): lock dates apply. Odoo 20's own posting never writes inside a locked
        period: it moves the entry's date to the first open day (as for every bill and entry), so
        a locked month's depreciation lands as a catch-up after the lock, never in the closed books."""
        asset = self._bill('2026-02-10')
        asset.validate()
        asset.compute_depreciation_board()
        first = self._first(asset)
        self.assertEqual(first.line_date, date(2026, 3, 31))
        self.company.fiscalyear_lock_date = date(2026, 6, 30)
        first.create_move()
        self.assertEqual(first.move_id.state, 'posted')
        self.assertGreater(first.move_id.date, date(2026, 6, 30), "never inside the locked period")
        self.assertFalse(self.env['account.move'].search_count([
            ('id', '=', first.move_id.id), ('date', '<=', '2026-06-30')]))
        self.assertIn('Depreciation 2026-03 (posted after lock)', first.move_id.ref,
                      "the re-dated entry names the month it covers (HAVA 07:20Z)")
        second = asset.depreciation_line_ids.filtered(lambda l: l.type == 'depreciate' and not l.move_id).sorted('line_date')[0]
        self.company.fiscalyear_lock_date = False
        second.create_move()
        self.assertNotIn('posted after lock', second.move_id.ref, "an ordinary month keeps OCA's reference")

    def test_the_fund_shows_its_assets(self):
        asset = self._bill('2026-02-10')
        self.fund.invalidate_recordset()
        self.assertEqual(self.fund.funded_asset_count, 1)
        self.assertEqual(self.fund.action_view_funded_assets()['domain'], [('source_fund_id', '=', self.fund.id)])
        self.assertEqual(self.fund.funded_asset_ids, asset)

    # ------------------------------------------------------------------ AGPL-3 s.13 (LAWYER H1030)

    def test_source_offer_is_on_the_assets_menu(self):
        menu = self.env.ref('nasaq_account_asset.menu_open_source_components')
        self.assertEqual(menu.parent_id, self.env.ref('account_asset_management.menu_finance_assets'))
        self.assertEqual(menu.action.url, 'https://github.com/STRBS/nasaq-open-source')
        visible = self.env['ir.ui.menu'].with_user(self.billing)._visible_menu_ids()
        self.assertIn(menu.id, visible, "every user of the asset modules reaches the offer")
