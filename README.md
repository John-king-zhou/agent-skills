# agent-skills

This repo stores my personal skills for coding agents. A skill is a folder with a
`SKILL.md` file. The file tells an agent how to do one kind of task. Claude Code reads
skills from `~/.claude/skills`. Other agents read them from `~/.agents/skills`.

## What is in the repo

| Path | Content |
|---|---|
| `skills/` | Global skills. One folder per skill. |
| `project-skills/MicroGen/` | Skills for the MicroGen project only. Not installed globally. |
| `project-skills/Plasmid_replicator_model/` | Skills for the plasmid replicator model project only. Not installed globally. |
| `install.sh` | Links every folder in `skills/` into the agent skill folders. |

## Skills

My own skills:

- **ste-chat-style**: Chat style for every conversation. It uses 80% ASD-STE100 (Simplified Technical English, relaxed slightly), defines each new term once, and prefers plain words.
- **ste-readme**: Style and format for README and findings files, with captioned figures. A findings file also follows `wait-what`.
- **wait-what**: User-only skill. It re-pitches the last message with context, STE, and terms from `GLOSSARY.md`.
- **karpathy-guidelines**: Rules that keep code changes small and verifiable.

Skills from other authors (see each folder for its license):

- **archify**: Architecture and workflow diagrams as HTML.
- **ce-doc-review**: Review of plans and specs.
- **convert-md-to-pdf**: Markdown to styled PDF. Source: `digital-stoic-org/agent-skills`.
- **find-skills**: Find and install more skills.
- **math-reasoning**: Math derivations and proofs for papers.
- **scientific-writing**: Drafts and audits of scientific manuscripts.

Project skills:

- **MicroGen/progress-review**: Summary of one part of the MicroGen project, with next steps. Copy it into the project at `.claude/skills/progress-review`.
- **Plasmid_replicator_model/fit-logistic-exponential**: Fit selected plasmid or gene abundance time series with the project's logistic plus exponential boost model, or pure logistic when requested. Copy the full folder into the project at `.agents/skills/fit-logistic-exponential`. It requires the project's benchmark code and the `replicator-jax` environment. Use a copy because the helper resolves the project root from its own file location.

## Set up a new machine

1. Clone the repo, for example into `~/ai-skills/agent-skills`.
2. Run `./install.sh`. It makes one symbolic link per skill. It skips any skill that already exists.
3. Run `./install.sh --force` to replace existing skills. The script first renames each old copy to `<name>.bak.<timestamp>`.
4. Run `./install.sh /some/other/skills/dir` to link into a different folder.

Because the folders are links, an edit in `~/.claude/skills/<name>` changes the file in this repo. Commit and push to share the change.

## Make ste-chat-style start automatically

A skill does not start by itself. A SessionStart hook (a command that Claude Code runs when a conversation starts) loads `ste-chat-style` every time. Add this to `~/.claude/settings.json`. Merge it with any `hooks` block that already exists.

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "sed '1,/^---$/d' \"$HOME/.claude/skills/ste-chat-style/SKILL.md\" | jq -Rs '{hookSpecificOutput: {hookEventName: \"SessionStart\", additionalContext: (\"The ste-chat-style skill is always on. Follow it in every reply:\\n\\n\" + .)}}'",
          "statusMessage": "Loading ste-chat-style"
        }
      ]
    }
  ]
}
```

The hook needs `jq`. Restart Claude Code after the change.

## Known problems

- The skills do not set up other agents' hooks. Only Claude Code runs the hook above.
- `wait-what` expects a `GLOSSARY.md` in the project. `ste-readme` tells the agent what to do when no glossary exists: use one name per concept and define it once.
- `archify` is 16 MB because it ships test files and rendered examples.
- Skills that the Claude app syncs (in `~/.claude/skills/synced`) and plugin skills (such as superpowers) are not stored here.
