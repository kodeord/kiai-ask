# version = "1"
# date = 2026-11-15
#
# Unofficial: part of a personal learning project, not affiliated with or
# endorsed by Mistral AI or any other provider. Shared as is, without warranty of
# any kind.
# Written and tested on macOS (Apple silicon, zsh) only; not tried on Linux or
# Windows.
# AI helped with parts of this code.

# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 kodeord (https://github.com/kodeord). See the file LICENSE.
"""Shared command-line helpers for the scripts beside this lib/ folder.

What the scripts have in common, so it lives here once:

    options   option_groups(): the groups -h lists the options in (model,
              prompt, answer); add_common_options(): what the ask scripts
              share (-u, -s, -t, -y, -x, -l, -L, the save options, --version,
              --max and -p), put in those groups; parse_common_args() writes
              out -p (PRESETS), checks --max and reads the -u file.
    saving    the options that save an answer to a file (-o, -a, -A, -q):
              add_save_options() adds them to the script's parser,
              prepare_save() checks them before anything is sent, and
              save_answer() writes the file once the answer is in.
    version   --version, read from the # version and # date lines at the
              top of the script: add_version_option().
    prompt    read_prompt(): the argument, the text piped in, or the prompt
              typed, and the system prompt (-s); for text piped in also its
              SHA-256, as shasum -a 256 FILE gives it, for -x. Standard
              input that is /dev/null or closed is nothing piped in; an
              empty pipe or file stops the script.
              read_prompt_file(): -u, the prompt from a file in place of the
              argument, and the SHA-256 of the file, for -x.
    asking    confirm_send() asks y/n before a large prompt; ask() asks any
              question on the keyboard.
    YAML      frontmatter() and one_line(): the header -x puts above the answer.
    the file  file_text(): what a saved answer holds, with the NOT COMPLETE
              mark and the thinking folded under it (-t).
    the end   finish(): the answer to the screen and to its file, and the
              exit status, the same in all the ask scripts.
    the log   log_run(): with -l, one Markdown entry in log.md (-L: and log.txt) in data/
              beside the scripts, or the script's own folder (log2.md with -l 2, and
              so on): the date and the model, the command under the
              script's file name, the start of what was sent (>>) and of
              the answer (<<), and their lengths (-> and <-).
    errors    api_error(): the message for a failed API call, the same in
              every script.

Three smaller helpers are shared as well: write_new() writes a file without
ever overwriting one, ollama_url() reads OLLAMA_HOST the way Ollama does, and
split_think() takes the <think>...</think> some models put first in the text.

The three ways to save, each an option in the script. The answers folder is
data/answers beside the scripts (OUT_DIR below), unless the script passes its
own to prepare_save():

    -o FILENAME  FILENAME in the answers folder, with .md added when it has no
                 suffix. A name with a folder in it (./answer.md,
                 ~/notes/answer.md) is used as written.
    -a           <name>_<date>_<time>.md in the answers folder, the name from the
                 local model in Ollama (LOCAL_MODEL below), in the language of
                 the prompt. If Ollama does not answer, the file is saved all
                 the same, with date and time only.
    -A           as -a, but the name from Mistral Small, in English (needs
                 MISTRAL_API_KEY). A script can leave it out (mistral=False),
                 and MISTRAL_NAMING = False below takes it out of all of them.

The answer is printed as well, unless -q. Nothing is overwritten: an existing
file gets _2, _3 ... beside it. The naming model sees the start of the prompt
(NAME_CHARS characters), not the answer.

The scripts import this from lib/, beside them. Python 3.10 or newer, standard
library only; mistralai is imported for -A alone.
"""

import hashlib
import ipaddress
import json
import os
import re
import stat
import sys
import threading
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import fill, shorten
from typing import NamedTuple

# =============================================================================
# Settings
# =============================================================================

# The answers folder unless a script has its own: data/answers beside the scripts
# (the folder above lib/), wherever they run from.
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "answers"
# -l: the folder for the log unless a script has its own: data/ beside the
# scripts, with log.md (-l, -l 1), log2.md (-l 2) ..., and with -L also log.txt,
# log2.txt ... Keep it out of git: the .gitignore beside the scripts leaves out
# all of data/.
LOG_DIR = Path(__file__).resolve().parent.parent / "data"
# -l: the longest line in it. 67 fits Word's usual font in 12 pt on an A4 page
# with normal margins, so a log pasted in keeps its lines as they are here.
LOG_WIDTH = 67
# -l and -L: the note at the top of a new log file, so a reader who does not
# know the scripts can read the entries. One text for both files: in log.md as
# an Obsidian callout, in log.txt (-L) without the backticks. {chars} is the
# script's LOG_CHARS; {day} and {entry} are how the file marks a day and an entry.
LOG_LEGEND = ("One entry per call with -l (-L writes it to the .txt file of the same "
              "name as well). {day} is the day, {entry} the time and the model that "
              "answered. Then the command as typed (without the prompt), `>>` the "
              "start of what was sent, `<<` the start of the answer (the first {chars} "
              "characters each, with their own line breaks; `...` marks a cut), and "
              "`->` / `<-` the full lengths in characters. `not complete`: the answer "
              "stopped before it was whole.")
# -p N, a shorthand for options typed often: -p 1 (or -p1) is read as the
# options listed for "1", where -p stood. An option after it still wins
# (-p 1 -e 2 is -e 2), and the log (-l) shows those options, not -p. One list
# for every script that uses this file, so -p 1 means the same in each; -h
# lists them. Use options they all have (-e, -t, -x, -y, -l, -L ...): a model
# name (-m) is the script's own, so it goes in SCRIPT_PRESETS. With both empty
# there is no -p. Left out on purpose, to be chosen run by run: where the
# answer goes (-o, -a or -A, which cannot stand together). A bare -l comes
# first in a list, so a prompt that is only a number is not read as its number.
PRESETS = {
    "1": ["-e", "3"],               # the most thinking
    "2": ["-l", "-x"],              # a documented run: logged, with YAML above the answer
    "3": ["-l", "-x", "-e", "3"],   # both
}
# -p for one script only, by the name before _ask in its file name (mis for
# mis_ask.py). Its numbers win over the same numbers in PRESETS, in that
# script, so they start at 4 and leave 1 to 3 the same everywhere. Here 4 is a
# fast, cheap model at the least thinking and 5 a strong one at the most.
SCRIPT_PRESETS: dict[str, dict[str, list[str]]] = {
    "mis": {"4": ["-m", "small", "-e", "1"], "5": ["-m", "ml", "-e", "3"]},
}
# The local model: -a names the file with it. Any model installed in Ollama
# (ollama list). The environment variable LOCAL_MODEL_CLI_COMMON, when set,
# names another one without a change here: an -mlx model runs only on a Mac
# with Apple silicon, so elsewhere set it to one without, e.g.
# export LOCAL_MODEL_CLI_COMMON=gemma4:12b in ~/.bashrc.
LOCAL_MODEL = os.environ.get("LOCAL_MODEL_CLI_COMMON") or "gemma4:12b-mlx"
# -A, the file named by Mistral: rarely used. False takes -A out of all the
# scripts, and -a and -o work as before; the lines about -A in the scripts'
# docstrings can then go.
MISTRAL_NAMING = True
MISTRAL_NAME_MODEL = "mistral-small-latest"   # the model for -A
NAME_CHARS = 2_000                  # how much of the prompt the naming model sees
NAME_TIMEOUT_S = 60                 # the first call loads the model into memory
# read_prompt(): how long standard input that is not the keyboard may stay
# silent before a line on the screen says the script is waiting for it.
STDIN_NOTE_S = 3

# For the local model (-a): the words in the language of the prompt. Letters
# like æ, ø, å and ß are written as ASCII in the file name (_clean_name below).
NAME_SYSTEM = ("Reply with 3-6 lowercase words naming the topic of the text. "
               "Use the same language as the text. No punctuation, no explanation.")


# =============================================================================
# Options, saving and the file name
# =============================================================================

@dataclass
class SaveTarget:
    path: Path | None   # -o: the file; -a/-A: None, it is named once the answer is in
    namer: str     # "" (-o), "ollama" (-a) or "mistral" (-A)
    folder: Path | None = None   # -a/-A: the answers folder; None for OUT_DIR


def add_save_options(parser, mistral: bool = True) -> None:
    """-o, -a and (with mistral=True and MISTRAL_NAMING) -A on the script's
    parser or one of its groups, one at a time, and -q."""
    mistral = mistral and MISTRAL_NAMING
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-o", "--output", metavar="FILENAME",
                   help="save the answer as FILENAME in the answers folder too (data/answers "
                        "unless the script sets another; .md added when FILENAME has no suffix; "
                        "a name with a folder is used as written); never overwrites: "
                        "FILENAME_2, FILENAME_3 ...")
    g.add_argument("-a", "--auto", action="store_true",
                   help="save the answer in the answers folder too, named by the local model in "
                        "Ollama (date and time only if Ollama does not answer)")
    if mistral:
        g.add_argument("-A", "--auto-mistral", action="store_true",
                       help=f"as -a, but named in English by {MISTRAL_NAME_MODEL}; "
                            f"the start of the prompt goes to Mistral")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help=("with -o, -a or -A" if mistral else "with -o or -a")
                             + ": save the answer without printing it")


def add_version_option(parser, script: str) -> None:
    """--version: the # version and # date lines at the top of the script."""
    head = Path(script).read_text(encoding="utf-8")[:300]
    version = re.search(r'^# version = "([^"]+)"', head, re.MULTILINE)
    date = re.search(r"^# date = (\S+)", head, re.MULTILINE)
    v, d = (version[1] if version else "?"), (date[1] if date else "?")
    parser.add_argument("--version", action="version", version=f"%(prog)s {v} ({d})")


def option_groups(parser) -> dict:
    """The groups -h lists the options in, below -h and --version: model,
    prompt and answer. The script puts its own options in them before
    add_common_options() adds the shared ones, or after, to come last."""
    return {title: parser.add_argument_group(title) for title in ("model", "prompt", "answer")}


def add_common_options(parser, script: str, *, ask_above: int, thinking_help: str,
                       yaml_fields: str, max_help: str, mistral: bool = True,
                       groups: dict | None = None, log_chars: int | None = None,
                       log_dir: Path | None = None) -> None:
    """What the ask scripts share, in the same groups and order in each:
    -t and --max under model, -u, -s and -y under prompt, -o/-a/-A/-q (no
    -A with mistral=False), -x and (with log_chars) -l and -L under answer, and
    -p (when there are presets for the script) and --version beside -h.
    groups: from option_groups(), with the script's own
    options in them; made here when not given. ask_above: the prompt's size in
    characters above which the script asks y/n, for -y's help. log_chars: how
    much of the prompt and the answer -l logs (LOG_CHARS in the script).
    log_dir: the script's own log folder, for -l's help; None for LOG_DIR. The
    help that differs from script to script is passed in."""
    groups = groups or option_groups(parser)
    model, prompt, answer = groups["model"], groups["prompt"], groups["answer"]
    model.add_argument("-t", "--thinking", action="store_true", help=thinking_help)
    model.add_argument("--max", type=int, metavar="N", help=max_help)
    prompt.add_argument("-u", "--user", metavar="FILE",
                        help="the prompt from a file (e.g. my_prompt.md), in place of "
                             "the argument; text piped in is then the document")
    prompt.add_argument("-s", "--system", metavar="TEXT",
                        help='system prompt, e.g. -s "$(< my_system_prompt.md)"')
    prompt.add_argument("-y", "--yes", dest="yes", action="store_true",
                        help=f"send without asking, also above {ask_above:,} chars")
    add_save_options(answer, mistral)
    answer.add_argument("-x", "--yaml", action="store_true",
                        help=f"put YAML frontmatter ({yaml_fields}) above the answer, for Obsidian")
    # -p beside -h and --version, as it may stand for options from any group.
    presets = presets_for(script)
    if presets:
        shown = "; ".join(f"{n}: {' '.join(opts)}" for n, opts in presets.items())
        shown = shown.replace("%", "%%")   # argparse reads % in help as a format
        parser.add_argument("-p", "--preset", metavar="N", choices=list(presets),
                            help=f"options typed often, by number ({shown}), as set in "
                                 f"lib/cli_common.py; -p1 works too, and an option after "
                                 f"-p overrides it")
    parser.presets = presets   # parse_common_args() writes -p N out with these
    if log_chars:
        # -l and -l 1 log to log.md, -l 2 to log2.md and so on; -L the same, and to
        # log.txt as well. The folder as seen from the script's own: data/ unless it
        # has moved. A bare -l or -L gives "" (check_log_numbers makes it a number).
        where = os.path.relpath(log_dir or LOG_DIR, Path(script).resolve().parent)
        answer.add_argument("-l", "--log", nargs="?", const="", metavar="N",
                            help=f"add the date and model, the command, the first {log_chars} "
                                 f"chars of prompt and answer, and their lengths, to "
                                 f"log.md in {where}/; -l 2 to log2.md, -l 3 to "
                                 f"log3.md ...")
        answer.add_argument("-L", "--log-txt", nargs="?", const="", metavar="N",
                            help="as -l, and the same entry as plain text in log.txt "
                                 "(-L 2: log2.md and log2.txt), for Word or a plain editor")
    add_version_option(parser, script)


def check_log_numbers(parser, args, words: list) -> None:
    """-l and -L take an optional number; -L is -l with a plain-text copy in
    log.txt. A word right after a bare -l or -L that is not a number belongs to
    words (the prompt), though argparse took it for the option's: it goes back
    there. Afterwards args.log is the number for both files, or None, and
    args.log_txt says whether -L was given. -l 2 -L logs once, to log2.md and
    log2.txt; two different numbers stop with a message."""
    given = {}
    for name, flag in (("log", "-l"), ("log_txt", "-L")):
        value = getattr(args, name, None)
        if value and not value.isdecimal():
            words.insert(0, value)
            value = ""
        if value and int(value) < 1:
            parser.error(f"{flag} takes a number from 1: {flag} (the same as {flag} 1), "
                         f"{flag} 2, {flag} 3 ...")
        if value is not None:
            given[flag] = value
    numbers = {v for v in given.values() if v}
    if len(numbers) > 1:
        parser.error("-l and -L log to the same files: give the number once, e.g. -L 2")
    args.log = (numbers.pop() if numbers else "1") if given else None
    args.log_txt = "-L" in given


def presets_for(script: str) -> dict:
    """-p in this script: PRESETS, with the script's own numbers from
    SCRIPT_PRESETS over them. The script is known by the name before _ask in
    its file name, so a number in front of the name changes nothing."""
    name = Path(script).name
    own = next((p for short, p in SCRIPT_PRESETS.items() if f"{short}_ask" in name), {})
    return {**PRESETS, **own}


def expand_presets(words: list, presets: dict) -> list:
    """words (the command line after the script's name) with each -p N written
    out as the options in presets[N], where it stood. -pN, -p=N, --preset N and
    --preset=N work too. Nothing after -- is touched, as it is all prompt. A
    number not in presets is left as it is, for argparse to name the ones
    there are."""
    out, i = [], 0
    while i < len(words):
        word = words[i]
        if word == "--":
            return out + words[i:]
        joined = re.fullmatch(r"(?:-p=?|--preset=)(.+)", word)
        if joined:
            number, step = joined[1], 1
        elif word in ("-p", "--preset") and i + 1 < len(words):
            number, step = words[i + 1], 2
        else:
            number, step = None, 1
        if number in presets:
            out += presets[number]
            i += step
        else:
            out.append(word)
            i += 1
    return out


def parse_common_args(parser):
    """The parsed options, with --max checked: at least 1, when given, and -l
    and -L as check_log_numbers leaves them. Two more for read_prompt() and -x:
    args.words, the prompt as given or, with -u, the text of its file, and
    args.prompt_sha256, the SHA-256 of that file (None without -u). The
    argument stays in args.prompt as typed, for the log. -u and a prompt
    argument together stop as a wrong argument. -p N is written out in
    sys.argv first (expand_presets), so argparse reads the options it stands
    for, and the log shows them."""
    presets = getattr(parser, "presets", None)
    if presets:
        sys.argv[1:] = expand_presets(sys.argv[1:], presets)
    args = parser.parse_args()
    if getattr(args, "preset", None) is not None:
        # -p joined to other letters (-yp1): argparse reads it, but it was not
        # written out above, so it would do nothing.
        parser.error("write -p apart from other options: -p 1 or -p1, not -yp1")
    if args.max is not None and args.max < 1:
        parser.error("--max must be at least 1")
    if hasattr(args, "log"):
        check_log_numbers(parser, args, args.prompt)
    args.words, args.prompt_sha256 = getattr(args, "prompt", []), None
    if getattr(args, "user", None):
        if args.words:
            parser.error("-u gives the prompt: give no prompt argument with it")
        text, args.prompt_sha256 = read_prompt_file(args.user, parser)
        args.words = [text]
    return args


def _check_writable(folder: Path, flag: str) -> None:
    """Stop before anything is sent if no file can be made in folder. A folder
    not made yet is judged by the nearest one above it that exists."""
    existing = folder
    while not existing.exists():
        existing = existing.parent
    if not os.access(existing, os.W_OK):
        sys.exit(f"{flag}: the folder {folder} is not writable. Nothing was sent.")


def prepare_save(args, out_dir: Path | None = None) -> SaveTarget | None:
    """Before anything is sent: where the answer is to go, or None for the
    screen. Stops with a message when it cannot be saved, so nothing is sent in
    vain. out_dir: the script's own answers folder, made when it does not
    exist; None for OUT_DIR."""
    folder = out_dir or OUT_DIR
    saving = args.output is not None or args.auto or getattr(args, "auto_mistral", False)
    if args.quiet and not saving:
        ways = "-o, -a or -A" if hasattr(args, "auto_mistral") else "-o or -a"
        print(f"-q needs a way to save ({ways}): without one the answer would go "
              "nowhere. Nothing was sent.", file=sys.stderr)
        sys.exit(2)
    if args.output is not None:
        name = args.output.strip()
        path = Path(name).expanduser() if ("/" in name or name.startswith("~")) else folder / name
        # Before the suffix: once .md is added, a folder no longer looks like one.
        # The last part "", "." or ".." is a folder too, made yet or not.
        last = name.replace(os.sep, "/").rsplit("/", 1)[-1]
        if last in ("", ".", "..") or path.is_dir():
            sys.exit(f"-o {args.output!r}: give a file name, not a folder. Nothing was sent.")
        if not path.suffix:
            path = path.with_name(path.name + ".md")
        if path.parent != folder and not path.parent.is_dir():
            sys.exit(f"-o: the folder {path.parent} does not exist. Nothing was sent.")
        _check_writable(path.parent, "-o")
        if path.parent == folder:
            folder.mkdir(parents=True, exist_ok=True)
        return SaveTarget(path, "")
    if getattr(args, "auto_mistral", False):
        _check_mistral_key()
        _check_writable(folder, "-A")
        return SaveTarget(None, "mistral", out_dir)
    if args.auto:
        _check_writable(folder, "-a")
        return SaveTarget(None, "ollama", out_dir)
    return None


def save_answer(target: SaveTarget, text: str, name_text: str, num_ctx: int | None = None) -> Path:
    """Write text to its file and return the path. With -a or -A the name is
    asked for first; if that fails, the file gets date and time only.
    num_ctx: the window of a script that calls Ollama itself, so -a names with
    the model as it is already in memory, and Ollama does not load it again."""
    path = target.path
    if path is None:
        folder = target.folder or OUT_DIR
        folder.mkdir(parents=True, exist_ok=True)
        label, source = "", ""
        if target.namer == "ollama":
            label, source = _name_from_ollama(name_text, num_ctx), LOCAL_MODEL
        elif target.namer == "mistral":
            label, source = _name_from_mistral(name_text), MISTRAL_NAME_MODEL
        if label:
            print(f"Name:  {label} (from {source})", file=sys.stderr)
        path = folder / ((f"{label}_" if label else "") + f"{datetime.now():%Y-%m-%d_%H-%M-%S}.md")
    return write_new(path, text)


def write_new(path: Path, text: str, newline: str | None = None) -> Path:
    """Write to path, or to the first free path_2, path_3 ... beside it. Mode "x"
    refuses a file that exists, so nothing is overwritten, even in a race.
    newline="" writes the line ends in text as they are (a CSV file); the
    default turns \n into the line end of the system, as text files get."""
    candidate, n = path, 1
    while True:
        try:
            with open(candidate, "x", encoding="utf-8", newline=newline) as f:
                f.write(text)
            return candidate
        except FileExistsError:
            n += 1
            candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")


def split_think(text: str) -> tuple[str, str]:
    """Some models put their thinking first in the text, as <think>...</think>,
    or with no </think> when they were cut off: -> (the rest, the thinking).
    A text without it comes back as it is, with no thinking."""
    m = re.match(r"<think>(.*?)(</think>|\Z)", text, re.DOTALL)
    if not m:
        return text, ""
    return text[m.end():].strip(), m.group(1).strip()


def _no_name(reason: str) -> str:
    """Say why there is no name, and go on without one."""
    print(f"Name:  none — {reason}; the file gets date and time only", file=sys.stderr)
    return ""


def _clean_name(reply: str) -> str:
    """The model's reply as a file-safe name: first line, ASCII, words joined by _."""
    reply = re.sub(r"<think>.*?(</think>|\Z)", "", reply, flags=re.DOTALL)
    line = next((l for l in reply.splitlines() if l.strip()), "")
    line = line.translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a", "ß": "ss",
                                         "Æ": "ae", "Ø": "o", "Å": "a"}))
    line = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode()
    name = "_".join(re.findall(r"[a-z0-9]+", line.lower())[:8])[:60].rstrip("_")
    return name or _no_name("the model gave no usable name")


def ollama_url(value: str) -> str:
    """OLLAMA_HOST read the way Ollama itself reads it: no scheme means http,
    then a missing port means 11434, and 0.0.0.0 becomes localhost. A bare
    IPv6 address (::1) is an address, and a port that is not a number gives
    the default. For -a here and for a script that calls Ollama itself."""
    v = value.strip().rstrip("/") or "http://localhost:11434"
    no_scheme = "://" not in v
    # A bare IPv6 address (::, ::1) has colons that are not a port. Ollama reads
    # it as an address, so it goes in brackets before the URL is split.
    scheme, _, rest = v.rpartition("://")
    hostport, slash, tail = rest.partition("/")
    try:
        ipaddress.IPv6Address(hostport)
        v = (f"{scheme}://" if scheme else "") + f"[{hostport}]{slash}{tail}"
    except ValueError:
        pass
    u = urllib.parse.urlsplit("http://" + v if no_scheme else v)
    host = u.hostname or "localhost"
    if host in ("0.0.0.0", "::"):
        host = "localhost"
    if ":" in host:                      # an IPv6 literal goes back in brackets
        host = f"[{host}]"
    try:
        port = u.port
    except ValueError:                   # not a number: Ollama uses its default port
        port = None
    port = port or (11434 if no_scheme else None)
    return f"{u.scheme}://{host}" + (f":{port}" if port else "") + u.path


def _name_from_ollama(text: str, num_ctx: int | None = None) -> str:
    """A short name from LOCAL_MODEL in the local Ollama, or "" with the reason
    on the screen. Nothing goes anywhere but this machine. num_ctx: the same window
    as the call before it, or Ollama loads the model again (measured: 2.6 s)."""
    host = ollama_url(os.environ.get("OLLAMA_HOST", ""))
    if urllib.parse.urlsplit(host).hostname not in ("localhost", "127.0.0.1", "::1"):
        return _no_name(f"OLLAMA_HOST points to {host}, not this machine")
    # No proxy: localhost stays local.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{host}/api/tags", timeout=2) as r:
            installed = {m.get("name", "") for m in json.load(r).get("models", [])}
        if not {LOCAL_MODEL, f"{LOCAL_MODEL}:latest"} & installed:
            return _no_name(f"{LOCAL_MODEL} is not installed in Ollama")
        call = urllib.request.Request(
            f"{host}/api/chat", method="POST", headers={"Content-Type": "application/json"},
            data=json.dumps({
                "model": LOCAL_MODEL,
                "messages": [{"role": "system", "content": NAME_SYSTEM},
                             {"role": "user", "content": text[:NAME_CHARS]}],
                "stream": False,
                "think": False,          # a model that can think would otherwise do so
                "options": {"num_predict": 30, **({"num_ctx": num_ctx} if num_ctx else {})},
            }).encode())
        with opener.open(call, timeout=NAME_TIMEOUT_S) as r:
            reply = json.load(r)
    except (OSError, ValueError) as e:   # not running, refused, timeout, HTTP error, bad JSON
        reason = getattr(e, "reason", None) or type(e).__name__
        return _no_name(f"Ollama did not answer ({reason})")
    except KeyboardInterrupt:            # Ctrl-C: the answer is saved all the same
        return _no_name("stopped with Ctrl-C")
    if reply.get("done_reason") != "stop":
        return _no_name(f"the name from {LOCAL_MODEL} was cut off")
    return _clean_name((reply.get("message") or {}).get("content") or "")


# =============================================================================
# The prompt, the question, the YAML header, the saved text, errors
# =============================================================================

class Prompt(NamedTuple):
    instruction: str        # the argument, "" without one
    document: str | None    # the text piped in; None when nothing was piped
    user: str               # what is sent: the instruction, the document, or both
    system: str             # -s, "" without it
    document_sha256: str | None   # of the bytes piped in, as they came; None without


def read_prompt_file(path: str, parser) -> tuple[str, str]:
    """-u: the prompt in a file, as UTF-8 text, and the SHA-256 of its bytes as
    shasum -a 256 FILE gives it (for -x). A BOM from a Windows editor is dropped,
    and line breaks become \\n. A file that cannot be read, or holds no text,
    stops the script as a wrong argument (exit status 2)."""
    try:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        parser.error(f"-u {path}: not UTF-8 text")
    except OSError as e:
        parser.error(f"-u {path}: {e.strerror or e}")
    if not text.strip():
        parser.error(f"-u {path}: the file is empty")
    return text, hashlib.sha256(raw).hexdigest()


def _piped_bytes() -> bytes | None:
    """The bytes piped in or redirected from a file, or None when nothing is:
    standard input is the keyboard, is closed, or is a device such as
    /dev/null, which is what cron, CI and a background job in a shell script
    give a program. An empty pipe or an empty file is not None but b"", and
    read_prompt() stops on it: the command that was to fill it may have
    failed. A pipe can also be open with nothing coming (an IDE, ssh): after
    STDIN_NOTE_S seconds a line on the screen says what the script waits for."""
    stdin = sys.stdin
    if stdin is None or stdin.isatty():
        return None
    try:
        if stat.S_ISCHR(os.fstat(stdin.fileno()).st_mode):
            return None
    except (OSError, ValueError, AttributeError):   # no file behind it (a test): read it as it is
        pass
    note = threading.Timer(STDIN_NOTE_S, print, [
        "Waiting for the text piped in ... (nothing to pipe in? Ctrl-C, then add < /dev/null)"],
        {"file": sys.stderr})
    note.daemon = True
    note.start()
    try:
        return stdin.buffer.read()
    except KeyboardInterrupt:
        sys.exit("\nStopped. Nothing was sent.")
    finally:
        note.cancel()


def read_prompt(words: list, system: str | None) -> Prompt:
    """The prompt as the scripts take it. The argument, if any, is the
    instruction. Text piped in or redirected from a file is the document it
    applies to. With neither, the prompt is typed. An empty text, text piped
    in that is not UTF-8, or an empty -s stops the script with a message,
    before anything is sent. What counts as piped in: _piped_bytes()."""
    instruction = " ".join(words).strip()
    document = digest = None
    raw = _piped_bytes()
    if raw is not None:
        # The bytes are hashed before anything is changed, so the SHA-256 is the
        # file's own (shasum -a 256 FILE). Then read as UTF-8, whatever the
        # terminal's settings; a BOM from a Windows editor is dropped.
        digest = hashlib.sha256(raw).hexdigest()
        try:
            document = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            sys.exit("The text piped in is not UTF-8 text. Nothing was sent.")
        # Line ends as \n, also from a Windows file (\r\n) on a Mac, as -u reads
        # its file. The SHA-256 above is of the bytes as they came.
        document = document.replace("\r\n", "\n").replace("\r", "\n")
        document = document.strip()
        if not document:
            sys.exit("The text piped in is empty. Nothing was sent.")
        user = f"{instruction}\n\n---\n\n{document}" if instruction else document
    elif instruction:
        user = instruction
    elif sys.stdin is None or not sys.stdin.isatty():
        # No argument, nothing piped in and no keyboard to type at (/dev/null).
        sys.exit("No prompt: give it as an argument, with -u or piped in. Nothing was sent.")
    else:
        # Read to the end, not just one line, so a pasted paragraph keeps its line
        # breaks and no pasted line is left over for the shell to run afterwards.
        print("Prompt (finish with Ctrl-D on a new line; Windows: Ctrl-Z, then Enter):",
              file=sys.stderr)
        try:
            user = sys.stdin.read().strip()
        except KeyboardInterrupt:
            sys.exit("\nStopped. Nothing was sent.")
        if not user:
            sys.exit("Empty prompt. Nothing was sent.")
    system_prompt = (system or "").strip()
    if system is not None and not system_prompt:
        sys.exit("The system prompt (-s) is empty. Nothing was sent.")
    return Prompt(instruction, document, user, system_prompt, digest)


def ask(question: str, yes: str = "y") -> bool | None:
    """Ask on the keyboard (/dev/tty), since standard input may be the text.
    True for the answer in yes, False for anything else, None with no terminal.
    Windows has no /dev/tty, so there confirm_send() says to use -y."""
    try:
        # Two handles: a terminal cannot be opened "r+", which raises an OSError
        # and would read as "no terminal".
        with open("/dev/tty") as tty_in, open("/dev/tty", "w") as tty_out:
            tty_out.write(question)
            tty_out.flush()
            return tty_in.readline().strip().lower() == yes.lower()
    except OSError:
        return None
    except KeyboardInterrupt:
        sys.exit("\nStopped. Nothing was sent.")


def confirm_send(chars: int, to: str) -> None:
    """Before a large prompt: y sends; anything else, or no terminal to ask
    in, stops the script with nothing sent. The scripts' -y skips this."""
    send = ask(f"{chars:,} chars to {to}. Send? [y/N] ")
    if send is None:
        sys.exit(f"{chars:,} chars and no terminal to ask in: add -y to send. "
                 f"Nothing was sent.")
    if not send:
        sys.exit("Nothing was sent.")


def one_line(text: str, n: int = 100) -> str | None:
    """One line, at most n characters, for the YAML; None when empty."""
    t = " ".join(text.split())
    return (t[:n] + "…" if len(t) > n else t) or None


def frontmatter(fields: dict) -> str:
    """YAML frontmatter, as Obsidian reads it. Each value is written as JSON,
    which is valid YAML: a string stays quoted, whatever it holds, and a list
    stays a list. The date is left bare, so Obsidian reads it as a date. None
    is left out."""
    lines = []
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, datetime):
            lines.append(f"{k}: {v.isoformat(timespec='seconds')}")
        else:
            lines.append(f"{k}: " + json.dumps(v if isinstance(v, (bool, int, float, list))
                                               else str(v), ensure_ascii=False))
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def file_text(header: str, answer: str, whole: bool, reason, thinking: str = "",
              label: str = "Thinking") -> str:
    """What a saved answer holds: the YAML header (-x, or ""), a NOT COMPLETE
    mark when the answer is not whole, with the reason the API gave, so a
    fragment does not read as a whole answer, the answer, and the thinking
    folded under it when there is any (pass it only with -t). Standard output
    gets neither the mark nor the thinking: only the file does."""
    mark = ("" if whole else f"> ⚠️ **NOT COMPLETE** (`{reason}`) — this is a fragment, "
                             f"not the whole answer.\n\n")
    fold = (f"\n\n<details><summary>{label} — {len(thinking):,} chars</summary>"
            f"\n\n{thinking}\n\n</details>" if thinking else "")
    return header + mark + answer + fold + "\n"


def finish(args, target: SaveTarget | None, header: str, answer: str, whole: bool, reason,
           thinking: str, name_text: str, label: str = "Thinking",
           num_ctx: int | None = None) -> int:
    """The end of the ask scripts: the answer to standard output unless
    -q, and with -o, -a or -A to its file as well (file_text). The exit status:
    0 a whole answer, 3 one that is not, 1 one that could not be saved. Then
    an answer that was not printed (-q) is printed after all, so it is not
    lost. name_text: what -a and -A name the file from; num_ctx: as
    in save_answer."""
    if not answer:
        print("(no text)" + (" — nothing saved" if target else ""), file=sys.stderr)
        return 3
    # On the screen as well, also when the answer is saved, unless -q. The
    # same as without saving: the thinking and the NOT COMPLETE mark go to
    # the file only. flush: the answer shows before the file is named.
    if not args.quiet:
        print(header + answer, flush=True)
    if target:
        # The file also gets the NOT COMPLETE mark and, with -t, the thinking
        # folded under the answer.
        body = file_text(header, answer, whole, reason, thinking if args.thinking else "",
                         label=label)
        try:
            path = save_answer(target, body, name_text, num_ctx)
        except OSError as e:   # checked before sending, but a disk can fill up
            print(f"Not saved ({type(e).__name__}): {e}"
                  + (". The answer is printed here instead." if args.quiet else ""),
                  file=sys.stderr)
            if args.quiet:
                print(header + answer, flush=True)
            return 1
        print(f"Saved: {path}", file=sys.stderr)
    return 0 if whole else 3


def _log_excerpt(mark: str, text: str, chars: int) -> str:
    """The start of text for the log: at most chars characters, cut at a space
    and marked ..., with its own line breaks kept and blank lines left out,
    each line wrapped at LOG_WIDTH under mark (>> or <<)."""
    text = text.strip()
    if len(text) > chars:
        cut = text[:max(0, chars - 3)]
        space = max(cut.rfind(" "), cut.rfind("\n"))
        text = (cut[:space] if space > 0 else cut).rstrip() + "..."
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line] or ["(no text)"]
    return "\n".join(fill(line, LOG_WIDTH, initial_indent=mark if k == 0 else "   ",
                          subsequent_indent="   ") for k, line in enumerate(lines))


def _append_log(path: Path, mark: str, legend: str, day_line: str, day: str,
                entry: list) -> None:
    """Add entry to the log at path, after legend if the file is new and after
    day_line if it is the day's first: the last heading (mark and a date) says
    which day the last entry was. A blank line follows each part, and one is
    put before them when the file does not end in one: a note of your own
    under the last entry may end without it, or without a line break at all,
    and the next heading would then join its last line."""
    try:
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        old = None   # unreadable: no legend and no day line, the entry still goes in
    head = ""
    if old is not None:
        if not old.strip():
            head = legend + "\n\n"
        days = re.findall(rf"^{re.escape(mark)}(\d{{4}}-\d{{2}}-\d{{2}}) ", old, re.M)
        if not days or days[-1] != day:
            head += day_line + "\n\n"
        breaks = len(old) - len(old.rstrip("\n"))   # line breaks at the end
        if old.strip() and breaks < 2:
            head = "\n" * (2 - breaks) + head
    with open(path, "a", encoding="utf-8") as f:
        f.write(head + "\n".join(entry) + "\n\n")


def log_run(model: str, prompt_words: list, sent: str, answer: str,
            chars: int, number: str = "1", folder: Path | None = None,
            whole: bool | None = None, txt: bool = False) -> None:
    """-l: one entry in log.md (number 1, the default) or logN.md (-l N), in
    folder (the script's own; None for LOG_DIR), made if needed. The entry is
    Markdown for Obsidian and still plain text in any editor: a ### heading with
    the date, the time to the second and the model that answered, then a code
    block with the command as typed, under the script's file name
    (mis_ask.py ...), so the entry says which script ran, the first chars
    characters of what was sent (>>) and of the answer (<<), with their own
    line breaks, wrapped at LOG_WIDTH, and their lengths (-> and <-), with
    "not complete" when whole is False. A new file starts with LOG_LEGEND, and
    the first entry of a day gets a ## heading of its own (## 2026-11-03), so a
    day folds in Obsidian. # is not used, so a title of your own can go on top. With txt (-L) the same lines go to log.txt (logN.txt)
    as well, under a line of dashes with the date, time and model, with a
    line of = for the day and the legend as plain text. Only the log is cut.
    prompt_words: the prompt as given on the command line, taken out of the
    command, wherever it stands, since it has a line of its own; -l and its
    number go as well. -s stands as its start and length, e.g.
    -s "You are a professional..." (2,026 chars). A log that cannot be written
    says so on the screen; the answer is out already."""
    n = len(prompt_words)
    i = next((i for i in range(len(sys.argv) - n, 0, -1)
              if sys.argv[i:i + n] == prompt_words), None)
    words = sys.argv[1:] if i is None else sys.argv[1:i] + sys.argv[i + n:]
    gone = {j for j, a in enumerate(words)
            if a in ("-l", "--log", "-L", "--log-txt", "--")
            or re.fullmatch(r"-[lL]\d+|--log(-txt)?=\S*", a)
            or (j and words[j - 1] in ("-l", "--log", "-L", "--log-txt") and a.isdecimal())}
    def shown(j: int, a: str) -> str:
        # -s as its start and length, also written --system=TEXT or -sTEXT: a
        # system prompt from a file would fill the entry.
        flag, text = "", None
        if j and words[j - 1] in ("-s", "--system"):
            text = a
        elif a.startswith("--system="):
            flag, text = "--system=", a[len("--system="):]
        elif a.startswith("-s") and len(a) > 2:
            flag, text = "-s", a[2:]
        if text is not None:
            return f'{flag}"{shorten(text, 30, placeholder="...")}" ({len(text):,} chars)'
        return f'"{shorten(a, chars, placeholder="...")}"' if " " in a else a

    cmd = [Path(sys.argv[0]).name] + [shown(j, a) for j, a in enumerate(words) if j not in gone]
    folder = folder or LOG_DIR
    name = "log" if int(number) == 1 else f"log{int(number)}"
    body = [fill(" ".join(cmd), LOG_WIDTH, subsequent_indent="    "),
            _log_excerpt(">> ", sent, chars), _log_excerpt("<< ", answer, chars),   # sent, received
            f"-> {len(sent)} chars | <- {len(answer)} chars"
            + (" · not complete" if whole is False else "")]
    # log.md: a heading per entry, so Obsidian's outline lists them, and the entry
    # itself in a code block, so nothing from a prompt or an answer is read as
    # Markdown: no #tags, [[links]] or headings from it. The fence is longer than
    # any run of backticks inside, so a ``` in the text cannot end the block early.
    # log.txt (-L): the same lines under a line of dashes, for Word or a plain editor.
    ticks = max((len(run) for run in re.findall(r"`+", "\n".join(body))), default=0)
    fence = "`" * max(3, ticks + 1)
    now = datetime.now()
    day, stamp = f"{now:%Y-%m-%d}", f"{now:%Y-%m-%d %H:%M:%S} · {model}"
    legend = LOG_LEGEND.format(chars=chars, day="`##`", entry="`###`")
    logs = [(folder / f"{name}.md", "### ",
             "> [!info] How to read this log\n"
             + fill(legend, LOG_WIDTH, initial_indent="> ", subsequent_indent="> "),
             f"## {day}", [f"### {stamp}", "", fence + "text", *body, fence])]
    if txt:
        legend = LOG_LEGEND.format(chars=chars, day="A line of ====", entry="a line of ----")
        logs.append((folder / f"{name}.txt", "---- ",
                     "How to read this log\n" + fill(legend.replace("`", ""), LOG_WIDTH),
                     f"==== {day} ".ljust(LOG_WIDTH, "="),
                     [f"---- {stamp} ".ljust(LOG_WIDTH, "-"), *body]))
    try:
        folder.mkdir(parents=True, exist_ok=True)
        for path, mark, legend, day_line, entry in logs:
            _append_log(path, mark, legend, day_line, day, entry)
    except OSError as e:
        print(f"Not logged ({type(e).__name__}): {e}", file=sys.stderr)


def api_error(e: Exception, key: str, model: str) -> str:
    """The message for a failed API call, the same in every script. The SDKs'
    errors for an HTTP status carry status_code and message; network errors
    and timeouts carry neither. key: the variable the key is read from."""
    status = getattr(e, "status_code", None)
    text = getattr(e, "message", None) or str(e)
    if status == 401:
        return f"401: the key was refused. Check what {key} holds."
    if status == 403:
        return f"403: the key may not use {model}: {text}"
    if status == 404:
        return f"404: {text}"
    if status:
        return f"HTTP {status}: {text}"
    return f"No answer from the API ({type(e).__name__}): {text}"


# =============================================================================
# -A: the file name from Mistral (MISTRAL_NAMING)
# =============================================================================

# English words, whatever the language of the prompt.
MISTRAL_NAME_SYSTEM = ("Reply with 3-6 lowercase English words naming the topic of the "
                       "question. No punctuation, no explanation.")


def _check_mistral_key() -> None:
    """-A: the key must be there before the script sends anything."""
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        sys.exit("-A needs MISTRAL_API_KEY for the file name: export it first, or use -a. "
                 "Nothing was sent.")


def _name_from_mistral(text: str) -> str:
    """A short name from MISTRAL_NAME_MODEL, or "" with the reason on the screen.
    The start of the prompt goes to Mistral."""
    try:
        from mistralai.client import Mistral  # as in the scripts
        client = Mistral(api_key=os.environ["MISTRAL_API_KEY"].strip(), timeout_ms=30_000)
        r = client.chat.complete(
            model=MISTRAL_NAME_MODEL, max_tokens=30,
            # Small 4 takes none or high, and what it does without the setting
            # is not documented. The 30 tokens are for the name, not for thinking.
            reasoning_effort="none",
            messages=[{"role": "system", "content": MISTRAL_NAME_SYSTEM},
                      {"role": "user", "content": text[:NAME_CHARS]}])
    except Exception as e:   # no SDK, no network, a refused key: the answer is saved all the same
        reason = getattr(e, "status_code", None) or type(e).__name__
        return _no_name(f"Mistral gave no name ({reason})")
    except KeyboardInterrupt:   # Ctrl-C: the answer is saved all the same
        return _no_name("stopped with Ctrl-C")
    choice = (getattr(r, "choices", None) or [None])[0]
    if getattr(choice, "finish_reason", None) != "stop":   # a cut-off name looks chosen
        return _no_name(f"the name from {MISTRAL_NAME_MODEL} was cut off")
    content = getattr(getattr(choice, "message", None), "content", None) or ""
    if isinstance(content, list):   # chunks, as SDK objects or dicts
        content = "".join((c.get("text") if isinstance(c, dict) else getattr(c, "text", None)) or ""
                          for c in content)
    return _clean_name(content)
