#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE="${BASE:-$SCRIPT_DIR}"
RELEASES_DIR="$BASE/releases"
LIVE_LINK="$BASE/www"
LOCK_FILE="$BASE/update.lock"
STATE_FILE="$BASE/release-state.json"
NEXT_STATE="$BASE/.release-state.new"

if [[ -f "$BASE/mirror.env" ]]; then
  set -a
  source "$BASE/mirror.env"
  set +a
fi
: "${APT_GPG_KEY_ID:?APT_GPG_KEY_ID is required}"
export APT_GPG_KEY_ID

force=false
case "${1:-}" in
  "") ;;
  --force) force=true ;;
  *) echo "usage: $0 [--force]" >&2; exit 2 ;;
esac

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

install -d -m 0755 "$RELEASES_DIR"

rm -f "$NEXT_STATE"
trap 'rm -f "$NEXT_STATE"' EXIT
python3 "$BASE/sync.py" --release-state > "$NEXT_STATE"

if [[ "$force" != true && -s "$STATE_FILE" ]] && cmp -s "$STATE_FILE" "$NEXT_STATE"; then
  rm -f "$NEXT_STATE"
  printf '%s No Release changes; repository rebuild skipped.\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  exit 0
fi

if [[ "$force" == true ]]; then
  printf '%s Forced repository rebuild.\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
elif [[ ! -s "$STATE_FILE" ]]; then
  printf '%s No previous Release state; repository rebuild required.\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
else
  printf '%s Release change detected; repository rebuild required.\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
fi

release_id=$(date -u +'%Y%m%dT%H%M%SZ')
release_dir="$RELEASES_DIR/release-$release_id"
mkdir "$release_dir"
cleanup() {
  [[ -d "${release_dir:-}" ]] && rm -rf "$release_dir"
  rm -f "$NEXT_STATE"
}
trap cleanup EXIT

python3 "$BASE/sync.py" --state-file "$NEXT_STATE" --previous-state "$STATE_FILE" "$release_dir"
chmod -R a+rX "$release_dir"

new_link="$BASE/.www.new"
rm -f "$new_link"
ln -s "releases/$(basename "$release_dir")" "$new_link"
mv -Tf "$new_link" "$LIVE_LINK"

release_dir=""
trap - EXIT

current=$(readlink -f "$LIVE_LINK")
find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d ! -path "$current" -exec rm -rf -- {} +

mv -f "$NEXT_STATE" "$STATE_FILE"
printf '%s Repository update complete.\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
