#!/bin/sh
# One Telegraf for N PostgreSQL instances.
# For every id of PG_INSTANCES (e.g. DB1,DB2) the input templates of INPUTS_DIR are rendered into RENDER_DIR
# as <id>__<file>.conf, ${PG_DSN} / ${PG_APP_DSN} / ${PG_INSTANCE} / ${PG_ENV} become
# ${<ID>_DSN} / ${<ID>_APP_DSN} / ${<ID>_INSTANCE} / ${<ID>_ENV}.
# <ID>_ENV (the `env` tag) is optional and defaults to PG_ENV.
# Only variable names are rewritten: values (passwords) are expanded by Telegraf itself when it loads the config.
# Static configs of STATIC_DIR (outputs) are copied as is.
#
# Usage: entrypoint.sh [--render-only | --test] [extra telegraf args]
#   --render-only (or RENDER_ONLY=1)  render and print the file list, do not start Telegraf
#   --test                            render and run `telegraf --test` (every input is gathered once)
set -eu

TELEGRAF_CONF=${TELEGRAF_CONF:-/etc/telegraf/telegraf.conf}
INPUTS_DIR=${INPUTS_DIR:-/etc/telegraf/inputs.d}
STATIC_DIR=${STATIC_DIR:-/etc/telegraf/telegraf.d}
RENDER_DIR=${RENDER_DIR:-/etc/telegraf/rendered.d}
RENDER_ONLY=${RENDER_ONLY:-0}
TEST=0

case "${1:-}" in
  --render-only) RENDER_ONLY=1; shift ;;
  --test) TEST=1; shift ;;
esac

die() {
  echo "entrypoint: $*" >&2
  exit 1
}

[ -n "${PG_INSTANCES:-}" ] || die "PG_INSTANCES is not set (comma separated ids, e.g. PG_INSTANCES=DB1,DB2)"
[ -d "$INPUTS_DIR" ] || die "INPUTS_DIR $INPUTS_DIR does not exist"
mkdir -p "$RENDER_DIR"
rm -f "$RENDER_DIR"/*.conf

if [ -d "$STATIC_DIR" ]; then
  for f in "$STATIC_DIR"/*.conf; do
    [ -f "$f" ] || continue
    cp "$f" "$RENDER_DIR/"
  done
fi

ids=$(echo "$PG_INSTANCES" | tr ',' ' ')
seen=" "
for ID in $ids; do
  case "$ID" in
    [A-Za-z_]*) ;;
    *) die "invalid id '$ID' in PG_INSTANCES: must start with a letter or _" ;;
  esac
  case "$ID" in
    *[!A-Za-z0-9_]*) die "invalid id '$ID' in PG_INSTANCES: only letters, digits and _ are allowed" ;;
  esac
  case "$seen" in
    *" $ID "*) die "duplicate id '$ID' in PG_INSTANCES" ;;
  esac
  seen="$seen$ID "

  for v in INSTANCE DSN APP_DSN; do
    eval "val=\${${ID}_$v:-}"
    [ -n "$val" ] || die "${ID}_$v is not set (required for '$ID' of PG_INSTANCES)"
  done
  eval "val=\${${ID}_ENV:-\${PG_ENV:-}}"
  [ -n "$val" ] || die "${ID}_ENV is not set and there is no default PG_ENV (the env tag of '$ID')"
  eval "${ID}_ENV=\$val"
  export "${ID}_ENV"

  lid=$(echo "$ID" | tr 'A-Z' 'a-z')
  for f in "$INPUTS_DIR"/*.conf; do
    [ -f "$f" ] || continue
    sed -e "s/\${PG_DSN}/\${${ID}_DSN}/g" \
        -e "s/\${PG_APP_DSN}/\${${ID}_APP_DSN}/g" \
        -e "s/\${PG_INSTANCE}/\${${ID}_INSTANCE}/g" \
        -e "s/\${PG_ENV}/\${${ID}_ENV}/g" \
        "$f" > "$RENDER_DIR/${lid}__$(basename "$f")"
  done
  eval "echo \"entrypoint: rendered $ID as \${${ID}_INSTANCE} (env \${${ID}_ENV})\""
done

if [ "$RENDER_ONLY" = "1" ]; then
  ls -1 "$RENDER_DIR"
  exit 0
fi

if [ "$TEST" = "1" ]; then
  exec telegraf --config "$TELEGRAF_CONF" --config-directory "$RENDER_DIR" --test "$@"
fi
exec telegraf --config "$TELEGRAF_CONF" --config-directory "$RENDER_DIR" "$@"
