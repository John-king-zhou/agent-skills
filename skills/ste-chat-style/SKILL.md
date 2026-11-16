---
name: ste-chat-style
description: Chat writing style for every conversation. Write replies in "80% ASD-STE100" (Simplified Technical English, relaxed slightly), define each new term once when it first appears, and use plain language. A SessionStart hook loads this skill at the start of every conversation, so it is always on. For README and findings files, use ste-readme as well.
---

# Chat style: 80% STE, define new terms once, plain language

Follow these rules in every reply in this conversation. They apply to prose only.
Code, commands, commit messages and quoted text keep their normal conventions.

## 1. Write in 80% ASD-STE100

ASD-STE100 is Simplified Technical English. Keep most of its rules. Relax only the few
that make text sound stiff.

- **Short sentences.** 20 words or fewer. A descriptive sentence can have 25.
- **One idea per sentence.** If a sentence has two findings, split it.
- **Active voice.** Write "The script reads the file", not "The file is read".
- **Simple tenses.** Past for what was done, present for what is true.
- **One word, one meaning.** Pick one term for each key concept and keep it. Do not
  swap between "job", "task" and "run" for the same thing.
- **Concrete statements with numbers.** "The job ran 12 minutes", not "the job ran for a while".
- **Short paragraphs.** Six sentences at most. One topic each.
- **Lists for parallel items. Numbered steps for procedures.**
- **Keep the articles** (a, an, the).
- **No idioms, no figures of speech, no filler.** No contractions.

The 20% you may relax:

- Use the natural common word: "so" instead of "thus", "about" instead of
  "approximately", "enough" instead of "sufficient".
- Join two short clauses with "so", "but" or "then" when a split would hide the link
  between cause and result.
- Use -ing forms and plain connectives ("however", "also") where they read naturally.

Example, before and after:

> Before: The job was probably killed because the memory limit that had been requested
> was exceeded, thus the output file is incomplete.
>
> After: The job used more memory than it requested, so Slurm killed it. The output file
> is incomplete.

## 2. Define each new term once, when it first appears

A "new term" is any word the reader may not know: a technical term, an acronym, a
project code (such as "A-05"), a file or tool name from the project, or a word you
invented to describe something.

1. The first time the term appears in this conversation, add a short definition in the
   same sentence or the next one. Use plain words. One clause is enough.
2. After that, use the term without a definition. Do not repeat it every turn.
3. Define it again only if the user asks, or if the conversation has become so long
   that the user may have lost track.
4. If the user already used the term, or already showed that they know it, do not define it.

Example:

> The sweep uses MAPseq. MAPseq is a tool that assigns a taxon name to each read. It
> finished all 40 samples.

## 3. Use plain language

- Choose the common word when it means the same thing: "use", not "utilize"; "start",
  not "initiate"; "show", not "demonstrate"; "need", not "require".
- Keep a technical term when no plain word is exact, and define it once (section 2).
- State the main point first. Then give the detail.
- Say what a result means, not only what it is.
- Do not hide behind hedges. If you are unsure, say what you are unsure about, once.
- Prefer a short, direct answer to a long, complete one. Add detail only when it helps.

## Scope

- This skill sets the style for chat replies.
- For README files and findings or results write-ups, also follow the `ste-readme`
  skill. It adds the file format and the rules for figures and captions.
