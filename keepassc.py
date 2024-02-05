#!/usr/bin/env python3
"""Command line, automatable, interface to keepass databases"""
#
# :dotsctl:
#   destdir: ~/bin/
#   dpkg:
#     - python3-pykeepass
#     - python3-yaml
# ...

import argparse
import yaml
import os
import sys

from pykeepass import PyKeePass


def config_load(filename):
    try:
        f = open(filename)
        config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {}

    return config


def config_cache_load(config, filename):
    """Override the static config with the cached session config"""
    try:
        f = open(filename)
        cache = yaml.safe_load(f)
    except FileNotFoundError:
        return

    for name, preset in cache.items():
        if name not in config["presets"]:
            print(f"Warn: Cached preset {name} not in config file")
            config["presets"][name] = preset
            continue

        for key, val in preset.items():
            config["presets"][name][key] = val


def config_addargs(config, args):
    """Override any loaded config with CLI args"""

    if args.preset is None:
        if "default" not in config:
            return
        args.preset = config["default"]

    if args.preset not in config["presets"]:
        config["presets"][args.preset] = {}

    if args.password is not None:
        config["presets"][args.preset]["pass"] = args.password

    if args.kdb is not None:
        config["presets"][args.preset]["kdb"] = args.kdb


def kdb_load(presetname, config):
    if presetname is None:
        print("No preset specified and no default configured")
        sys.exit(1)

    if presetname not in config["presets"]:
        # first, try again with a number
        presetname = int(presetname)
        if presetname not in config["presets"]:
            print(f"No preset config for {presetname}")
            sys.exit(1)

    preset = config["presets"][presetname]

    if "pass" not in preset:
        # todo:
        # if not sudo then readpass
        # else die
        print("cannot prompt")
        sys.exit(1)

    k = PyKeePass(preset["kdb"], preset["pass"])

    # TODO:
    # that kdb and pass combo worked, so ensure we write the cache
    # config_cachefile_save()
    # DumpFile($option->{cachefile}, $config->{presets});

    return k


def render_sudo(found):
    found_user = []

    for item in found:
        if item.username == os.environ.get("USER"):
            found_user.append(item)

    if len(found_user) > 1:
        print("Too many results found for sudo lookup")
        sys.exit(1)
    if len(found_user) == 0:
        sys.exit(1)

    for item in found_user:
        print(item.password)


def sgr(*modes):
    term = os.environ.get("TERM")
    if term not in ['xterm']:
        return ''

    # TODO: if not tty stdout, return ''

    ansi = {
        "normal": 0,
        "bold": 1,
        "red": 31,
        "redbg": 41,
    }

    codes = []
    for mode in modes:
        if mode in ansi:
            codes.append(str(ansi[mode]))

    if len(codes) == 0:
        codes.append(str(ansi["normal"]))

    return "\x1b[" + ";".join(codes) + "m"


def render_password(password):
    return sgr("bold","red","redbg") + password + sgr()


def render_list(found):
    # TODO sort group,title,username

    for item in found:
        # TODO column widths
        group = "/" + "/".join(item.path[1:-1])
        print(
            group,
            item.title,
            item.username,
            render_password(item.password),
            item.url
        )


def argparser():
    ap = argparse.ArgumentParser(
        description="__doc__",
    )

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")

    if not xdg_config_home:
        xdg_config_home = os.path.expanduser("~/.config")
    if not xdg_runtime_dir:
        xdg_runtime_dir = "/run/lock"

    config_filename = os.path.join(xdg_config_home, "keepassc.yaml")
    cache_filename = os.path.join(xdg_runtime_dir, "kdbcache.yaml")

    ap.add_argument(
        "--config",
        default=config_filename,
        help="Location of config file"
    )
    ap.add_argument(
        "--cachefile",
        default=cache_filename,
    )
    ap.add_argument(
        "--debug",
        default=False,
        action="store_true",
    )
    ap.add_argument(
        "--sudo",
        default=False,
        action="store_true",
        help="Format output for use in automation"
    )

    ap.add_argument("-k", "--kdb")
    ap.add_argument("--password")
    ap.add_argument("--preset", "-s")
    ap.add_argument("--add", "-a")
    ap.add_argument("search")

    args = ap.parse_args()
    return args


def main():
    args = argparser()

    config = config_load(args.config)
    config_cache_load(config, args.cachefile)
    config_addargs(config, args)

    if args.debug:
        print("Option:", args)
        print("Config:", config)

    k = kdb_load(args.preset, config)

    # TODO:
    # subp_add()

    found = k.find_entries(title=args.search, regex=True)

    if args.sudo:
        render_sudo(found)
    else:
        render_list(found)

if __name__ == "__main__":
    main()
