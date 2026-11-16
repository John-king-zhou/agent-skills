---
name: ste-readme
description: Write explanations, summaries and README or findings files in "80% ASD-STE100" style (Simplified Technical English, relaxed slightly so it reads naturally), with relevant figures embedded and briefly captioned. Use this skill whenever the user asks for a README, a findings or results summary, a write-up or documentation file for a project, data or analysis folder, or asks to explain or summarise what was found "in STE", "ASD-STE100", "simplified technical English", "simple English" or "plain style", even if they do not name the percentage. Also use it when the user asks to add figures to an explanation or to document notebooks and their outputs for a colleague. A findings file also follows the wait-what style (context first, glossary terms).
---

# STE-style explanations and README files

This skill covers two things that usually go together:

1. **A writing style**: "80% ASD-STE100". Simplified Technical English, relaxed a little.
2. **A deliverable**: a Markdown README or findings file that sits in the project folder,
   with the relevant figures embedded and a short caption under each.

Use the style alone when the user only wants an explanation in chat. Use both when they
want a file.

## Part 1: The style

ASD-STE100 was made so that technical text is hard to misread, also for readers whose
first language is not English. Strict STE can sound stiff. The user prefers about 80% of
it: keep the rules that prevent misreading, relax the ones that only make the text
awkward.

### Keep these rules

- **Short sentences.** Aim for 20 words or fewer. A descriptive sentence can go to 25.
- **One idea per sentence.** If a sentence has two findings, split it.
- **Active voice.** "The method fits the derivative", not "the derivative is fitted".
- **Simple tenses.** Past for what was done, present for what is true.
- **One word, one meaning.** Choose a term and keep it. Do not alternate between
  "trajectory", "curve" and "time series" for the same thing unless you say they are the same.
- **Concrete statements with numbers.** "97% of trajectories reach R² above 0.9", not
  "most trajectories fit well".
- **Short paragraphs.** Six sentences at most. One topic each.
- **Lists for parallel items, numbered steps for procedures.**
- **No idioms, no figures of speech, no filler.** No contractions.
- **Keep the articles** (a, an, the). Do not write in telegraphic style.

### Relax these rules (the 20%)

- **Use the natural common word** when the STE-approved word sounds stiff: "so" for
  "thus", "enough" for "sufficient", "about" for "approximately", "then" to link steps.
- **Allow a compound sentence** joined by "so", "but" or "then" when splitting it would
  hide the link between cause and result.
- **Allow -ing forms and ordinary connectives** where they read naturally.
- **Use the field's own technical terms** freely. Define a term once if the reader may
  not know it.
- **Lead a bullet with a bold phrase** that states the point, then explain it.

### The difference in practice

Strict (100%):

> One trajectory does not give sufficient information to identify one equation. Along one
> trajectory, the library terms are almost the same as each other. Thus, many structures
> fit the data equally well, and small differences decide the vote.

80%:

> One trajectory does not contain enough information to identify a single equation. Along
> one curve, the library terms look almost the same as each other, so many structures fit
> equally well. Small differences in curve shape then decide the winner.

Strict (100%):

> - A free τ improves the fit of the derivative.
> - A free τ does not improve the reconstruction with five terms. For N50, the result
>   decreases from 97% to 85%.

80%:

> - **A free τ improves the derivative fit but not the reconstruction.** With five terms,
>   N50 drops from 97% to 85%.

If the user asks for a different level ("100%", "strict", "50%"), move along the same
scale: strict means apply every rule above without the relaxations; lower means closer to
ordinary clear prose but still short sentences and active voice.

## Part 2: The README or findings file

### Before writing

The file is only as good as the facts in it, and readers will trust its numbers.

- **Read the sources.** Open the notebooks, scripts, metadata and any existing README.
  Take numbers from stored outputs or saved result files, not from memory of the
  conversation. If a number cannot be found in the folder, leave it out or say it is
  not verified.
- **Look at every figure you plan to include.** Captions written without viewing the
  figure tend to describe what the figure was meant to show, not what it shows.
- **Check for an existing file.** If a README already exists, read it and ask or extend
  it; do not overwrite someone's file silently.

### Findings files: also follow the wait-what style

This applies to findings and results files (`<topic>_findings.md` and similar). It does
not apply to a plain `README.md` that only describes a folder.

`wait-what` is a user-only skill, so the Skill tool may refuse it. If it does, read
`~/.claude/skills/wait-what/SKILL.md` and follow it as written. Do not copy it into the
project. Its rules for a findings file:

1. **Open with a little context.** Before the first finding, tell the reader in two to
   four sentences what the project is, what question this file answers, and where the
   work stands. Assume the reader has lost track.
2. **Use the project's ubiquitous language.** Take every term from `GLOSSARY.md`. If the
   repo has a `GLOSSARY-MAP.md`, follow it to the right glossary. Use each glossary term
   exactly as written. Do not invent a synonym.
3. **No glossary found?** Do not create one. Choose one name for each key concept, use
   it everywhere, and define it once where it first appears. Tell the user in the
   hand-over message that no `GLOSSARY.md` exists.
4. **Write in Simplified Technical English.** The 80% level from Part 1 applies.

If the wait-what rules and the structure below conflict, keep the structure below and
apply the wait-what rules inside it.

### Where to put it and how to link figures

- Put the file in the folder it describes, next to the notebooks or code, so that
  relative links work and the file travels with the folder.
- Link figures with **relative paths** from the file's own location, for example
  `![Reconstruction against number of terms](figures/vote/fig2_reconstruction.png)`.
  Do not use absolute paths; they break when the folder is copied.
- After writing, confirm that each linked image file exists.
- Name the file for what it is: `README.md` for a description of the folder,
  `<topic>_findings.md` for results.

### Structure

Adapt the sections to the content, but this order works for most analysis folders:

```markdown
# <What this is>: <Findings So Far | README>

<Two or three lines: what the file covers, how to view the figures, which notebooks or
scripts the content comes from.>

## 1. The data            (what is in the folder, sizes, how it was made)
## 2. <Method or analysis> (what was done, in a few sentences, then findings as bullets)
## 3. <Limits>            (why a result is or is not decisive)
## 4. <Further analysis>  (one section per major analysis)
## 5. Conclusions         (three to five bullets; say which findings are solid)
## 6. Recommended next steps (numbered)
```

For a plain README, replace the findings sections with: what each file or notebook does,
how to run it (environment, working directory), what the outputs are and where they go,
and known problems.

### Figures and captions

Choose figures that carry a finding. A few well-chosen figures are better than every
figure the notebooks made; five to eight is usually enough.

Place each figure directly after the text that it supports. Under it, write a caption in
this form:

```markdown
![Short alt text](relative/path/to/figure.png)

**Figure 3. Share of trajectories with a good reconstruction, against the number of terms.**
The black line is all plasmids together. The share is highest at five or six terms. It
drops at three terms, and for P3 it falls sharply at seven terms.
```

- The bold sentence says what the figure is.
- The next one to three sentences say how to read it (what the lines or colours mean)
  and what the reader should see. State the observation, not only the axes.
- Refer back to figures from the text by number ("see Figure 3") when a later section
  relies on them.

### Honest reporting

- Separate what is solid from what is not. If a result is sensitive to a choice (a
  threshold, a seed, a unit), say so in one sentence.
- Say what was not run or not checked.
- Do not smooth over a negative result. "The vote does not settle on one structure" is a
  finding.

### When you hand it over

In chat, say where the file is and how to view the figures (for example, the Markdown
preview in the editor). Add a short table of the figures and what each shows if there are
several. Mention that the file must stay in its folder for the relative links to work.
Keep the chat message in the same style as the file.
