#!/usr/bin/env bash
# waqt-timer release script
#
# One command: verify, build the .deb, tag, and publish a GitHub release titled
# "Waqt Timer vX.Y.Z" whose notes are the matching section of CHANGELOG.md.
#
#   ./release.sh              build + commit-ready tree check + publish
#   ./release.sh --commit     commit everything as "updated vX.Y.Z" first
#   ./release.sh --dry-run    show exactly what would happen, publish nothing
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

CONTROL="pkg/DEBIAN/control"
CHANGELOG="CHANGELOG.md"
TITLE_PREFIX="Waqt Timer"
NOTES_FILE="$(mktemp)"
trap 'rm -f "$NOTES_FILE"' EXIT

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
say() { printf '==> %s\n' "$*"; }

usage() {
    cat <<EOF
Usage: ./release.sh [options]

Reads the version from $CONTROL, builds waqt-timer_<version>_all.deb,
pushes the branch, then creates the GitHub release with:
  tag    : v<version>
  title  : $TITLE_PREFIX v<version>
  notes  : the "## [<version>]" section of $CHANGELOG
  asset  : waqt-timer_<version>_all.deb

Options:
  --no-build      Reuse the .deb already in the repo root instead of rebuilding
  --commit        git add -A && git commit -m "updated v<version>" before releasing
  --draft         Publish the release as a draft
  --allow-dirty   Release even if the working tree has uncommitted changes
  --dry-run       Print the plan and the release notes, then exit
  -h, --help      Show this help
EOF
}

NO_BUILD=0; COMMIT=0; DRAFT=0; ALLOW_DIRTY=0; DRY_RUN=0
while [ $# -gt 0 ]; do
    case "$1" in
        --no-build)     NO_BUILD=1 ;;
        --commit)       COMMIT=1 ;;
        --draft)        DRAFT=1 ;;
        --allow-dirty)  ALLOW_DIRTY=1 ;;
        --dry-run)      DRY_RUN=1 ;;
        -h|--help)      usage; exit 0 ;;
        *)              usage >&2; die "unknown option: $1" ;;
    esac
    shift
done

# ---------------------------------------------------------------- preflight --
command -v git  >/dev/null || die "git not found"
command -v gh   >/dev/null || die "GitHub CLI (gh) not found - install it first"
command -v dpkg-deb >/dev/null || die "dpkg-deb not found"
gh auth status >/dev/null 2>&1 || die "gh is not logged in - run: gh auth login"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
[ -f "$CONTROL" ]  || die "missing $CONTROL"
[ -f "$CHANGELOG" ] || die "missing $CHANGELOG"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" != "HEAD" ] || die "detached HEAD - check out a branch first"

# ------------------------------------------------------------------ version --
VERSION="$(sed -n 's/^Version:[[:space:]]*//p' "$CONTROL" | head -n1)"
[ -n "$VERSION" ] || die "could not read Version: from $CONTROL"
TAG="v${VERSION}"
DEB="waqt-timer_${VERSION}_all.deb"
TITLE="${TITLE_PREFIX} ${TAG}"

# ------------------------------------------------------------ release notes --
# index() is a literal search, so dots in the version are not regex metachars.
awk -v ver="$VERSION" '
    index($0, "## [" ver "]") == 1 { inside = 1 }
    inside && index($0, "## [") == 1 && index($0, "## [" ver "]") != 1 { exit }
    inside { print }
' "$CHANGELOG" > "$NOTES_FILE"
[ -s "$NOTES_FILE" ] || die "no \"## [$VERSION]\" section found in $CHANGELOG - add the changelog entry first"
NOTES_LINES="$(wc -l < "$NOTES_FILE")"

# ------------------------------------------------------------- guard rails ---
if [ -n "$(git status --porcelain)" ]; then
    if [ "$COMMIT" = 1 ]; then
        say "committing working tree as \"$TAG\""
        git add -A
        if ! git diff --cached --quiet; then
            git commit -m "updated ${TAG}"
        else
            say "nothing staged to commit"
        fi
    elif [ "$ALLOW_DIRTY" = 0 ]; then
        git status --short >&2
        die "working tree is dirty - commit it (./release.sh --commit) or pass --allow-dirty"
    else
        say "WARNING: releasing from a dirty working tree (--allow-dirty)"
    fi
fi

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
    die "tag ${TAG} already exists locally - bump the version in $CONTROL first"
fi
if gh release view "$TAG" >/dev/null 2>&1; then
    die "release ${TAG} already exists on GitHub - bump the version in $CONTROL first"
fi

# ------------------------------------------------------------------- build ---
if [ "$NO_BUILD" = 0 ]; then
    command -v python3 >/dev/null || die "python3 not found"
    say "syntax check"
    python3 -m py_compile pkg/opt/waqt-timer/*.py
    rm -rf pkg/opt/waqt-timer/__pycache__
    say "setting permissions"
    chmod 755 pkg/DEBIAN/postinst pkg/opt/waqt-timer/waqt_timer.py pkg/usr/bin/waqt-timer
    say "building ${DEB}"
    dpkg-deb --build pkg "$DEB"
else
    say "skipping build (--no-build)"
fi

[ -f "$DEB" ] || die "$DEB not found - drop --no-build or build it first"
PKG_VER="$(dpkg-deb -f "$DEB" Version)"
[ "$PKG_VER" = "$VERSION" ] || die "$DEB carries Version ${PKG_VER}, expected ${VERSION} - rebuild it"
if dpkg-deb -c "$DEB" | grep -q '__pycache__'; then
    die "$DEB contains __pycache__ - rm -rf pkg/opt/waqt-timer/__pycache__ and rebuild"
fi
say "package ok: $DEB ($(du -h "$DEB" | cut -f1)), Version ${PKG_VER}"

# ----------------------------------------------------------------- dry run ---
if [ "$DRY_RUN" = 1 ]; then
    cat <<EOF

DRY RUN - nothing was pushed or published.

  branch    : ${BRANCH}
  tag       : ${TAG}
  title     : ${TITLE}
  asset     : ${DEB} ($(du -h "$DEB" | cut -f1))
  notes     : ${NOTES_LINES} lines from ${CHANGELOG}
  draft     : $([ "$DRAFT" = 1 ] && echo yes || echo no)

----- release notes -----
EOF
    cat "$NOTES_FILE"
    echo "-------------------------"
    exit 0
fi

# ----------------------------------------------------------------- publish ---
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
