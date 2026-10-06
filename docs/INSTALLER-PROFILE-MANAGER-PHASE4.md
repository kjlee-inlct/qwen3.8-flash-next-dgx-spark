# Completed-install settings preview slice

This temporary phase note records the implementation boundary while the canonical
`docs/INSTALLER-PROFILE-MANAGER.md` is updated before merge.

The completed-install Wizard now enters an installed-setup management menu before the existing
profile selector. The menu offers profile selection/switch, a runtime/API/service settings
preview, current-profile default refresh, or cancel. Settings are staged in memory and applied
only at the shared `[6/6]` normalized-plan boundary, so manifest re-parsing and explicit CLI
overrides retain their existing precedence.

The settings editor covers config override, monitor/protection thresholds, API access/ports,
and service enablement. This first slice is deliberately preview-only: selecting settings forces
the run to the existing dry-run exit. The existing resume execution path does not currently
remove a managed proxy when changing LAN/Docker access to local-only, nor remove a managed
systemd unit when changing service-enabled to service-disabled. Opening live apply before those
cleanup semantics are transactional would allow manifest/host-resource drift.

Profile-default refresh is now reachable from the completed-install Wizard and continues to use
the existing `REFRESH_PROFILE_DEFAULTS` path. No install manifest schema, runtime transaction,
profile-switch transaction, service ownership rule, or qualification state changes in this
slice.
