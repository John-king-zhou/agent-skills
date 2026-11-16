---
name: progress-review
description: Review one part of the MicroGen project that the user names (for example the model_plan folder), summarize a topic they choose, and give next steps. The reply has a glossary on top and never uses project codes (such as A-05) without a plain-words explanation. It calls the global wait-what skill to write the reply. Use when the user types /progress-review or says they lost track of a part of the project.
---

# progress-review

The user lost the thread on one part of the project. Your job is to re-orient them.

The user's request follows the skill name. It names the part to review, the topic to summarize, and any extra wishes. Example: "review the model_plan folder, summarize the training decisions, and give me next steps."

Request: $ARGUMENTS

If the request names no part of the project, ask one short question. Do not guess.

## Steps

1. Find the named part. Read the files in it. For a folder, read every Markdown file first, then the files they point to. Use `git log` and `git status` for that path to see what changed recently.
2. Check claims against the repository. If a plan says a script or test exists, confirm that it exists. Mark each claim as "done", "in progress", "planned", or "not found".
3. Collect every technical term you plan to use, including project-specific names, decision identifiers, and script names.
4. Call the global `wait-what` skill (at `~/.claude/skills/wait-what`) to write the reply. This is a required step, not a hint. Use the Skill tool with `skill: "wait-what"`. If the tool refuses because the skill is user-only, read `~/.claude/skills/wait-what/SKILL.md` and follow it as written. Do not recreate or copy that skill into this project.
5. Write the reply in the format below. The `wait-what` rules (context first, Simplified Technical English, terms from `GLOSSARY.md`) and the format below both apply. If they conflict, the format below wins.

## Reply format

Use this order. Do not add other sections.

### 1. Glossary (on top)

- One line per technical term, in alphabetical order.
- Each line gives the full term and a plain definition of 25 words or fewer.
- Include project terms (for example the names of experiments, gates, or arms) and field terms.
- Define a term here even if the user probably knows it. The goal is zero lookup work.

### 2. Summary

- Cover the topic the user named. If they named none, cover the purpose, the current state, and the main decisions.
- Say what was decided, why, and what is still open.
- Give concrete numbers, dates, and file paths. Link files as Markdown links.
- Say clearly where documents disagree with each other or with the code.

### 3. Next steps

- A numbered list in the order to do them.
- Each step names the action, the file or command involved, and what finishing it looks like.
- Mark which steps block others.
- Keep the list to 7 steps or fewer. Put the single most important step first and say why.

## Writing rules

- Common English abbreviations are fine, for example "e.g.", "i.e.", and "etc.".
- Do not assume the user knows project codes. This covers decision numbers (for example "D-06"), experiment or arm identifiers (for example "A-05"), gate names, script numbers, and any other short label made up by the project.
- Never use a project code alone. Always say what it means in plain words first, then show the code in parentheses once if the user needs it to find the file. Example: "the alternative bank experiment (A-05)", not "A-05".
- Spell out technical acronyms and shortened field terms on first use, and define them in the glossary. Example: "Simplified Technical English" instead of its short form.
- Put each project code in the glossary with its plain meaning, so the user can map the code to the file.
- Follow the user's global writing style: short sentences (25 words or fewer), active voice, one term per concept, short paragraphs, and lists for parallel items.
- Do not edit project files. This skill only reads and reports, unless the user asks you to save the reply.
- If the user asks to save the reply, use the `ste-readme` skill for the file.
