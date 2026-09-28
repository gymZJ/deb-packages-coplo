#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import lzma
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


USER_AGENT = "coplo-packages-server/1.0"
CACHE_ROOT = Path(__file__).with_name("cache") / "github-assets"
ARCHES = ("amd64", "arm64")
COMPONENT = "main"

PACKAGES_FILE = Path(__file__).with_name("packages.toml")


def load_configuration() -> tuple[list[dict], list[dict]]:
    data = tomllib.loads(PACKAGES_FILE.read_text())

    suites = []
    seen_suite_names = set()
    default_suites = []
    for item in data.get("suite", []):
        suite = dict(item)
        name = str(suite.get("name", "")).strip()
        family = str(suite.get("family", "")).strip().lower()
        release_tokens = tuple(
            str(token).strip().lower()
            for token in suite.get("release_tokens", ())
            if str(token).strip()
        )
        if not name or not family or not release_tokens:
            raise RuntimeError(f"invalid suite entry in {PACKAGES_FILE}: {suite!r}")
        if name in seen_suite_names:
            raise RuntimeError(f"duplicate suite {name!r} in {PACKAGES_FILE}")
        seen_suite_names.add(name)
        suite["name"] = name
        suite["family"] = family
        suite["release_tokens"] = release_tokens
        suite["label"] = str(suite.get("label") or name)
        suite["default"] = bool(suite.get("default", False))
        if suite["default"]:
            default_suites.append(name)
        suites.append(suite)

    if not suites:
        raise RuntimeError(f"at least one [[suite]] is required in {PACKAGES_FILE}")
    if len(default_suites) > 1:
        raise RuntimeError(
            f"only one suite may be default in {PACKAGES_FILE}: {', '.join(default_suites)}"
        )

    sources = []
    for item in data.get("package", []):
        if not item.get("enabled", True):
            continue
        source = dict(item)
        patterns = tuple(source.get("patterns", ()))
        source["patterns"] = patterns
        source["distribution_aware"] = bool(source.get("distribution_aware", False))
        if not source.get("repository") or not source["patterns"]:
            raise RuntimeError(f"invalid package entry in {PACKAGES_FILE}: {source!r}")
        sources.append(source)
    return suites, sources


def load_sources() -> list[dict]:
    return load_configuration()[1]


def package_config_sha256() -> str:
    return hashlib.sha256(PACKAGES_FILE.read_bytes()).hexdigest()


def request_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    attempts = 5
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code in {401, 403, 404, 422}:
                raise
            if attempt == attempts:
                raise
            delay = attempt * 3
            print(
                f"GitHub API retry {attempt}/{attempts - 1} for {url}: {exc}; retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)


def download(url: str, path: Path, expected_size: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    attempts = 5
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=300) as response, part.open("wb") as output:
                shutil.copyfileobj(response, output, 1024 * 1024)
            if expected_size is not None and part.stat().st_size != int(expected_size):
                raise RuntimeError(
                    f"downloaded size mismatch for {url}: expected {expected_size}, got {part.stat().st_size}"
                )
            os.replace(part, path)
            return
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError) as exc:
            part.unlink(missing_ok=True)
            if attempt == attempts:
                raise
            delay = attempt * 5
            print(
                f"download retry {attempt}/{attempts - 1} for {url}: {exc}; retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)


def deb_field(path: Path, field: str) -> str:
    return subprocess.check_output(["dpkg-deb", "-f", str(path), field], text=True).strip()


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_stanza(path: Path, relative: str) -> str:
    fields = subprocess.check_output(["dpkg-deb", "-f", str(path)], text=True).rstrip()
    return (
        f"{fields}\n"
        f"Filename: {relative}\n"
        f"Size: {path.stat().st_size}\n"
        f"MD5sum: {file_hash(path, 'md5')}\n"
        f"SHA1: {file_hash(path, 'sha1')}\n"
        f"SHA256: {file_hash(path, 'sha256')}\n\n"
    )


def write_packages(directory: Path, entries: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    raw = "".join(entries).encode()
    (directory / "Packages").write_bytes(raw)
    with (directory / "Packages.gz").open("wb") as raw_file:
        with gzip.GzipFile(fileobj=raw_file, mode="wb", compresslevel=9, mtime=0) as archive:
            archive.write(raw)
    with lzma.open(directory / "Packages.xz", "wb", preset=9) as archive:
        archive.write(raw)


def write_release(suite_dir: Path, suite: str) -> Path:
    now = datetime.now(timezone.utc)
    files = sorted(
        path
        for path in suite_dir.rglob("*")
        if path.is_file() and path.name not in {"Release", "InRelease", "Release.gpg"}
    )
    lines = [
        "Origin: Coplo Packages",
        "Label: Coplo Packages",
        f"Suite: {suite}",
        f"Codename: {suite}",
        f"Date: {now.strftime('%a, %d %b %Y %H:%M:%S +0000')}",
        f"Valid-Until: {(now + timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S +0000')}",
        f"Architectures: {' '.join(ARCHES)}",
        f"Components: {COMPONENT}",
        "Description: Coplo Debian package repository",
    ]
    for label, algorithm in (
        ("MD5Sum", "md5"),
        ("SHA1", "sha1"),
        ("SHA256", "sha256"),
        ("SHA512", "sha512"),
    ):
        lines.append(label + ":")
        for path in files:
            relative = path.relative_to(suite_dir).as_posix()
            lines.append(f" {file_hash(path, algorithm)} {path.stat().st_size:16d} {relative}")
    release = suite_dir / "Release"
    release.write_text("\n".join(lines) + "\n")
    return release


def sign(release: Path, key: str) -> None:
    subprocess.run(
        [
            "gpg", "--batch", "--yes", "--local-user", key,
            "--detach-sign", "--armor",
            "--output", str(release.with_name("Release.gpg")), str(release),
        ],
        check=True,
    )
    subprocess.run(
        [
            "gpg", "--batch", "--yes", "--local-user", key,
            "--clearsign",
            "--output", str(release.with_name("InRelease")), str(release),
        ],
        check=True,
    )


def matching_assets(release: dict, patterns: tuple[str, ...]) -> list[dict]:
    return [
        asset
        for asset in release.get("assets", [])
        if any(fnmatch.fnmatch(asset.get("name", ""), pattern) for pattern in patterns)
    ]


def asset_matches_distribution(asset_name: str, family: str, token: str) -> bool:
    # Upstreams use both separated distro markers (ubuntu-24.04,
    # debian-trixie) and compact markers (ubuntu24.04, debiantrixie).
    # Match the family and release token as one marker so similarly named
    # assets cannot be assigned to an unrelated suite.
    return re.search(
        rf"(?<![a-z0-9]){re.escape(family.lower())}[-_.]?{re.escape(token.lower())}(?![a-z0-9])",
        asset_name.lower(),
    ) is not None


def matching_suites(source: dict, asset_name: str, suites: list[dict]) -> tuple[str, ...]:
    if not source.get("distribution_aware", False):
        return tuple(suite["name"] for suite in suites)

    return tuple(
        suite["name"]
        for suite in suites
        if any(
            asset_matches_distribution(asset_name, suite["family"], token)
            for token in suite["release_tokens"]
        )
    )


def normalized_asset(asset: dict) -> dict:
    return {
        "id": asset.get("id"),
        "name": asset.get("name"),
        "size": asset.get("size"),
        "updated_at": asset.get("updated_at"),
        "browser_download_url": asset.get("browser_download_url"),
    }


def source_release_state(source: dict) -> dict:
    try:
        release = request_json(
            f"https://api.github.com/repos/{source['repository']}/releases/latest"
        )
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {
                "repository": source["repository"],
                "release": None,
                "assets": [],
            }
        raise

    selected = matching_assets(release, source["patterns"])

    assets_by_id = {
        asset.get("id"): normalized_asset(asset)
        for asset in selected
        if asset.get("id") is not None
    }
    return {
        "repository": source["repository"],
        "release": {
            "id": release.get("id"),
            "tag_name": release.get("tag_name"),
            "published_at": release.get("published_at"),
            "created_at": release.get("created_at"),
        },
        "assets": sorted(
            assets_by_id.values(),
            key=lambda asset: (str(asset.get("name", "")), int(asset.get("id") or 0)),
        ),
    }


def collect_release_state() -> dict:
    sources = load_sources()
    return {
        "schema_version": 2,
        "config_sha256": package_config_sha256(),
        "sources": [source_release_state(source) for source in sources],
    }


def load_release_state(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get("schema_version") not in {1, 2} or not isinstance(data.get("sources"), list):
        raise RuntimeError(f"unsupported release state file: {path}")
    return data


def state_by_repository(state: dict) -> dict[str, dict]:
    return {item["repository"]: item for item in state["sources"]}


def prune_asset_cache(release_state: dict) -> None:
    keep = {
        source["repository"].replace("/", "_"): {
            asset["name"]
            for asset in source.get("assets", [])
            if asset.get("name")
        }
        for source in release_state["sources"]
    }

    if not CACHE_ROOT.exists():
        return

    for cache_dir in CACHE_ROOT.iterdir():
        if not cache_dir.is_dir():
            continue
        keep_names = keep.get(cache_dir.name, set())
        for path in cache_dir.iterdir():
            if path.is_file() and path.name not in keep_names:
                path.unlink()
        if not any(cache_dir.iterdir()):
            cache_dir.rmdir()


def build_repository(output: Path, release_state: dict, previous_state: dict | None = None) -> int:
    key = os.environ.get("APT_GPG_KEY_ID", "").strip()
    if not key:
        raise RuntimeError("APT_GPG_KEY_ID is required")

    releases = state_by_repository(release_state)
    previous_releases = state_by_repository(previous_state) if previous_state else {}
    suites, sources = load_configuration()
    suite_names = tuple(suite["name"] for suite in suites)
    live_root = output.parent.parent / "www"
    try:
        current_root = live_root.resolve(strict=True)
    except FileNotFoundError:
        current_root = None

    with tempfile.TemporaryDirectory(prefix="coplo-server-sync-") as temp_name:
        temp = Path(temp_name)
        stage = temp / "repository"
        indexes = {
            suite: {arch: [] for arch in ARCHES}
            for suite in suite_names
        }
        catalog_by_name: dict[str, dict] = {}

        for source in sources:
            source_state = releases.get(source["repository"])
            if not source_state or source_state.get("release") is None:
                print(f"skip {source['repository']}: no release", file=sys.stderr)
                continue

            release = source_state["release"]

            assets = [
                asset
                for asset in source_state.get("assets", [])
                if any(
                    fnmatch.fnmatch(asset.get("name", ""), pattern)
                    for pattern in source["patterns"]
                )
            ]
            if not assets:
                print(f"skip {source['repository']}: no matching .deb assets", file=sys.stderr)
                continue

            previous_source = previous_releases.get(source["repository"], {})
            previous_asset_ids = {
                item.get("id")
                for item in previous_source.get("assets", [])
                if item.get("id") is not None
            }

            for asset in assets:
                asset_suites = matching_suites(source, asset["name"], suites)
                if not asset_suites:
                    print(
                        f"skip {source['repository']}: {asset['name']} matches no configured suite",
                        file=sys.stderr,
                    )
                    continue
                incoming = temp / "downloads" / source["repository"].replace("/", "_") / asset["name"]
                incoming.parent.mkdir(parents=True, exist_ok=True)
                reused = False
                cache_dir = CACHE_ROOT / source["repository"].replace("/", "_")
                cache_path = cache_dir / asset["name"]
                expected_size = asset.get("size")

                if cache_path.exists():
                    if expected_size is None or cache_path.stat().st_size == int(expected_size):
                        try:
                            os.link(cache_path, incoming)
                        except OSError:
                            shutil.copy2(cache_path, incoming)
                        print(f"cache {source['repository']}: {asset['name']}")
                        reused = True
                    else:
                        cache_path.unlink(missing_ok=True)

                if not reused and current_root is not None and asset.get("id") in previous_asset_ids:
                    candidates = list((current_root / "pool").rglob(asset["name"]))
                    for candidate in candidates:
                        if expected_size is not None and candidate.stat().st_size != int(expected_size):
                            continue
                        try:
                            os.link(candidate, incoming)
                        except OSError:
                            shutil.copy2(candidate, incoming)
                        print(f"reuse {source['repository']}: {asset['name']}")
                        reused = True
                        break
                if not reused:
                    print(f"download {source['repository']}: {asset['name']}")
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    download(asset["browser_download_url"], cache_path, expected_size)
                    try:
                        os.link(cache_path, incoming)
                    except OSError:
                        shutil.copy2(cache_path, incoming)
                architecture = deb_field(incoming, "Architecture")
                if architecture not in (*ARCHES, "all"):
                    continue

                package = deb_field(incoming, "Package")
                version = deb_field(incoming, "Version")
                first = package[:1].lower() or "_"
                relative = f"pool/{COMPONENT}/{first}/{package}/{asset['name']}"
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(incoming, target)

                entry = package_stanza(target, relative)
                for target_arch in ARCHES if architecture == "all" else (architecture,):
                    for suite in asset_suites:
                        indexes[suite][target_arch].append(entry)

                item = catalog_by_name.setdefault(
                    package,
                    {
                        "name": package,
                        "version": version,
                        "repository": source["repository"],
                        "repository_url": f"https://github.com/{source['repository']}",
                        "upstream_repository": source["upstream_repository"],
                        "upstream_url": f"https://github.com/{source['upstream_repository']}",
                        "source_type": source["source_type"],
                        "release_tag": release.get("tag_name"),
                        "updated_at": release.get("published_at") or release.get("created_at"),
                        "homepage": source.get("homepage"),
                        "license": source.get("license") or "—",
                        "suites": [],
                        "artifacts": [],
                    },
                )
                for suite in asset_suites:
                    if suite not in item["suites"]:
                        item["suites"].append(suite)
                item["artifacts"].append(
                    {
                        "package": package,
                        "version": version,
                        "filename": asset["name"],
                        "architecture": architecture,
                        "suites": list(asset_suites),
                        "size": target.stat().st_size,
                        "url": "/" + relative,
                        "sha256": file_hash(target, "sha256"),
                    }
                )

        for suite in suite_names:
            suite_dir = stage / "dists" / suite
            for architecture in ARCHES:
                binary = suite_dir / COMPONENT / f"binary-{architecture}"
                write_packages(binary, indexes[suite][architecture])
                (binary / "Release").write_text(
                    f"Archive: {suite}\n"
                    f"Component: {COMPONENT}\n"
                    f"Architecture: {architecture}\n"
                )
            sign(write_release(suite_dir, suite), key)

        public_key = stage / "coplo-archive-keyring.gpg"
        with public_key.open("wb") as output_key:
            subprocess.run(["gpg", "--batch", "--export", key], stdout=output_key, check=True)

        catalog = {
            "schema_version": 4,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "component": COMPONENT,
            "suites": [
                {
                    "name": suite["name"],
                    "family": suite["family"],
                    "release_tokens": list(suite["release_tokens"]),
                    "label": suite["label"],
                    "default": suite["default"],
                }
                for suite in suites
            ],
            "packages": sorted(catalog_by_name.values(), key=lambda item: item["name"]),
        }
        (stage / "catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(stage, output)

    prune_asset_cache(release_state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", type=Path)
    parser.add_argument(
        "--release-state",
        action="store_true",
        help="print the latest source Release state without downloading package assets",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="build from a previously captured Release state",
    )
    parser.add_argument(
        "--previous-state",
        type=Path,
        help="reuse unchanged package assets from the current repository when IDs match this previous state",
    )
    args = parser.parse_args()

    if args.release_state:
        if args.output_dir or args.state_file or args.previous_state:
            parser.error("--release-state cannot be combined with an output directory, --state-file, or --previous-state")
        print(json.dumps(collect_release_state(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.output_dir is None:
        parser.error("OUTPUT_DIR is required unless --release-state is used")

    release_state = (
        load_release_state(args.state_file)
        if args.state_file is not None
        else collect_release_state()
    )
    previous_state = None
    if args.previous_state is not None and args.previous_state.is_file():
        previous_state = load_release_state(args.previous_state)
    return build_repository(args.output_dir.resolve(), release_state, previous_state)


if __name__ == "__main__":
    raise SystemExit(main())
