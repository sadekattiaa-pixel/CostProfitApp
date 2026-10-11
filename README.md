# Invoice

Developed by **Alintilqa Programming & Digital Solutions**.
© 2026 Alintilqa Programming & Digital Solutions. All rights reserved.
جميع الحقوق محفوظة للشركة المطوّرة.

Desktop application for supplier, product, invoice, cost, and profit management.

**Current source version: 2.1.0** (maintenance updated 12 October 2026).
Developer attribution and copyright were updated in the source on 12 October 2026.
The existing Windows installer was built on 11 October and does not include these
latest attribution changes. No installer was rebuilt for this update.

## Version 2.1.0 — 11 October 2026

This release assigns version 2.1.0 to the current reviewed source, including the
21 staged maintenance fixes. The application screens, package version, installer
definitions, and future Windows version metadata are consistent. No executable
or installer was built as part of this version update.

## Previous updates in 1.2.0

This update fixes the 17 confirmed issues identified in the comprehensive review:

- Preserve newer local work during session recovery; validate backup databases
  and roll back failed restores of the database and images.
- Normalize Excel dates, match tire patterns and suppliers, and group invoices
  by supplier and invoice number. Reject invalid prices and quantities.
- Preserve unit-price precision when saving, copying, and editing invoices;
  search legacy batteries by code and place Excel images in the correct column.
- Use archived product details in historical reports, refresh invoice suppliers,
  and apply changes to the automatic backup interval immediately.
- Offer Save, Discard, or Cancel for unsaved invoice changes; handle malformed
  storage configuration and session locks; restrict imports to supported XLSX files.

See [CHANGELOG.md](CHANGELOG.md) for the change history and
[HANDOFF.md](HANDOFF.md) for the project state and maintenance rules.

## Staged reliability and scale fixes — 11 October 2026

The 21 confirmed findings B01–B21 were addressed in four tested stages:

- Publish only complete backup archives; preserve old storage settings and logos
  if writing fails. Image deletion follows the outer database commit.
- Keep fractional quantities and historical product identities. Reject invalid
  product dimensions and ambiguous supplier names; unique supplier codes take priority.
- Round monetary line totals to cents and sum those totals. Allocate cost rounding
  cents cumulatively so line costs equal invoice net cost and line profits equal
  invoice profit. Round each payment, discount, and expense to cents. Keep unit
  price precision and calculate the exchange rate from the unrounded USD basis;
  its ratio can differ from displayed rounded totals. Existing archived totals
  are preserved; new saves/recalculations use this policy.
- Export user text as literal Excel values, sanitize worksheet titles and suggested
  filenames, and escape user text in PDF reports.
- Show 100 rows per page in suppliers, products, and invoice lists. Search resets
  the page; exports include every matching record. Heavy pages open on demand.
- Reuse product catalog models and materialize historical JSON once per report.
- Publish using a worker-owned read-only database connection. Keep edits made
  during publication pending for another save, defer image cleanup until the
  worker finishes, and serialize restore/reset/shutdown with publication.
  Directory notifications trigger checks; a 30-second background fallback detects
  external image edits without scanning all images every idle UI tick.

Final verification: **134 tests and 3 subtests passed**, including 50,000 invoices,
500,000 invoice lines, 1,000-row imports/exports, and injected storage failures.
The evidence, baseline comparison, and staged implementation report are under
`CostProfitApp_gpt/staged-fixes-20261010`; no installer was built.

## Run locally

Use a configured Python environment with the dependencies in `requirements.txt`,
then run `python -B run_app.py` from a working copy. The `-B` option prevents
Python bytecode files from being created in the source tree.

For this workspace, keep the primary `CostProfitApp` folder clean: create working
copies, environments, test data, reports, and generated files under the sibling
`CostProfitApp_gpt` folder. Run tests in an isolated copy there, because some
existing tests create temporary databases beside the test files.

Select a writable data folder when prompted. Move the entire packaged application
folder when copying it between drives or computers. Each computer must meet the
application requirements.

## Activation and portable use

Device activation and license binding have been removed for both installed and
portable operation, including USB activation security. The application does not
require an activation record or an activation utility.

Portable operation remains available. Login passwords, screen locking, the
shared-session lock, backups, and data-recovery protections remain in place.
The machine identity used by the shared-session lock identifies a session owner;
it does not bind the application license to a computer.

## Invoice import and unsaved changes

Invoice import supports `.xlsx` files. Suppliers and products must already exist;
import does not create them automatically. Tire matching considers the pattern,
category, and supplier. An unknown template supplier can be replaced by the
matched product's existing supplier, while a conflicting known supplier is rejected.

Dates are stored as `YYYY-MM-DD`. Present price columns must contain valid
positive numbers; a missing price column may use the other price column. A blank,
zero, negative, or non-finite value in a present column is rejected. Rows for the
same supplier invoice must use the same date.

Unsaved invoice changes prompt for Save, Discard, or Cancel before closing or
opening another invoice. This also protects closing the lock screen and restarting
for a storage-folder change or backup restore. It does not automatically save
form input during a power failure or forced process termination.

Historical product reports use archived product snapshots when available.
Older invoices without snapshots fall back to the current product catalog.

## OneDrive and sequential use

Select the same shared data-and-images folder on each computer. Folder paths are
device-local. On each computer, set the OneDrive folder to
Always keep on this device. Never open the program on two computers at once.
Close the first program and wait for OneDrive to upload ALL changes, then wait
for the next computer to download ALL changes before opening the program there.
The startup confirmation is manual; Invoice does not claim to verify cloud sync.
The shared file lock is an aid, not a distributed lock or server lease.

Sessions run on a durable local database and local images, under
`%LOCALAPPDATA%/CostProfitApp/Sessions`. On successful closing, Invoice publishes a
complete database snapshot and updated images to the selected shared folder.
Opening a session acquires the shared lock before opening the database. Locks
never expire automatically. Recovery of an old lock requires explicit confirmation.
Malformed locks are preserved and are not released automatically.

An unfinished local session is preserved for explicit recovery, including local
changes made after a publication whose final session-record update failed.
If the shared database has changed, Invoice refuses to overwrite it with the old
local session. You may explicitly archive the unfinished local work in a local
backup and open the current shared data, preserving the old work for review
rather than merging it.

## Backups and restoration

Automatic and manual backups remain outside OneDrive, locally under
`%LOCALAPPDATA%/CostProfitApp/Backups` by default. Choose a different local backup
folder in Settings if needed. Changing the automatic backup interval takes effect
immediately. Existing user data and backup archives are not moved or deleted by
this source update.

Restore checks the database integrity, required application schema, and database
relationships before replacing live data. It prepares incoming images and creates
a before-restore backup. Failed replacement attempts roll back to the previous
database and images and reopen the database connection. If rollback itself fails,
recovery files are retained at the location reported by the application.
Restore operates on the local session. Committed data is published in the background
and again on successful closing; unfinished publication is awaited before closing.

## Validation

Version 1.2.0 was checked on an isolated working copy:

- 32 existing project tests, 54 regression tests, and two startup tests passed:
  **88 tests and 3 subtests passed**.
- Python and PowerShell syntax checks passed. Windows version-resource data was
  checked without building an executable.
- Additional import checks passed for distinct tire patterns and numeric values
  that cannot be represented for storage.

The additional regression tests and validation reports are stored under
`CostProfitApp_gpt/release-1.2.0-20261008`, outside the primary project.
Physical printer behavior, OneDrive synchronization between two real computers,
and installation of a newly built package were not tested in this update.

## Build for Windows

**Build installer packages only when the user explicitly requests them.**
No application or installer build was performed for the 2.1.0 update.
For this workspace, run any subsequently authorized build from a working copy
under `CostProfitApp_gpt`, keeping generated output outside the primary project.

The existing `build_windows.ps1` and `build_installer.ps1` scripts build the
application and Windows installer. The executable path in the build copy is
`dist/Invoice/Invoice.exe`; the installer name is
`dist/installer/Invoice-Setup-2.1.0.exe`.

The old portable installer and its build definitions have been removed. The
independent single-file portable edition is maintained under
`CostProfitApp_gpt/portable-2.1.0`, with its own source and build script.
Its executable is `output/Invoice.exe`; it uses the embedded default data path
and stores session path choices in memory without a permanent configuration file.
Both editions preserve shared-data session protection.

The Python package, application screens, build-script messages, and future
Windows executable version metadata derive their version from `APP_VERSION` in
`app/config.py`. The Windows installer definition also specifies `2.1.0` and must remain
consistent with it when upgrading the version.
