## Settings apply safety gap

Before live settings apply is enabled, the installer must close two existing resume-path gaps:

- switching managed API access from Docker/LAN to `local` must remove the owned proxy resources;
- switching from managed systemd service to no-service must remove the owned unit rather than only changing the manifest field.

Until those cleanup paths are transactional/recoverable, completed-install settings editing stays
preview-only and exits through the existing dry-run boundary.
