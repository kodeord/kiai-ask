# mis_ask

A small command-line tool for asking a model at Mistral from the terminal, one
request at a time. It sends a prompt and prints the answer.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: GPL-3.0-only](https://img.shields.io/badge/license-GPL--3.0--only-blue)
![Status: learning project](https://img.shields.io/badge/status-learning%20project-lightgrey)

> **Unofficial.** A personal learning project, not affiliated with or endorsed
> by Mistral AI or any other provider. Shared as is, without warranty of any
> kind (see [LICENSE](LICENSE)). The script sends your prompts to Mistral's
> API, which may be billed to your own account, and model output can be wrong.
> Do not send confidential documents or personal data you are not allowed to
> share.

| File | What it is |
|---|---|
| `mis_ask.py` | the script: asks Mistral Large, GLM 5.3, GLM 5.3 Flash, DeepSeek V4.1 Flash or Mistral Small |
| `lib/cli_common.py` | what the script leans on: the common options, reading the prompt, the y/n question, saving, the YAML header, the log and the error messages |

Only the answer goes to standard output. The status lines and the model's
thinking (`-t`) go to the screen (standard error), so `>` and `|` pass on the
answer alone. The screen says what is sent, and says more only when the answer
is not whole: why, and what helps. The model and the token counts are in the
YAML header (`-x`).

## Made for study: one request at a time, not a chat

Each run is one request on its own. Nothing from earlier runs is kept or sent:
the model gets the system prompt (`-s`), your prompt and any document piped in,
and nothing else.

That adds a little friction on purpose. In a chat window it is easy to let the
conversation do the thinking, nudging the model along one follow-up at a time.
With no conversation to lean on, you work out what you are asking, and which
text belongs with it, before you press Enter. A prompt over 3,000 characters
also stops to ask y/n first, and `-e` puts the choice of how much the model
should think on the command line.

The tool is also meant to help document the use of AI, as many universities
ask of students. `-l` logs each run as it happens: the date, the model, the
command, and the start of the prompt and of the answer. `-x` puts the same
facts as YAML frontmatter above the answer, which Obsidian shows as
properties, with the SHA-256 of a document piped in and of a prompt file
(`-u`), so you can always see, and show, what was sent and what came back.
Notes of your own can go in `data/log.md` as plain text under an entry, so the
question, the answer and what you made of it stand together; just do not start
a line of a note with ```` ``` ````, `## ` or `### `, which the log uses for
itself.

## Requirements

- Python 3.10 or newer
- the folder `lib/` with `cli_common.py` beside `mis_ask.py`
- the `mistralai` package, version 3
- your own API key from [console.mistral.ai](https://console.mistral.ai) (API
  use may be billed)
- only for `-a`: [Ollama](https://ollama.com), running, with a local model
  (see [Naming saved answers](#naming-saved-answers)); without it,
  `-a` names the file by the date and time

`lib/cli_common.py` needs nothing beyond the standard library.

Written and tested on macOS (Apple silicon) with Python 3.13, `mistralai` 3.7
and Ollama 0.40.1. It has not been tried on Linux or Windows: the commands for
bash and PowerShell below are given as a help, untested.

Make a virtual environment and install the package:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install "mistralai>=3,<4"
```

On Windows: `.venv\Scripts\pip install "mistralai>=3,<4"`.

## The API key

At [console.mistral.ai](https://console.mistral.ai), choose a plan first:
Experiment (free, with low limits) or Scale (paid by use). Then make a key
under API Keys. On the Experiment plan, Mistral may use what you send through
the API to train its models, unless you turn that off under Admin → Privacy.

The script reads the key from the environment variable `MISTRAL_API_KEY`.
Never put the key in the code.

## Running it

With the Python of the virtual environment, from the folder the script is in:

```bash
.venv/bin/python mis_ask.py "How many live in Madrid?"
```

On Windows: `.venv\Scripts\python mis_ask.py "How many live in Madrid?"`.

The examples below use `./mis_ask.py`. That works once the script is
executable (`chmod +x mis_ask.py`) and the virtual environment is active
(`source .venv/bin/activate`).

To run it from any folder without activating anything, add a function like
this to `~/.zshrc` or `~/.bashrc`, with the path to your copy:

```bash
mis() { /path/to/repo/.venv/bin/python /path/to/repo/mis_ask.py "$@"; }
```

Then `mis "How many live in Madrid?"` works anywhere. Saved answers and logs
still go to `data/` beside the script.

## The models

| `-m` | Model at Mistral | `-e 1` | `-e 2` | `-e 3` |
|---|---|---|---|---|
| `ml` (default) | `mistral-large-latest` (Mistral Large, now Large 4) | low | medium | high |
| `glm` | `zai-glm-5-3` (GLM 5.3) | low | high | high |
| `flashg` | `zai-glm-5-3-flash` (GLM 5.3 Flash) | low | high | high |
| `flashd` | `deepseek-v4-1-flash-1017` (DeepSeek V4.1 Flash) | low | high | high |
| `small` | `mistral-small-latest` (Mistral Small 4) | none | high | high |

`mistral-large-latest` is the newest Mistral Large: it moves on when Mistral
releases a new one. It is Large 4 now, and the efforts above are Large 4's.
DeepSeek V4.1 Flash is a public preview at Mistral, so it may change or go
away at short notice. Not every account may have every model; an error from
the API says so.

Before anything is sent, the effort is checked against the installed
`mistralai` package, so a level the package does not know is never dropped
without a word.

## Examples

The argument is the prompt:

```bash
./mis_ask.py "How many live in Madrid?"
```

An instruction, and the text of a file as the document it applies to:

```bash
./mis_ask.py "Translate this to French" < notes.md
```

An instruction and the clipboard (macOS; only when you know what the clipboard
holds):

```bash
pbpaste | ./mis_ask.py "Translate to English"
```

No argument: type or paste the prompt, and end it with Ctrl-D on a new line
(Windows: Ctrl-Z, then Enter):

```bash
./mis_ask.py
```

Save the answer, with nothing else in the file:

```bash
./mis_ask.py "How many live in Madrid?" > madrid.md
```

Save it as `data/answers/river.md` as well, with YAML frontmatter on top, from
GLM 5.3 at the most effort:

```bash
./mis_ask.py -m glm -e 3 -x -o river "What is the name of the river in Paris?"
```

An instruction kept in a file (`-u`), applied to a document piped in:

```bash
./mis_ask.py -u summarise.md < draft.md
```

A system prompt from a file:

```bash
./mis_ask.py -s "$(< my_system_prompt.md)" "What should I see in Lisbon?"
```

Add an entry for the run to `data/log.md`:

```bash
./mis_ask.py "When did Austria join the EU?" -l
```

Show the model's thinking on the screen (it never goes to standard output):

```bash
./mis_ask.py -t "Did Telemann pave the way for J. S. Bach in Leipzig?"
```

Quote the prompt: zsh reads `?` and `*` in it as file patterns. A prompt that
starts with `-` needs `--` before it.

## Options

`-h` lists them all, with the models and what each effort level sends.

| Option | What it does |
|---|---|
| `-m NAME` | the model: `ml` (default), `glm`, `flashg`, `flashd` or `small`; see [The models](#the-models) |
| `-e N` | the effort: `1` least, `2` standard (the default), `3` most; what each number sends to each model is in the table above. The names the model takes (`none`, `low`, `medium`, `high`) work too |
| `-s TEXT` | a system prompt; from a file: `-s "$(< file.md)"` |
| `-u FILE` | the prompt from a file, in place of the argument; text piped in is then the document |
| `-t` | show the model's thinking on the screen; with `-o`, `-a` or `-A` it is saved too, folded under the answer |
| `-y` | send without asking, also above 3,000 characters (the system prompt included) |
| `-x` | YAML frontmatter above the answer: date, model, effort, status, tokens, and the start of the prompt and of the system prompt; with `-u` also the prompt file and its SHA-256, and with a document piped in, its SHA-256. Write `--yaml` with two dashes: `-yaml` is read as `-y -a …` |
| `-o NAME` | save the answer as `data/answers/NAME` too (`.md` added when `NAME` has no suffix; a name with a folder in it is used as written) |
| `-a` | save it in `data/answers`, named by a local model in Ollama; see [Naming saved answers](#naming-saved-answers) |
| `-A` | as `-a`, but named in English by Mistral Small, in one more (small) API call; the start of the prompt goes to Mistral |
| `-q` | with `-o`, `-a` or `-A`: save the answer without printing it |
| `-l [N]` | add an entry to `data/log.md` (`-l 2`: `log2.md`, and so on): the date and model, the command, the first 240 characters of the prompt and of the answer, and their lengths |
| `-L [N]` | as `-l`, and the same entry as plain text in `data/log.txt`, to paste into Word or read in a plain editor |
| `--max N` | the cap on the reply in tokens, thinking included: 12,000 unless given |
| `-p N` | options typed often, by number, set in `lib/cli_common.py` and shown by `-h`: `-p 1` the most thinking (`-e 3`), `-p 2` a documented run (`-l -x`), `-p 3` both, `-p 4` Mistral Small at the least thinking, `-p 5` Mistral Large at the most. An option after `-p` overrides it, and `-l` logs the options, not `-p` |
| `--version` | the script's version and date |

An existing file is never overwritten: the answer goes to `NAME_2`, `NAME_3` …
beside it.

## Naming saved answers

`-a` asks a local model in Ollama for a short file name, in the language of the
prompt. For the name, the prompt goes only to Ollama (at `localhost:11434`, or
where `OLLAMA_HOST` points, if that is this machine). The model is
`gemma4:12b-mlx`, which runs only on Apple silicon. To use another model you
have installed (`ollama list`) without changing the code, set
`LOCAL_MODEL_CLI_COMMON` in `~/.zshrc` or `~/.bashrc`:

```bash
export LOCAL_MODEL_CLI_COMMON=gemma4:12b
```

If Ollama does not answer, or does not have the model, the answer is saved all
the same, named by the date and time.

`-A` asks Mistral Small instead, which names the file in English. That is one
more API call on your account, a small one: it uses the same
`MISTRAL_API_KEY`, and the first 2,000 characters of the prompt go to Mistral.

## How it works

- **One request, no retries.** The script waits a fixed time for the answer,
  depending on the effort, and longer with a higher `--max`.
  Ctrl-C stops a run; a request that was already sent may still be billed.
- **Instruction and document.** With text piped in, the argument is the
  instruction, and the two are sent as the instruction, a line `---`, and the
  document. An empty pipe or file stops the run with nothing sent, as the
  command that was to fill it may have failed. Where standard input is
  `/dev/null` (cron, CI, a background job in a shell script), nothing is piped
  in and the argument is the whole prompt.
- **A question before large prompts.** Above 3,000 characters, the system
  prompt included, the script asks y/n on the keyboard first; `-y` skips the
  question. Windows has no terminal to ask in, so add `-y` there for large
  prompts.
- **Checked before anything is sent.** The key, the options, the effort and
  whether an answer can be saved where `-o`, `-a` or `-A` would put it, so a
  request is never paid for in vain. If saving fails after all (a full disk),
  an answer held back by `-q` is printed instead, so it is not lost.
- **Plain messages.** A Python version that is too old, a missing package, a
  missing `lib/` folder or a missing key stops the script with a sentence that
  says what to do, not a traceback.

`lib/cli_common.py` holds the shared parts, written so that more scripts for
other providers can use them and behave the same.

## Privacy and cost

- Everything `mis_ask.py` sends goes to Mistral's API and counts against your
  account.
- On Mistral's free Experiment plan, what you send may be used to train
  Mistral's models unless you turn it off (see [The API key](#the-api-key)).
- With `-A`, the start of the prompt also goes to Mistral Small, which names
  the file, in one more API call. With `-a`, the file is named by the local
  model in Ollama, and the prompt does not leave the machine for that.
- `-l` writes the start of your prompts and answers to `data/`, and `-o`, `-a`
  and `-A` save the answers there (with `-x`, the start of the prompt too).
  Keep them out of git; the `.gitignore` here does.
- Do not send confidential documents or personal data you are not allowed to
  share.

## Exit status

| Code | Meaning |
|---|---|
| `0` | a whole answer |
| `1` | nothing was sent, the call failed, or the answer could not be saved |
| `2` | wrong arguments |
| `3` | an answer that is not whole (cut off or empty) |

## Layout

```text
mis_ask.py            ask a Mistral model
lib/cli_common.py     what the script leans on: the common options, reading the
                      prompt, the y/n question, saving, the YAML header and the log
data/answers/         answers saved with -o, -a and -A (made when needed)
data/log*.md, *.txt   the logs from -l and -L (made when needed)
data/prompts/         a place for prompt files of your own, for -s and -u
```

## Acknowledgments

The use of command-line arguments in this project was partly inspired by:

Youens-Clark, K. (2020). *Tiny Python projects: Learn coding and testing with puzzles and games*. Manning Publications.

## AI assistance

The first versions were my own work. Later I used an AI coding assistant
(Claude, by Anthropic) to review, restructure and document the code, and to
help add features. I reviewed and tested the changes myself. Like the rest of
the project, it is provided as is; see the disclaimer above.

## License

[GPL-3.0-only](LICENSE) © 2026 [kodeord](https://github.com/kodeord)

You may use, study, change and share the code. If you pass on copies, changed
or not, they come under the same licence, with the source and with the
copyright and licence notices kept. There is no warranty: see the disclaimer
at the top, and sections 15 and 16 of the licence.
