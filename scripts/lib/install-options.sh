#!/usr/bin/env bash
# Canonical user-facing installer option inventory.
#
# Fields:
#   id<TAB>class<TAB>wizard<TAB>usage-fragment<TAB>long-flags
#
# class is one of:
#   setting        persisted/runtime configuration exposed by CLI and Wizard
#   informational read-only command surface
#   maintenance   explicit maintenance operation, not a normal Wizard setting
#   control       execution/help control, not persisted configuration
#
# Multiple long flags in one logical option group are comma-separated.

install_option_registry() {
  printf '%s\t%s\t%s\t%s\t%s\n' \
    profile setting yes '[--model PROFILE]' '--model' \
    model_root setting yes '[--model-root PATH]' '--model-root' \
    config_override setting yes '[--config-override PATH]' '--config-override' \
    list_models informational no '[--list-models]' '--list-models' \
    list_backends informational no '[--list-backends]' '--list-backends' \
    language setting yes '[--lang en|ko]' '--lang' \
    confirmation control no '[--yes]' '--yes' \
    start_policy setting yes '[--no-start]' '--no-start' \
    service_mode setting yes '[--service|--no-service]' '--service,--no-service' \
    monitor_mode setting yes '[--monitor|--no-monitor|--protect]' '--monitor,--no-monitor,--protect' \
    monitor_min_available setting yes '[--monitor-min-available-gib N]' '--monitor-min-available-gib' \
    monitor_min_free setting yes '[--monitor-min-free-gib N]' '--monitor-min-free-gib' \
    monitor_free_gate setting yes '[--monitor-free-gate-gib N]' '--monitor-free-gate-gib' \
    monitor_min_swap_free setting yes '[--monitor-min-swap-free-gib N]' '--monitor-min-swap-free-gib' \
    monitor_consecutive setting yes '[--monitor-consecutive N]' '--monitor-consecutive' \
    monitor_heartbeat setting yes '[--monitor-heartbeat N]' '--monitor-heartbeat' \
    api_access setting yes '[--api-access local|docker|lan]' '--api-access' \
    api_docker_port setting yes '[--api-docker-port N]' '--api-docker-port' \
    api_lan_address setting yes '[--api-lan-address IPv4]' '--api-lan-address' \
    api_lan_port setting yes '[--api-lan-port N]' '--api-lan-port' \
    manifest_migration maintenance no '[--migrate-manifest]' '--migrate-manifest' \
    refresh_profile_defaults setting yes '[--refresh-profile-defaults]' '--refresh-profile-defaults' \
    dry_run setting yes '[--dry-run]' '--dry-run' \
    help control no '[-h|--help]' '--help'
}

install_option_long_flags() {
  local id class wizard usage flags flag
  local -a flag_list=()

  while IFS=$'\t' read -r id class wizard usage flags; do
    IFS=',' read -r -a flag_list <<<"${flags}"
    for flag in "${flag_list[@]}"; do
      [[ -n "${flag}" ]] && printf '%s\n' "${flag}"
    done
  done < <(install_option_registry)
}

install_option_usage() {
  local id class wizard fragment flags
  printf 'Usage: ./install.sh'
  while IFS=$'\t' read -r id class wizard fragment flags; do
    printf ' %s' "${fragment}"
  done < <(install_option_registry)
  printf '\n'
  printf '       ./install.sh  # interactive English/Korean wizard (default)\n'
}

install_option_flag() {
  local wanted_id="$1" wanted_variant="${2:-}"
  local id class wizard usage flags flag
  local -a flag_list=()

  while IFS=$'\t' read -r id class wizard usage flags; do
    [[ "${id}" == "${wanted_id}" ]] || continue
    IFS=',' read -r -a flag_list <<<"${flags}"
    if [[ -z "${wanted_variant}" ]]; then
      [[ "${#flag_list[@]}" == 1 ]] || return 2
      printf '%s\n' "${flag_list[0]}"
      return 0
    fi
    for flag in "${flag_list[@]}"; do
      [[ "${flag}" == "--${wanted_variant}" ]] || continue
      printf '%s\n' "${flag}"
      return 0
    done
    return 2
  done < <(install_option_registry)

  return 1
}
