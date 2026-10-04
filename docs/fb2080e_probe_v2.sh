#!/usr/bin/env bash
# FB2080E visibility + SANE-runtime diagnostics, v2 (2026-10-03).
# Run from the Ubuntu host's normal desktop terminal, not through sudo.
# No image scan, installation, system configuration change, raw USB command,
# firmware upload, or network request is performed. SANE discovery/opening can
# initialize a connected scanner. --passive skips discovery and device opening.
set -uo pipefail
umask 077
export LC_ALL=C

usage() { printf 'Usage: bash %s [--passive] [output-parent-directory]\n' "$0"; }
passive=0
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if [[ ${1:-} == --passive ]]; then passive=1; shift; fi
if (( $# > 1 )) || [[ ${1:-} == --* ]]; then usage >&2; exit 2; fi
if (( EUID == 0 )); then
    printf 'Run as your normal desktop user, not with sudo. Root hides the access problem being investigated.\n' >&2
    exit 2
fi
parent=${1:-"$PWD"}
mkdir -p -- "$parent" || exit 1
parent=$(cd -- "$parent" && pwd -P) || exit 1
out=$(mktemp -d "$parent/fb2080e-probe-v2-XXXXXXXX") || exit 1
printf 'Diagnostics: %s\nNo image scan will be requested. Close other scanner applications.\n' "$out"

run() {
    local label=$1 seconds=$2 rc
    shift 2
    { printf 'Command: '; printf '%q ' "$@"; printf '\n'; } > "$out/$label.command.txt"
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'Command unavailable: %s\n' "$1" > "$out/$label.stderr.txt"
        : > "$out/$label.stdout.txt"
        printf '127\n' > "$out/$label.exit-status.txt"
        return 0
    fi
    if command -v timeout >/dev/null 2>&1; then
        timeout --kill-after=5s "${seconds}s" "$@" > "$out/$label.stdout.txt" 2> "$out/$label.stderr.txt"
        rc=$?
    else
        "$@" > "$out/$label.stdout.txt" 2> "$out/$label.stderr.txt"
        rc=$?
    fi
    printf '%s\n' "$rc" > "$out/$label.exit-status.txt"
    return 0
}

{
    printf 'UTC: '; date -u '+%Y-%m-%dT%H:%M:%SZ'
    uname -srmo
    printf 'Effective UID: %s\nPassive mode: %s\n' "$EUID" "$passive"
    cat /etc/os-release 2>/dev/null || true
} > "$out/system.txt"
{
    printf 'Executable resolution in this script process:\n'
    type -a scanimage lsusb env timeout 2>&1 || true
    printf '\nSelected environment variables (not a full environment dump):\n'
    for var in PATH LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT SANE_CONFIG_DIR SNAP FLATPAK_ID container WSL_DISTRO_NAME; do
        printf '%s=%q\n' "$var" "${!var-}"
    done
    printf '\nProcess confinement hints (not proof of a sandbox):\n'
    grep -E '^(Uid|Gid|CapEff|NoNewPrivs|Seccomp):' /proc/self/status 2>/dev/null || true
    cat /proc/self/attr/current 2>/dev/null || true
    printf '\n'
    for marker in /.dockerenv /run/.containerenv /.flatpak-info; do
        [[ ! -e "$marker" ]] || printf 'Marker exists: %s\n' "$marker"
    done
} > "$out/execution-context.txt"
run virtualization 10 systemd-detect-virt
run container-detection 10 systemd-detect-virt --container
run packages 15 dpkg-query -W '-f=${binary:Package}\t${Version}\n' sane-utils libsane1 libsane-common usbutils
run package-integrity 30 dpkg --verify sane-utils libsane1 libsane-common

# Capture ALL USB IDs; the old script only captured the expected model ID.
run usb-all 10 lsusb
run usb-topology 10 lsusb -t
run usb-avision-vendor 10 lsusb -d 0638:
run usb-exact-target 10 lsusb -d 0638:0a84
exact_count=0
{
    for d in /sys/bus/usb/devices/*; do
        [[ -r "$d/idVendor" && -r "$d/idProduct" ]] || continue
        vendor=$(cat "$d/idVendor" 2>/dev/null) || continue
        product=$(cat "$d/idProduct" 2>/dev/null) || continue
        [[ $vendor != 0638 || $product != 0a84 ]] || exact_count=$((exact_count + 1))
        printf '\nUSB path: %s  ID=%s:%s\n' "$d" "$vendor" "$product"
        for attr in manufacturer product bcdDevice authorized busnum devnum speed; do
            if [[ -r "$d/$attr" ]]; then printf '%s=' "$attr"; cat "$d/$attr" 2>/dev/null; fi
        done
        # Do not deliberately read the serial attribute.
        if [[ -r "$d/busnum" && -r "$d/devnum" ]]; then
            bus=$(cat "$d/busnum" 2>/dev/null); dev=$(cat "$d/devnum" 2>/dev/null)
            if [[ $bus =~ ^[0-9]+$ && $dev =~ ^[0-9]+$ ]]; then
                printf -v node '/dev/bus/usb/%03d/%03d' "$((10#$bus))" "$((10#$dev))"
                stat -c 'Node=%n mode=%a owner=%U group=%G' "$node" 2>/dev/null || true
                readable=no; writable=no
                [[ ! -r "$node" ]] || readable=yes
                [[ ! -w "$node" ]] || writable=yes
                printf 'Shell access check: readable=%s writable=%s (not an actual USB open test)\n' "$readable" "$writable"
                if [[ $vendor == 0638 ]] && command -v getfacl >/dev/null 2>&1; then
                    getfacl -p "$node" 2>/dev/null || true
                fi
            fi
        fi
    done
} > "$out/usb-sysfs-all.txt"
printf '%s\n' "$exact_count" > "$out/exact-target-sysfs-count.txt"

scan_path=$(type -P scanimage 2>/dev/null || true)
{
    printf 'PATH-selected scanimage: %s\n' "${scan_path:-NOT FOUND}"
    for p in "$scan_path" /usr/bin/scanimage; do
        [[ -n "$p" && -e "$p" ]] || continue
        printf '\nExecutable: %s\n' "$p"
        real=$(readlink -f -- "$p" 2>/dev/null) || real=$p
        printf 'Resolved: %s\n' "$real"
        stat -c 'File=%n size=%s mode=%a modified=%y' "$real" 2>/dev/null || true
        sha256sum -- "$real" 2>/dev/null || true
        if command -v dpkg-query >/dev/null 2>&1; then dpkg-query -S "$p" "$real" 2>&1 || true; fi
        if command -v readelf >/dev/null 2>&1; then
            readelf -d "$real" 2>/dev/null | grep -E 'NEEDED|RPATH|RUNPATH' || true
        fi
    done
} > "$out/executable-files.txt"
[[ -z "$scan_path" ]] || run version-path 10 "$scan_path" --version
# This removes common environment overrides, but does not bypass loader caches,
# RPATH, overwritten files, /etc/ld.so.preload, or a container's filesystem.
clean=(env -u LD_LIBRARY_PATH -u LD_PRELOAD -u LD_AUDIT -u SANE_CONFIG_DIR -u LD_DEBUG_OUTPUT)
scanner=$scan_path
if [[ -x /usr/bin/scanimage ]]; then
    scanner=/usr/bin/scanimage
    run version-system 10 "${clean[@]}" /usr/bin/scanimage --version
    run loader-system 10 "${clean[@]}" LD_DEBUG=libs /usr/bin/scanimage --version
elif [[ -n "$scanner" ]]; then
    run version-fallback 10 "${clean[@]}" "$scanner" --version
    run loader-fallback 10 "${clean[@]}" LD_DEBUG=libs "$scanner" --version
fi
{
    for f in /etc/sane.d/dll.conf /etc/sane.d/avision.conf /etc/sane.d/dll.d/*; do
        [[ -f "$f" && -r "$f" ]] || continue
        printf '\n--- %s ---\n' "$f"
        grep -Ein 'avision|0638|0a84' "$f" || true
    done
} > "$out/config-relevant-lines.txt"

visible=0
if (( exact_count > 0 )) || grep -Eqi 'ID[[:space:]]+0638:0a84([[:space:]]|$)' "$out/usb-all.stdout.txt" "$out/usb-exact-target.stdout.txt"; then
    visible=1
fi
{
    printf 'Expected USB ID visible in this process: %s\n' "$visible"
    printf 'Exact sysfs matches: %s\n' "$exact_count"
    printf 'PATH-selected executable: %s\n' "${scan_path:-NOT FOUND}"
    printf 'Executable selected for device discovery: %s\n' "${scanner:-NOT FOUND}"
    if (( visible == 0 )); then
        printf 'No exact USB match. Check usb-all and usb-sysfs-all for another ID.\n'
        printf 'Device discovery skipped; this is not a scanner-protocol test or proof of hardware failure.\n'
        printf 'Repeat from the real Ubuntu host terminal with the scanner powered and connected.\n'
    elif (( passive == 1 )); then
        printf 'Exact USB match present. SANE device discovery skipped by --passive.\n'
    fi
} > "$out/SUMMARY.txt"

if (( visible == 1 && passive == 0 )) && [[ -n "$scanner" ]]; then
    cfg="$out/isolated-sane-config"
    mkdir -p -- "$cfg/dll.d" "$cfg/dll.aliases.d"
    printf 'avision\n' > "$cfg/dll.conf"
    printf 'usb 0x0638 0x0a84\n' > "$cfg/avision.conf"
    # Enabling avision limits backend selection, not necessarily probing to one
    # physical USB device: avision also checks its compiled-in model table.
    run avision-discovery 45 "${clean[@]}" SANE_CONFIG_DIR="$cfg" SANE_DEBUG_DLL=3 \
        SANE_DEBUG_AVISION=7 SANE_DEBUG_SANEI_USB=3 "$scanner" -f '%d|%v|%m%n'
    mapfile -t devices < <(awk -F'|' 'tolower($1) ~ /^avision:/ && tolower($3) ~ /fb2080e/ {print $1}' \
        "$out/avision-discovery.stdout.txt" | sort -u)
    printf 'SANE FB2080E device matches: %s\n' "${#devices[@]}" >> "$out/SUMMARY.txt"
    if (( ${#devices[@]} == 1 )); then
        printf '%s\n' "${devices[0]}" > "$out/device-name.txt"
        run device-help 45 "${clean[@]}" SANE_CONFIG_DIR="$cfg" SANE_DEBUG_AVISION=7 \
            "$scanner" -d "${devices[0]}" --help
        run device-options 45 "${clean[@]}" SANE_CONFIG_DIR="$cfg" SANE_DEBUG_AVISION=7 \
            "$scanner" -d "${devices[0]}" -A
        printf 'Device option queries attempted. No image scan requested; inspect exit codes.\n' >> "$out/SUMMARY.txt"
    fi
elif [[ -z "$scanner" ]]; then
    printf 'scanimage unavailable; install sane-utils using your normal package manager.\n' >> "$out/SUMMARY.txt"
fi

cat > "$out/README.txt" <<'TXT'
FB2080E diagnostic v2
Read SUMMARY.txt, usb-all.stdout.txt, usb-sysfs-all.txt, execution-context.txt,
executable-files.txt, version-*.stdout.txt, loader-*.stderr.txt, then any
avision-discovery/device-help/device-options logs.

No image scan, installation, persistent configuration edit, raw USB command,
firmware upload, sudo invocation, or network access is performed. SANE discovery
can initialize scanners; --passive skips discovery and device option queries.
Missing tools or restricted access are logged, not fixed automatically.

Exit code 0 on enumeration does NOT prove a scanner was found. The number of
returned devices matters. 124/137 can indicate a command timeout.

Run from a normal terminal on the host with the USB cable, not an agent's
sandbox/container. Container/virtualization hints cannot establish where the
scanner is actually attached. The cleaned environment comparison does not
force packaged library files or override confinement.

Privacy: the archive includes local paths, USB model names/IDs, permissions and
selected environment values. Backend logs can include device serial numbers.
Review before sharing. No upload is performed.
TXT
archive="$out.tar.gz"
if tar -czf "$archive" -C "$parent" "$(basename "$out")"; then
    cat "$out/SUMMARY.txt"
    printf '\nArchive: %s\n' "$archive"
else
    printf 'Archiving failed; logs are retained in %s\n' "$out" >&2
    exit 1
fi
