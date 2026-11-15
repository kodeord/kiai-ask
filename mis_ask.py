#!/usr/bin/env python3
# version = "1"
# date = 2026-11-15
#
# Unofficial: not affiliated with or endorsed by Mistral AI. A personal learning
# project, shared as is, without warranty of any kind. It sends your prompts to
# Mistral's API, which may be billed to your own account, and model output can
# be wrong.
# Written and tested on macOS (Apple silicon, zsh) only; not tried on Linux or
# Windows.
# AI helped with parts of this code.

# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 kodeord (https://github.com/kodeord). See the file LICENSE.
"""Sends a prompt to a Mistral model and prints the answer.

It is also meant to help document the use of AI, as many universities ask of
students, sometimes with the prompts themselves: -l keeps a log of each run
(date, model, the command, and the start of the prompt and of the answer), and
-x puts the same facts above a saved answer.

Each run is one request on its own, not a chat: nothing from earlier runs is
kept or sent. The model gets the system prompt (-s), the prompt and any
document piped in, and nothing else.

Needs Python 3.10 or newer, the mistralai package (version 3)
and the folder lib/ with cli_common.py beside this file.

    python3 -m pip install "mistralai>=3,<4"

The key is read from the environment variable MISTRAL_API_KEY. Get a key at
console.mistral.ai; API use may be billed.

Do not paste an API key directly into the code.

A few ways to run it:
- Type ./mis_ and press Tab to autocomplete the name.
- A function in ~/.zshrc makes it shorter still.

Only the answer goes to standard output and the status lines go to the screen, so
> and | pass on the answer alone. The screen says what is sent, and says more
only when the answer is not whole; the model and the tokens are in the YAML (-x).

    # Write the name of the program (+ Enter). Type or paste your prompt. End with Ctrl-D
    ./mis_ask.py

    # Enter your prompt in the command line
    ./mis_ask.py "Do Berliners prefer shopping on Schlossstrasse to shopping at Alexanderplatz?"

    # Save the output to a file
    ./mis_ask.py "How many live in Madrid?" > Madrid.md

    # Create a simple log entry (by appending to the log file)
    ./mis_ask.py "When did Austria join the EU?" -l

    # An instruction + the text of a file
    ./mis_ask.py "Translate this to French" < "Welkom_in_Den_Haag.md"

    # An instruction + the clipboard (macOS; only use if you know the contents of your clipboard)
    pbpaste | ./mis_ask.py "Translate to English"

    # The clipboard can also be the argument (macOS; use -- if the text starts with -)
    ./mis_ask.py "$(pbpaste)"

    # The response from the LLM can also be sent to the clipboard (macOS)
    ./mis_ask.py "Did Telemann pave the way for J. S. Bach in Leipzig?" | pbcopy

    # Save to a file in OUTPUT_DIR, with YAML at top, and more
    ./mis_ask.py -m glm -e 3 -x -o river.md "What is the name of the river in Paris?"

    # System prompt from a file of your own (data/prompts/ is a place for them)
    ./mis_ask.py -s "$(< data/prompts/my_system_prompt.md)" "question"

    # The same question to two models at once, Small and Large (the default).
    # Each answer comes when it is done, so their lines can mix on the screen.
    q="Is The Hague or Amsterdam the capital of the Netherlands?"
    ./mis_ask.py -m small -e 1 "$q" & ./mis_ask.py -e 3 "$q"

Options:
    -m  the model; without -m, DEFAULT_MODEL near the top of this file:
        ml      Mistral Large, the newest: mistral-large-latest, which is
                Large 4 now
        glm     GLM 5.3
        flashg  GLM 5.3 Flash
        flashd  DeepSeek V4.1 Flash, a public preview at Mistral that may
                change or go away at short notice
        small   Mistral Small 4
    -e  one scale for all the scripts here: 1 least, 2 standard (the default),
        3 most. What 1, 2 and 3 send to each model is in MODELS, under Models
        below; -h shows it too. The names low, medium, high and none work too,
        where the model takes them
    -s  (--system) a system prompt, as text; from a file:
        -s "$(< my_system_prompt.md)"
    -u  (--user) the prompt from a file (UTF-8 text) in place of the argument,
        e.g. -u my_prompt.md. Text piped in is then the document
        it applies to
    -t  show the model's thinking on the screen, never in the answer on
        standard output. With -o, -a or -A it is saved too, folded under
        the answer
    -y  (--yes) send a large prompt without asking; otherwise a prompt over
        ASK_ABOVE_PROMPT_CHARS characters, the system prompt included, asks
        y/n first
    -x  (--yaml) put YAML frontmatter above the answer (Obsidian shows it as
        properties): date, model, effort, status, tokens, and the start of the
        prompt and of the system prompt. With -u also the prompt file and its
        SHA-256, and with a document piped in, its SHA-256 (as shasum -a 256
        FILE gives it).
        Without -x, the answer alone. Write --yaml with two dashes: -yaml with
        one is read as -y -a ... and stops with an error
    -o  save the answer as FILENAME in OUTPUT_DIR (see Settings) as well as
        printing it. .md is added when FILENAME has no suffix; a name with a
        folder in it (./answer.md) is used as written. An existing file is
        never overwritten: the answer goes to FILENAME_2, FILENAME_3 ...
        beside it
    -a  save it in OUTPUT_DIR, named by the local Ollama model (LOCAL_MODEL in
        lib/cli_common.py) in the language of the prompt. If Ollama does not
        answer, the file gets date and time only
    -A  as -a, but named in English by Mistral Small (MISTRAL_API_KEY); the
        start of the prompt goes to Mistral
    -q  (--quiet) with -o, -a or -A: save the answer without printing it
    -l  (--log) add the date and the model that answered, the command, the
        first LOG_CHARS characters of the prompt (>>) and of the answer
        (<<), and the length of each (-> and <-), to log.md in LOG_DIR
        (see Settings). Only the log is cut: the model gets the whole prompt.
        -l 2 logs to log2.md, -l 3 to log3.md and so on; -l and -l 1 to
        log.md. A number right after -l belongs to -l, not to the prompt
    -L  (--log-txt) as -l, and the same entry as plain text in log.txt
        (log2.txt with -L 2 ...), to paste into Word or read in a plain
        editor. -l and -L together log once, to both files
    --max  the cap on the reply in tokens, thinking included: MAX_TOKENS
        unless given. A cut-off answer says on the screen which limit it hit
    -p  (--preset) options typed often, by number: -p 1 (or -p1) is read as
        the options listed for 1 in lib/cli_common.py. 1 to 3 (PRESETS) are
        the same in all the ask scripts, and 4 and 5 (SCRIPT_PRESETS) choose
        this script's model; -h shows what each number stands for. An
        option after -p overrides it, and -l logs the options, not -p

Quote the prompt: zsh reads ? and * in it as file patterns. Typed prompts end
with Ctrl-D on a new line (Windows: Ctrl-Z, then Enter). One request, no retries.
Ctrl-C stops a run; a request that was already sent may still be billed.

Where standard input is /dev/null (cron, CI, a background job in a shell
script), the argument is the whole prompt. An empty pipe or file still stops
the run, as the command that was to fill it may have failed.

Exit status: 0 a whole answer, 1 nothing sent, the call failed or the answer
could not be saved, 2 wrong arguments, 3 an answer that is not whole (cut off
or empty).
"""

# =============================================================================
# Imports and requirements
# =============================================================================

import argparse
import os
import sys
import typing
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# The three requirements in the docstring are checked here. A missing one stops
# the script with one line that says what to do, not with a traceback.

# 1. Python.
if sys.version_info < (3, 10):
    sys.exit(f"{Path(__file__).name} needs Python 3.10 or newer; this is {sys.version.split()[0]}.")

# 2. mistralai, Mistral's SDK (software development kit: the package that talks to
#    Mistral's API for this script).
try:
    from mistralai.client import Mistral
except ImportError:
    sys.exit(f'{Path(__file__).name} needs the mistralai package, version 3: '
             'python3 -m pip install "mistralai>=3,<4"')

# 3. lib/cli_common.py, beside this script. It holds what the scripts share: the
#    common options, saving (-o, -a, -A), reading the prompt, the y/n question,
#    the YAML header and the last step, which prints and saves the answer.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
try:
    from cli_common import (
        add_common_options,
        api_error,
        confirm_send,
        finish,
        frontmatter,
        log_run,
        one_line,
        option_groups,
        parse_common_args,
        prepare_save,
        read_prompt,
        split_think,
    )
except ModuleNotFoundError as e:
    if e.name != "cli_common":
        raise   # lib/ is there but lacks a module it needs: show that error as it is
    sys.exit("lib/cli_common.py is missing: keep the folder lib/ beside this file.")


# =============================================================================
# Settings
# =============================================================================

# The model used when -m is not given: a name from MODELS (ml, glm ...) or its
# model id (mistral-large-latest ...). A model that is not in MODELS needs a line there.
DEFAULT_MODEL = "ml"
MAX_TOKENS = 12_000          # one reply, thinking included; --max overrides it
# Ask y/n above this many characters in the prompt, the system prompt included.
ASK_ABOVE_PROMPT_CHARS = 3_000
# How many characters of the prompt and of the answer -l writes to the log.
LOG_CHARS = 240
# Where -l writes the log: data/ beside this script, with log.md (-l, -l 1),
# log2.md (-l 2) and so on. Any path works; it is made if needed.
LOG_DIR = Path(__file__).resolve().parent / "data"
# Where -o, -a and -A save the answers: data/answers beside this script. Any path
# works, e.g. Path.cwd() for the folder you run the script from; it is made if needed.
OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "answers"


# =============================================================================
# Models
# =============================================================================

class Model(NamedTuple):
    id: str          # the model id at Mistral
    efforts: list    # the effort names it takes
    scale: tuple     # what -e 1, 2 and 3 send; None means no effort is sent


# One line per model: Model(model id at Mistral, [effort names it accepts],
# (what -e 1, 2 and 3 send)). The list in [] is used to check a name, and its first
# name must be the lowest level: the hint after a cut-off answer suggests a lower
# -e only above it. The tuple in () follows -e 1, 2, 3 (each name in it must also
# be in []). Without -e the script uses -e 2, and None sends no effort.
# Mistral's pages:
#   models, with deprecations  https://docs.mistral.ai/models
#   changelog                  https://docs.mistral.ai/resources/changelogs
MODELS = {
    # Mistral Large, the newest: mistral-large-latest moves on when Mistral releases
    # a new Large. Now it is Large 4 (mistral-large-4 and mistral-large-4-0 are the
    # same model), so the efforts here are Large 4's; check them when it moves.
    # Large 4 always thinks. It accepts low, medium and high, and uses high when no
    # effort is sent. The preview's none is now low, and Mistral calls medium the
    # level for everyday tasks.
    "ml":     Model("mistral-large-latest", ["low", "medium", "high"], ("low", "medium", "high")),
    # GLM 5.3 always thinks. Mistral also takes max; this script stops at high.
    "glm":    Model("zai-glm-5-3",          ["low", "high"],           ("low", "high", "high")),
    # GLM 5.3 Flash works like glm. Mistral and Z.ai list low, high and max, and
    # Z.ai uses max when no effort is sent.
    "flashg": Model("zai-glm-5-3-flash",    ["low", "high"],           ("low", "high", "high")),
    # DeepSeek V4.1 Flash is a public preview at Mistral, so its id and behaviour
    # may change, or it may disappear, at short notice.
    "flashd": Model("deepseek-v4-1-flash-1017", ["low", "high"],       ("low", "high", "high")),
    # Mistral Small 4 thinks first only at high.
    "small":  Model("mistral-small-latest", ["none", "high"],          ("none", "high", "high")),
}


# =============================================================================
# Command line
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a prompt to a Mistral model.",
                                     allow_abbrev=False)
    parser.add_argument("prompt", nargs="*",
                        help="the prompt, or the instruction for piped text; quote it, "
                             "as zsh reads ? and * as file patterns")
    groups = option_groups(parser)   # the groups -h shows: model, prompt, answer
    model = groups["model"]
    model.add_argument("-m", "--model", choices=MODELS, default=DEFAULT_MODEL,
                       help=f"ml Mistral Large (now Large 4), glm GLM 5.3, flashg GLM 5.3 "
                            f"Flash, flashd DeepSeek V4.1 Flash (a preview at Mistral, may "
                            f"change soon), small Small 4; default {DEFAULT_MODEL}")
    # Built from MODELS, so the help always shows what -e 1, 2 and 3 send.
    sent = ", ".join(f"{name} {'/'.join(s or '-' for s in m.scale)}" for name, m in MODELS.items())
    model.add_argument("-e", "--effort", choices=["1", "2", "3", "high", "medium", "low", "none"],
                       default="2",
                       help=f"1 least, 2 standard (default), 3 most; sent as {sent}; "
                            f"the names are sent as given, where the model takes them")
    # The options the ask scripts share: -t, --max, -u, -s, -y, -o, -a, -A, -q, -x,
    # -l, -L and --version, and -p when lib has presets.
    add_common_options(
        parser, __file__, groups=groups, ask_above=ASK_ABOVE_PROMPT_CHARS, log_chars=LOG_CHARS,
        log_dir=LOG_DIR,
        thinking_help="show the model's thinking on the screen (stderr); "
                      "with -o, -a or -A also saved in the file",
        yaml_fields="date, model, effort, status, tokens, prompt, system prompt, "
                    "-u file and SHA-256, document SHA-256",
        max_help=f"cap on the reply in tokens, thinking included (default {MAX_TOKENS:,})")
    return parser


# =============================================================================
# Helpers: the SDK's effort names and the reply's content
# =============================================================================

def _literals(t) -> list:
    """Every string literal in a (nested) Union/Literal type."""
    out = []
    for a in typing.get_args(t):
        out += [a] if isinstance(a, str) else _literals(a)
    return out


def _get(obj, name):
    """A field of a chunk, whether the chunk is an SDK object or a plain dict."""
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def flat(content) -> str:
    """The text in content: the string itself, or the text chunks of a list.
    A chunk of another type is left out, even if it has text of its own."""
    if isinstance(content, list):
        return "".join(_get(c, "text") or "" for c in content
                       if _get(c, "type") in ("text", None))
    return content or ""


def read_content(content) -> tuple[str, str]:
    """The answer and the thinking in a reply's content. Only text chunks are
    the answer. The thinking comes as chunks of its own, or first in the text
    as <think>...</think>, which split_think() takes out."""
    answer = flat(content).strip()
    thinking = []
    if isinstance(content, list):
        thinking = [flat(_get(c, "thinking")).strip() for c in content
                    if _get(c, "type") == "thinking"]
    answer, inline = split_think(answer)
    return answer, "\n\n".join(t for t in thinking + [inline] if t)


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    # --- Options, model and effort -------------------------------------------
    parser = build_parser()
    args = parse_common_args(parser)   # also checks that --max is at least 1
    cap = MAX_TOKENS if args.max is None else args.max   # --max overrides the cap for this run
    # DEFAULT_MODEL may hold a model id instead of a name; use the name in MODELS.
    args.model = {m.id: name for name, m in MODELS.items()}.get(args.model, args.model)
    if args.model not in MODELS:
        parser.error(f"DEFAULT_MODEL = {DEFAULT_MODEL!r} is not a name or model id "
                     f"in MODELS; add a line there")
    model = MODELS[args.model]
    levels = model.efforts
    scaled = args.effort in ("1", "2", "3")
    if scaled:
        effort = model.scale[int(args.effort) - 1]
        if effort is None and args.effort != "2":
            print(f"Note: {model.id} has no effort setting; -e {args.effort} sends nothing.",
                  file=sys.stderr)
    elif args.effort not in levels:
        parser.error(f"-e {args.effort}: {model.id} takes "
                     + (f"-e 1, 2, 3, {' or '.join(levels)}" if levels
                        else "no effort; -e 1-3 send nothing"))
    else:
        effort = args.effort

    # An effort level that is not understood can be dropped without a word, and the
    # model then answers at its own default. That is why the effort is checked
    # before anything is sent.
    if effort:
        try:
            from mistralai.client.models import ReasoningEffort as _RE
            known = _literals(_RE)
        except ImportError:
            known = []
        if effort not in known:
            sys.exit(f"The installed mistralai does not list effort {effort!r}, so it could be "
                     f"dropped without a word. Upgrade mistralai. Nothing was sent.")

    timeout_ms = 300_000 if effort not in (None, "none") else 100_000   # thinking takes longer
    # A higher --max gets more time, in proportion.
    timeout_ms = int(timeout_ms * max(1, cap / MAX_TOKENS))

    # --- Key, prompt and checks before sending -------------------------------
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        sys.exit("MISTRAL_API_KEY is not set: export MISTRAL_API_KEY=... in this terminal first.")
    # The argument or the -u file, if any, is the instruction, and text piped in is
    # the document it applies to. With neither, the prompt is read from the keyboard
    # (typed or pasted, ended with Ctrl-D).
    instruction, document, user_prompt, system_prompt, document_sha256 = read_prompt(
        args.words, args.system)   # args.words: with -u, the file's text (lib reads it)
    # Plain dicts, which the SDK accepts. typing.Any stops a type checker from holding
    # them to the SDK's own, stricter message types.
    messages: list[typing.Any] = (
        ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        + [{"role": "user", "content": user_prompt}])

    # -o, -a and -A are checked before anything is sent, so nothing is sent in vain.
    save_target = prepare_save(args, OUTPUT_DIR)

    # Ask y/n before a large prompt. The question goes to the keyboard, because
    # standard input may hold the document.
    chars = len(system_prompt) + len(user_prompt)
    if chars > ASK_ABOVE_PROMPT_CHARS and not args.yes:
        confirm_send(chars, model.id)

    # --- Send ----------------------------------------------------------------
    # The SDK does not retry by default, so one run sends at most one request.
    client = Mistral(api_key=key, timeout_ms=timeout_ms)

    print(f"\nSending {len(user_prompt):,} chars to {model.id} (effort {effort or '-'}"
          + (f" from -e {args.effort}" if scaled else "")
          + (f", system prompt {len(system_prompt):,}" if system_prompt else "")
          + (f", cap {cap:,}" if args.max else "") + ")...",
          file=sys.stderr)
    # reasoning_effort is sent only when there is an effort. typing.Any, because a type
    # checker cannot tell which parameter each key in ** goes to, so it checks them all.
    effort_arg: dict[str, typing.Any] = {"reasoning_effort": effort} if effort else {}
    try:
        response = client.chat.complete(
            model=model.id,
            max_tokens=cap,
            messages=messages,
            **effort_arg,
        )
    except KeyboardInterrupt:   # Ctrl-C while waiting: one line, not a traceback
        sys.exit("\nStopped while waiting for the answer. The request may still be billed.")
    except Exception as e:   # api_error() words it the same way in every script
        sys.exit(api_error(e, "MISTRAL_API_KEY", model.id))

    # --- The reply and the status lines --------------------------------------
    choice = (response.choices or [None])[0]
    if choice is None:
        sys.exit(f"{model.id} returned no answer (no choices), though the request may have "
                 f"been billed.")
    answer, thinking = read_content(choice.message.content if choice.message else None)

    # Status lines go to the screen (stderr); only the answer goes to stdout. They
    # come only when something needs saying: an answer that is not whole, and why.
    # The model, the tokens and the rest are in the YAML (-x).
    whole = choice.finish_reason == "stop" and bool(answer)
    if not whole:
        print(f"Finish reason: {choice.finish_reason}  <- not a whole answer", file=sys.stderr)
    # If the answer was cut off, say which limit it hit and what helps.
    if choice.finish_reason == "length":
        print(f"Hint:          the cap of {cap:,} tokens was reached, thinking included.\n"
              f"               --max {2 * cap} raises it"
              + ("; a lower -e also helps, as the thinking spends the same budget"
                 if effort not in (None, model.efforts[0]) else "") + ".", file=sys.stderr)
    elif choice.finish_reason == "model_length":
        print("Hint:          the model's own limit (its context length) was reached.\n"
              "               --max cannot raise it; shorten the text.", file=sys.stderr)

    # Token counts as Mistral reports them, for the YAML (-x). Without them (usage is
    # None), they are left out rather than fail.
    usage = response.usage
    tokens_in = getattr(usage, "prompt_tokens", None)
    tokens_out = getattr(usage, "completion_tokens", None)
    details = (getattr(usage, "model_extra", None) or {}).get("completion_tokens_details")
    thinking_tokens = (details.get("reasoning_tokens") if isinstance(details, dict)
                       else getattr(details, "reasoning_tokens", None))

    # If effort was sent but no thinking came back, say so; with -t, show the
    # thinking itself.
    if effort not in (None, "none") and not thinking and not thinking_tokens:
        print(f"Note:          effort {effort} was sent, but no thinking came back",
              file=sys.stderr)
    print(file=sys.stderr)
    if args.thinking:
        print(f"--- thinking, {len(thinking):,} chars ---\n{thinking}\n"
              f"--- end of thinking ---\n"
              if thinking else "(no thinking came back with this answer)\n", file=sys.stderr)

    # --- The answer: header, screen, file and log ----------------------------
    # With -x, YAML frontmatter goes above the answer, on screen and in a saved file.
    header = frontmatter({
        "generated": datetime.now(),
        "tool": Path(__file__).name,
        "model": response.model,
        "effort": effort,
        "effort_scale": args.effort if scaled else None,
        "system_prompt": one_line(system_prompt),
        "prompt": one_line(instruction or user_prompt),
        "prompt_file": args.user,
        "prompt_sha256": args.prompt_sha256,
        "document_chars": len(document) if document and instruction else None,
        "document_sha256": document_sha256,
        "finish_reason": choice.finish_reason,
        "complete": whole,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "reasoning_tokens": thinking_tokens,
    }) if args.yaml else ""
    # Print and save the answer, and get the exit status.
    code = finish(args, save_target, header, answer, whole, choice.finish_reason, thinking,
                  user_prompt)
    if args.log:   # -l: add one entry to the log now that the answer is out
        log_run(response.model, args.prompt, user_prompt, answer, LOG_CHARS, args.log, LOG_DIR,
                whole=whole, txt=args.log_txt)
    return code


if __name__ == "__main__":
    sys.exit(main())
