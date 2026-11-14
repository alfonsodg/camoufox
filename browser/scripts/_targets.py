"""The (target, arch) pairs Camoufox builds, and what each one maps to.

One table, so the build scripts, multibuild.py and the PGO pin cannot disagree
about what is supported. The release matrix in .github/workflows/release.yml
excludes the same unsupported pairs by hand.
"""

# (target, arch) -> (Mozilla target triple, Mozilla PGO profile platform).
# The profile platforms are those `use-pgo` assigns in Firefox 159's
# taskcluster/kinds/build: Linux arm64 is built with the x86_64 Linux profile.
SUPPORTED = {
    ('linux', 'x86_64'): ('x86_64-pc-linux-gnu', 'linux64'),
    ('linux', 'arm64'): ('aarch64-unknown-linux-gnu', 'linux64'),
    ('windows', 'x86_64'): ('x86_64-pc-windows-msvc', 'win64'),
    ('windows', 'i686'): ('i686-pc-windows-msvc', 'win32'),
    ('macos', 'x86_64'): ('x86_64-apple-darwin', 'macosx64'),
    ('macos', 'arm64'): ('aarch64-apple-darwin', 'macosx64-aarch64'),
}
TARGETS = sorted({target for target, _ in SUPPORTED})
ARCHS = sorted({arch for _, arch in SUPPORTED})
PROFILE_PLATFORMS = sorted({profile for _, profile in SUPPORTED.values()})


def check_supported(target, arch):
    """Raise ValueError naming the pair and the supported ones."""
    if (target, arch) not in SUPPORTED:
        pairs = ', '.join(f'{t},{a}' for t, a in SUPPORTED)
        raise ValueError(f'Unsupported build target {target},{arch}; supported: {pairs}')
