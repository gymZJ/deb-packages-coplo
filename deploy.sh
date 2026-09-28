#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TARGET_DIR=""
SITE_ADDRESS="${SITE_ADDRESS:-:8080}"
INSTALL_TIMER=true
RUN_SYNC=true
STANDALONE=false
BUILD_FRONTEND=true

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [options]

Deploy the Coplo APT mirror from this checkout.

Options:
  --target DIR          Runtime directory (otherwise prompted interactively)
  --site ADDRESS        Caddy site address for --standalone (default: :8080)
  --standalone          Start the bundled Caddy container after deployment
  --no-timer            Do not install/enable the per-user systemd timer
  --no-sync             Do not run a mirror update after deployment
  --no-build            Reuse an existing ./dist instead of running npm ci/build
  -h, --help            Show this help

Deployment requires an existing GPG secret key. If APT_GPG_KEY_ID is not set,
the script lists available secret-key fingerprints and prompts for one.

The deployed mirror is updated every 30 minutes by a user systemd timer.
For a user timer to survive logouts, enable lingering for the deployment user.
EOF
}

while (($#)); do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { echo "--target requires a value" >&2; exit 2; }
      TARGET_DIR=$2
      shift 2
      ;;
    --site)
      [[ $# -ge 2 ]] || { echo "--site requires a value" >&2; exit 2; }
      SITE_ADDRESS=$2
      shift 2
      ;;
    --standalone) STANDALONE=true; shift ;;
    --no-timer) INSTALL_TIMER=false; shift ;;
    --no-sync) RUN_SYNC=false; shift ;;
    --no-build) BUILD_FRONTEND=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$TARGET_DIR" ]]; then
  printf 'Deployment directory: '
  IFS= read -r TARGET_DIR
  if [[ -z "$TARGET_DIR" ]]; then
    echo "deployment directory cannot be empty" >&2
    exit 2
  fi
fi

TARGET_DIR=$(realpath -m "$TARGET_DIR")
MIRROR_DIR="$TARGET_DIR/mirror"
FRONTEND_DIR="$TARGET_DIR/frontend"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

require_command python3
require_command dpkg-deb
require_command gpg
require_command flock
require_command rsync
require_command realpath

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required (tomllib is used by mirror/sync.py)")
PY

if [[ "$BUILD_FRONTEND" == true ]]; then
  require_command node
  require_command npm
  node -e 'const major=Number(process.versions.node.split(".")[0]); if (major < 24) { console.error("Node.js 24+ is required"); process.exit(1) }'
  (cd "$ROOT_DIR" && npm ci && npm run build)
elif [[ ! -f "$ROOT_DIR/dist/index.html" ]]; then
  echo "--no-build requested but $ROOT_DIR/dist/index.html does not exist" >&2
  exit 1
fi

install -d -m 0755 "$TARGET_DIR" "$MIRROR_DIR" "$FRONTEND_DIR"

# Deployment is declarative: version-controlled files are replaced with the
# current checkout every time. Runtime data produced by the mirror itself is
# not treated as an old-version compatibility concern.

install -m 0755 "$ROOT_DIR/mirror/run-update.sh" "$MIRROR_DIR/run-update.sh"
install -m 0755 "$ROOT_DIR/mirror/sync.py" "$MIRROR_DIR/sync.py"
install -m 0644 "$ROOT_DIR/mirror/packages.toml" "$MIRROR_DIR/packages.toml"
install -m 0644 "$ROOT_DIR/mirror/mirror.env.example" "$MIRROR_DIR/mirror.env.example"

if [[ -z "${APT_GPG_KEY_ID:-}" ]]; then
  echo "Available secret GPG keys:"
  mapfile -t secret_fingerprints < <(
    gpg --batch --with-colons --list-secret-keys 2>/dev/null \
      | awk -F: '$1 == "fpr" { print $10 }'
  )
  if ((${#secret_fingerprints[@]} == 0)); then
    echo "no secret GPG keys are available" >&2
    exit 1
  fi
  printf '  %s\n' "${secret_fingerprints[@]}"
  printf 'APT signing key fingerprint: '
  IFS= read -r APT_GPG_KEY_ID
  if [[ -z "$APT_GPG_KEY_ID" ]]; then
    echo "APT signing key fingerprint cannot be empty" >&2
    exit 2
  fi
fi

key_id=$(printf '%s' "$APT_GPG_KEY_ID" | tr -d '[:space:]')
if ! gpg --batch --list-secret-keys "$key_id" >/dev/null 2>&1; then
  echo "secret GPG key '$key_id' is not available" >&2
  exit 1
fi

cat > "$MIRROR_DIR/mirror.env" <<EOF
APT_GPG_KEY_ID=$key_id
GITHUB_TOKEN=${GITHUB_TOKEN:-}
EOF
chmod 0600 "$MIRROR_DIR/mirror.env"

rsync -a --delete "$ROOT_DIR/dist/" "$FRONTEND_DIR/"

if [[ "$INSTALL_TIMER" == true ]]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    unit_dir="$HOME/.config/systemd/user"
    install -d -m 0755 "$unit_dir"
    sed "s|__MIRROR_DIR__|$MIRROR_DIR|g" \
      "$ROOT_DIR/deploy/systemd/coplo-mirror.service" \
      > "$unit_dir/coplo-mirror.service"
    install -m 0644 "$ROOT_DIR/deploy/systemd/coplo-mirror.timer" \
      "$unit_dir/coplo-mirror.timer"
    systemctl --user daemon-reload
    systemctl --user enable --now coplo-mirror.timer

    if command -v loginctl >/dev/null 2>&1; then
      linger=$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)
      if [[ "$linger" != yes ]]; then
        if loginctl enable-linger "$USER" >/dev/null 2>&1; then
          :
        elif command -v sudo >/dev/null 2>&1 && sudo -n loginctl enable-linger "$USER" >/dev/null 2>&1; then
          :
        else
          echo "warning: user lingering is disabled; the timer may stop after logout" >&2
          echo "enable it with: sudo loginctl enable-linger $USER" >&2
        fi
      fi
    fi
  else
    echo "warning: systemd user manager is unavailable; timer installation skipped" >&2
  fi
fi

if [[ "$RUN_SYNC" == true ]]; then
  "$MIRROR_DIR/run-update.sh" --force
fi

if [[ "$STANDALONE" == true ]]; then
  require_command docker
  docker compose version >/dev/null
  standalone_dir="$TARGET_DIR/standalone"
  install -d -m 0755 "$standalone_dir"
  install -m 0644 "$ROOT_DIR/deploy/standalone/Caddyfile" "$standalone_dir/Caddyfile"
  install -m 0644 "$ROOT_DIR/deploy/standalone/compose.yaml" "$standalone_dir/compose.yaml"
  cat > "$standalone_dir/.env" <<EOF
COPLO_DEPLOY_DIR=$TARGET_DIR
SITE_ADDRESS=$SITE_ADDRESS
EOF
  (
    cd "$standalone_dir"
    docker compose up -d
  )
fi

printf '\nCoplo mirror deployed to %s\n' "$TARGET_DIR"
printf 'Frontend: %s\nMirror:   %s\n' "$FRONTEND_DIR" "$MIRROR_DIR"
if [[ "$INSTALL_TIMER" == true ]]; then
  printf 'Timer:    systemctl --user status coplo-mirror.timer\n'
fi
if [[ "$STANDALONE" == true ]]; then
  printf 'Site:     %s\n' "$SITE_ADDRESS"
fi
