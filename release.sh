#!/usr/bin/env bash
# waqt-timer release script
#
# One command: verify, bump the version if asked, build the .deb if it is not
# ready, tag, and publish a GitHub release titled "Waqt Timer vX.Y.Z" whose
# notes are the matching section of CHANGELOG.md.
#
#   ./release.sh 1.5.4 --commit    pick the version, bump the strings,
#                                  build waqt-timer_1.5.4_all.deb, publish
#   ./release.sh --dry-run         show exactly what would happen
#   ./release.sh                   release whatever Version: is in the control file
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

CONTROL="pkg/DEBIAN/control"
CHANGELOG="CHANGELOG.md"
PKG_CHANGELOG="pkg/usr/share/doc/waqt-timer/changelog"
APP_PY="pkg/opt/waqt-timer/waqt_timer.py"
TITLE_PREFIX="Waqt Timer"
NOTES_FILE="$(mktemp)"
trap 'rm -f "$NOTES_FILE"' EXIT

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
say() { printf '==> %s\n' "$*"; }

usage() {
    cat <<EOF
Usage: ./release.sh [version] [options]

Reads the version from $CONTROL, or takes the one you pass:
  ./release.sh 1.5.4 --commit
  ./release.sh --version 1.5.4 --commit

If the version you pass is ahead of $CONTROL, the version strings are
updated first (control file, app docstring + User-Agent, READMEs, docs page)
and the changelog is synced into the package. Then:
  tag    : v<version>
  title  : $TITLE_PREFIX v<version>
  notes  : the "## [<version>]" section of $CHANGELOG
  asset  : waqt-timer_<version>_all.deb

The .deb is built when it is missing, and reused when it is already there.

Options:
  --version X.Y.Z  Release this version (a leading v is accepted; also positional)
  --rebuild        Build the .deb even if one already exists for this version
  --no-build       Reuse the existing .deb, fail if it is missing
  --commit         git add -A && git commit -m "updated v<version>" before releasing
  --draft          Publish the release as a draft
  --allow-dirty    Release even if the working tree has uncommitted changes
  --dry-run        Print the plan and the release notes, change nothing
  -h, --help       Show this help
EOF
}

NO_BUILD=0; REBUILD=0; COMMIT=0; DRAFT=0; ALLOW_DIRTY=0; DRY_RUN=0
VERSION_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --version)      shift; [ $# -gt 0 ] || die "--version needs a value, e.g. --version 1.5.4"; VERSION_ARG="$1" ;;
        --version=*)    VERSION_ARG="${1#--version=}" ;;
        --rebuild)      REBUILD=1 ;;
        --no-build)     NO_BUILD=1 ;;
        --commit)       COMMIT=1 ;;
        --draft)        DRAFT=1 ;;
        --allow-dirty)  ALLOW_DIRTY=1 ;;
        --dry-run)      DRY_RUN=1 ;;
        -h|--help)      usage; exit 0 ;;
        -*)             usage >&2; die "unknown option: $1" ;;
        *)              if printf '%s' "$1" | grep -Eq '^v?[0-9]+\.[0-9]+\.[0-9]+$'; then
                            VERSION_ARG="$1"
                        else
                            usage >&2; die "unexpected argument: $1"
                        fi ;;
    esac
    shift
done
if [ "$NO_BUILD" = 1 ] && [ "$REBUILD" = 1 ]; then
    die "--no-build and --rebuild cannot be combined"
fi

# ---------------------------------------------------------------- preflight --
command -v git      >/dev/null || die "git not found"
command -v gh       >/dev/null || die "GitHub CLI (gh) not found - install it first"
command -v dpkg-deb >/dev/null || die "dpkg-deb not found"
gh auth status >/dev/null 2>&1 || die "gh is not logged in - run: gh auth login"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
[ -f "$CONTROL" ]   || die "missing $CONTROL"
[ -f "$CHANGELOG" ] || die "missing $CHANGELOG"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" != "HEAD" ] || die "detached HEAD - check out a branch first"

# ------------------------------------------------------------------ version --
CONTROL_VERSION="$(sed -n 's/^Version:[[:space:]]*//p' "$CONTROL" | head -n1)"
[ -n "$CONTROL_VERSION" ] || die "could not read Version: from $CONTROL"

VERSION="${VERSION_ARG:-$CONTROL_VERSION}"
VERSION="${VERSION#v}"
printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' \
    || die "version must look like 1.5.4, got '$VERSION'"

TAG="v${VERSION}"
DEB="waqt-timer_${VERSION}_all.deb"
TITLE="${TITLE_PREFIX} ${TAG}"

BUMP=0
if [ "$VERSION" != "$CONTROL_VERSION" ]; then
    BUMP=1
fi

# ------------------------------------------------------------ release notes --
# index() is a literal search, so dots in the version are not regex metachars.
awk -v ver="$VERSION" '
    index($0, "## [" ver "]") == 1 { inside = 1 }
    inside && index($0, "## [") == 1 && index($0, "## [" ver "]") != 1 { exit }
    inside { print }
' "$CHANGELOG" > "$NOTES_FILE"
[ -s "$NOTES_FILE" ] || die "no \"## [$VERSION]\" section found in $CHANGELOG - add the changelog entry first"

# ------------------------------------------------------------- guard rails ---
if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
    die "tag ${TAG} already exists locally - pick a newer version"
fi
if gh release view "$TAG" >/dev/null 2>&1; then
    die "release ${TAG} already exists on GitHub - pick a newer version"
fi

# --------------------------------------------------------------- bump files --
bump_files() {
    local old="$1" new="$2" esc
    esc="$(printf '%s' "$old" | sed 's/\./\\./g')"
    say "updating version ${old} -> ${new}"
    sed -i "s/^Version:[[:space:]]*${esc}[[:space:]]*\$/Version: ${new}/" "$CONTROL"
    sed -i -e "s/Waqt Timer v${esc}/Waqt Timer v${new}/" \
           -e "s|waqt-timer/${esc}\"|waqt-timer/${new}\"|" "$APP_PY"
    sed -i "s/${esc}/${new}/g" README.md pkg/usr/share/doc/waqt-timer/README.md docs/index.html
    grep -q "^Version: ${new}\$" "$CONTROL" || die "$CONTROL was not updated to ${new}"
    grep -q "UA = \"waqt-timer/${new}\"" "$APP_PY" || die "$APP_PY User-Agent was not updated to ${new}"
    say "updated: $CONTROL, $APP_PY, README.md, pkg/.../README.md, docs/index.html"
}

# ------------------------------------------------------------------- build ---
ensure_deb() {
    if [ "$NO_BUILD" = 1 ]; then
        [ -f "$DEB" ] || die "--no-build was given but ${DEB} does not exist"
        say "reusing existing ${DEB} (--no-build)"
    elif [ "$REBUILD" = 1 ] || [ ! -f "$DEB" ]; then
        command -v python3 >/dev/null || die "python3 not found"
        say "syntax check"
        python3 -m py_compile pkg/opt/waqt-timer/*.py
        rm -rf pkg/opt/waqt-timer/__pycache__
        say "setting permissions"
        chmod 755 pkg/DEBIAN/postinst pkg/opt/waqt-timer/waqt_timer.py pkg/usr/bin/waqt-timer
        say "building ${DEB}"
        dpkg-deb --build pkg "$DEB"
    else
        say "reusing existing ${DEB} (pass --rebuild to rebuild it)"
    fi

    [ -f "$DEB" ] || die "${DEB} was not produced"
    local pkg_ver
    pkg_ver="$(dpkg-deb -f "$DEB" Version)"
    [ "$pkg_ver" = "$VERSION" ] || die "${DEB} carries Version ${pkg_ver}, expected ${VERSION} - rerun with --rebuild"
    if dpkg-deb -c "$DEB" | grep -q '__pycache__'; then
        die "${DEB} contains __pycache__ - rm -rf pkg/opt/waqt-timer/__pycache__ and rerun with --rebuild"
    fi
    say "package ok: ${DEB} ($(du -h "$DEB" | cut -f1)), Version ${pkg_ver}"
}

plan() {
    cat <<EOF
  branch    : ${BRANCH}
  tag       : ${TAG}
  title     : ${TITLE}
  version   : ${CONTROL_VERSION} -> ${VERSION}
  asset     : ${DEB} $([ -f "$DEB" ] && echo "($(du -h "$DEB" | cut -f1), already built)" || echo "(will be built)")
  notes     : $(wc -l < "$NOTES_FILE") lines from ${CHANGELOG}
  draft     : $([ "$DRAFT" = 1 ] && echo yes || echo no)
EOF
    if [ "$BUMP" = 1 ]; then
        echo "  bump      : $CONTROL, $APP_PY, README.md, pkg/usr/share/doc/waqt-timer/README.md, docs/index.html"
        echo "  sync      : $PKG_CHANGELOG <- $CHANGELOG"
    fi
}

# ----------------------------------------------------------------- dry run ---
if [ "$DRY_RUN" = 1 ]; then
    if [ "$BUMP" = 1 ]; then
        say "DRY RUN - version strings are NOT written, so the .deb is not built"
        plan
    else
        ensure_deb
        say "DRY RUN - nothing was committed, pushed or published"
        plan
    fi
    printf '\n----- release notes -----\n'
    cat "$NOTES_FILE"
    printf '%s\n' '-------------------------'
    exit 0
fi

# ------------------------------------------------------------------ execute ---
if [ "$BUMP" = 1 ]; then
    bump_files "$CONTROL_VERSION" "$VERSION"
fi

# the package must ship the same changelog the release notes came from
mkdir -p "$(dirname "$PKG_CHANGELOG")"
cp -f "$CHANGELOG" "$PKG_CHANGELOG"

if [ -n "$(git status --porcelain)" ]; then
    if [ "$COMMIT" = 1 ]; then
        say "committing working tree as \"${TAG}\""
        git add -A
        if ! git diff --cached --quiet; then
            git commit -m "updated ${TAG}"
        else
            say "nothing staged to commit"
        fi
    elif [ "$ALLOW_DIRTY" = 1 ]; then
        say "WARNING: releasing from a dirty working tree (--allow-dirty)"
    elif [ "$BUMP" = 1 ]; then
        git status --short >&2
        die "the version bump changed the files above - rerun with --commit (or --allow-dirty)"
    else
        git status --short >&2
        die "working tree is dirty - commit it (./release.sh --commit) or pass --allow-dirty"
    fi
fi

ensure_deb

say "pushing ${BRANCH} to origin"
git push origin "HEAD:${BRANCH}"

GH_ARGS=("$TAG" "$DEB" --title "$TITLE" --notes-file "$NOTES_FILE")
if [ "$DRAFT" = 1 ]; then
    GH_ARGS+=(--draft)
fi

say "creating release ${TITLE}"
gh release create "${GH_ARGS[@]}"

URL="$(gh release view "$TAG" --json url -q .url)"
cat <<EOF

==> released ${TITLE}
    ${URL}
    asset: ${DEB}

Next: sudo apt install /tmp/${DEB}
EOF
