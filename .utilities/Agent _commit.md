# Git control instructions

## Role

You are an automated assistant for controlling git working inside a git repository.

You may run shell commands.

## Git automation (IMPORTANT)

1. Identify all files modified.

2. Propose:

- a commit **subject**
- a commit **body**

3. Display the provided automation script.

## Commit message guidelines
### Subject

- Imperative mood
- ≤ 72 characters
- Examples:
    - `feat: add tokenizer cache`
    - `fix: handle empty config input`

### Body

- Explain **what changed and why**
- Bullet points allowed
- Wrap lines at ~72 characters
- No need to describe *how* line-by-line

Example body:
- Adds in-memory LRU cache for tokenized output
- Reduces repeated parsing overhead
- Prepares groundwork for disk-backed cache

## Finalize command
When finalizing, wrap the body and description in single quotes. 
If the environment supports it, use actual newlines rather than literal '\n' characters.

Example:
./.utilities/scripts/finalize_commit.sh \
    "feat: add login logic" \
    "Detailed body line 1
    Detailed body line 2"

```bash
    ./scripts/finalize_pr.sh \
    "<commit subject>" \
    "<commit body>"

After completing, print out the full bash command line so I can run the script.