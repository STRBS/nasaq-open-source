# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # LAWYER H1035: this module depends on OCA and core Odoo only. The restricted funds are
    # whatever analytic plan the company names here; on Nasaq that is its Funds plan.
    asset_fund_plan_id = fields.Many2one(
        'account.analytic.plan', string="Funds Plan for Assets",
        help="The analytic plan whose accounts are restricted funds. An asset bought on one of them "
             "records it as 'Funded by', and its depreciation and disposal entries never carry it: "
             "the fund is charged once, at purchase.")
