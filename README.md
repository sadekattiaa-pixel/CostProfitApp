# Invoice

Desktop application for supplier, product, invoice, cost, and profit management.

## Run locally

Use the configured Python environment and run `python run_app.py`.
The application automatically binds on its first launch. Source development stores
its binding outside the project. Packaged copies store the protected device record
in `License/device.dat` beside Invoice.exe; move the entire application folder
when moving the copy between drives on the same Windows computer.
The binding is protected by Windows DPAPI and the Windows device identity.
Reinstalling Windows may require a fresh copy. Deleting the record or copying an
unactivated copy can permit fresh automatic activation; this is not a central
license-enforcement system. Existing manual signing keys are not used or deleted.

## OneDrive and sequential use

Select the same shared data-and-images folder on each computer. Folder paths and
activation records are device-local. On each computer, set the OneDrive folder to
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
An unfinished local session is preserved for recovery. If the shared database
has changed, Invoice refuses to overwrite it with the old local session. You may
explicitly archive the unfinished local work in a local backup and open the
current shared data, preserving the old work for review rather than merging it.

Automatic and manual backups remain outside OneDrive, locally under
`%LOCALAPPDATA%/CostProfitApp/Backups` by default. Existing data and backup archives
are not moved or deleted by this update. Choose a different local backup folder
in Settings if needed. Restore operates on the local session and publishes on
closing, with a before-restore backup.

## Build for Windows

Use the existing `build_windows.ps1` and `build_installer.ps1` scripts.
The executable is `dist/Invoice/Invoice.exe`, and the installer is named Invoice.
`build_usb_package.ps1` packages the portable copy; activation is automatic on the
computer at first launch. The old activator tool now only inspects device records.
