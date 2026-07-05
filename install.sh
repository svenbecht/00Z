#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="svenbecht"
REPO_NAME="00Z"
DEFAULT_REF="main"
DEFAULT_REF_TYPE="branch"
DEFAULT_FORMAT="tar"

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

usage() {
  cat <<'EOF'
00Z installer

Safely downloads and extracts the 00Z repository.
This script does not use sudo, does not install dependencies,
and does not execute project code automatically.

Usage:
  bash install.sh [options]

Options:
  --dir <path>        Target directory (default: 00Z)
  --ref <name>        Branch or tag name to download (default: main)
  --ref-type <type>   branch | tag (default: branch)
  --format <type>     tar | zip (default: tar)
  -h, --help          Show this help

Examples:
  bash install.sh
  bash install.sh --dir ./00Z-local
  bash install.sh --ref v0.1.0 --ref-type tag
EOF
}

target_dir="$REPO_NAME"
ref="$DEFAULT_REF"
ref_type="$DEFAULT_REF_TYPE"
format="$DEFAULT_FORMAT"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dir)
      [ "$#" -ge 2 ] || die "Missing value for --dir"
      target_dir="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || die "Missing value for --ref"
      ref="$2"
      shift 2
      ;;
    --ref-type)
      [ "$#" -ge 2 ] || die "Missing value for --ref-type"
      ref_type="$2"
      shift 2
      ;;
    --format)
      [ "$#" -ge 2 ] || die "Missing value for --format"
      format="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

case "$ref_type" in
  branch|tag) ;;
  *) die "Invalid --ref-type: $ref_type (expected: branch or tag)" ;;
esac

case "$format" in
  tar|zip) ;;
  *) die "Invalid --format: $format (expected: tar or zip)" ;;
esac

case "$ref" in
  ""|*[!A-Za-z0-9._-]*|*".."*)
    die "Unsafe or invalid --ref value: $ref"
    ;;
esac

[ ! -e "$target_dir" ] || die "Target path already exists: $target_dir"

need_cmd curl
need_cmd mktemp
need_cmd mv

if [ "$format" = "tar" ]; then
  need_cmd tar
  archive_ext="tar.gz"
else
  need_cmd unzip
  archive_ext="zip"
fi

case "$ref_type" in
  branch) archive_url="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${ref}.${archive_ext}" ;;
  tag) archive_url="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${ref}.${archive_ext}" ;;
esac

tmp_dir="$(mktemp -d)"
archive_path="$tmp_dir/archive.$archive_ext"
extract_dir="$tmp_dir/extract"
mkdir -p "$extract_dir"

cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

printf 'Downloading %s from %s\n' "$REPO_NAME" "$archive_url"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$archive_url" -o "$archive_path"

printf 'Extracting archive\n'
if [ "$format" = "tar" ]; then
  tar -xzf "$archive_path" -C "$extract_dir"
else
  unzip -q "$archive_path" -d "$extract_dir"
fi

shopt -s nullglob
extracted_entries=("$extract_dir"/*)
shopt -u nullglob

[ "${#extracted_entries[@]}" -eq 1 ] || die "Archive did not extract into exactly one top-level entry"
[ -d "${extracted_entries[0]}" ] || die "Extracted top-level entry is not a directory"
extracted_root="${extracted_entries[0]}"

mkdir -p "$(dirname "$target_dir")"
mv "$extracted_root" "$target_dir"

printf '\nInstalled into: %s\n' "$target_dir"
printf 'For safety, no project code was executed automatically.\n\n'
printf 'Next steps:\n'
printf '  cd %s\n' "$target_dir"
printf '  PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only\n'
