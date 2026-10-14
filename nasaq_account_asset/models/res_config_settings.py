# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    asset_fund_plan_id = fields.Many2one(related='company_id.asset_fund_plan_id', readonly=False)
