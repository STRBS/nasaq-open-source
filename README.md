# Nasaq — open-source components

This repository holds **only the open-source components** that run inside **Nasaq**, an Odoo 20 system for non-profit organisations. They are published under the **GNU Affero General Public License v3** (see `LICENSE`), as section 13 of that licence requires: every user of these modules over a network can get the source of the version they use.

## Ownership and licence

- **Nasaq** is the name and mark of the Nasaq platform's owner (the Center). This repository holds only the open-source components it runs.
- The OCA modules (`account_asset_management`, `report_xlsx`, `report_xlsx_helper`) are written and owned by the **Odoo Community Association (OCA) and its contributors**, as their copyright notices and manifests say. **STRIDE Business Solutions is the porter of `account_asset_management` to Odoo 20.0 only, not its owner or author.**
- `nasaq_account_asset` is written by STRIDE Business Solutions (its manifest author) and licensed AGPL-3.
- **Each module keeps its own licence** as stated in its `__manifest__.py` and file headers. The AGPL-3 text in `LICENSE` applies to all four modules.

**The default branch, `main`, always holds the code that runs.** Each deployment is also tagged (see *Deployments* below).

## What is here

| Module | Licence | Source | Changes by STRIDE |
|---|---|---|---|
| `account_asset_management` | AGPL-3 | [OCA/account-financial-tools](https://github.com/OCA/account-financial-tools), branch 19.0 @ `ddcabb93373382148826f97bf9935424d03ddea5` | Ported to Odoo 20.0: security moved to `ir.access.csv`, six icon names, versions. Each changed file is marked *Modified by Stride for Odoo 20.0, 2026-10*. Offered back to OCA. |
| `report_xlsx` | AGPL-3 | [OCA/reporting-engine](https://github.com/OCA/reporting-engine) pull request #1203 @ `b07289ada619afe1c36cef8df47cfb31794aa3af` | None (OCA's own Odoo 20 migration). |
| `report_xlsx_helper` | AGPL-3 | [OCA/reporting-engine](https://github.com/OCA/reporting-engine) pull request #1214 @ `c27dd95` | None (OCA's own Odoo 20 migration). |
| `nasaq_account_asset` | AGPL-3 | STRIDE Business Solutions | Written by STRIDE. Applies the restricted-fund rule to the asset register: an asset bought with a restricted fund is charged to that fund once, at purchase; depreciation and disposal never charge it again. Depends only on `account_asset_management` and Odoo core. |

The authors and copyright notices of the OCA modules are unchanged. Python libraries needed: `python-dateutil`, `xlsxwriter`, `xlrd`.

## Deployments

| Tag | Date | What it is |
|---|---|---|
| `nasaq-0673cf7` | 2026-10-14 | First deployment: all four modules installed (`account_asset_management` with Stride's Odoo 20.0 port, `report_xlsx`, `report_xlsx_helper`, `nasaq_account_asset` 20.0.1.0.0). The tag points at the commit whose module code was deployed. |

## Contributing

Changes to the OCA modules go to OCA first, through its own repositories and review. This repository follows OCA's releases.
