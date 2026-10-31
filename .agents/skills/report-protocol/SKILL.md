---
name: report-protocol
description: Creates and maintains a local documentation library (default `reports/`) of research reports, concept notes, bug investigations, design decisions and comparisons. Every doc is visually structured markdown (TL;DR, one table or diagram per section, numbered Q&A log at the end), and every folder gets a summary-with-links README using relative paths only. Make sure to use this skill whenever the user asks to create, write or generate a report, doc, write-up, analysis, deep research or "document this", asks to update or fix a reports README/index, or asks to log a question into a doc - even if they never say "report".
---

# report-protocol

You maintain a **documentation library** that a human will skim, click through and learn from. The reader is the user, not a text-scraping agent. A doc that is a wall of paragraphs has failed, however accurate it is.

Every rule below exists to stop one failure: information piled up in paragraphs with no structure, no summary and no way to navigate. If you are unsure which way to go, choose the layout that can be understood by reading only headings, tables, diagrams and the TL;DR.

---

## 1. Library layout

```text
reports/
|-- README.md                  <- root: summary + domain table (relative links)
+-- <domain>/
    |-- README.md              <- sub-domain: fixed template
    |-- 01-<slug>.md
    +-- 02-<slug>.md
```

| Rule                     | Detail                                                                                                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Root**                 | `reports/` unless the project says otherwise (some projects use `docs/`; the same rules apply).                                                                                                                                 |
| **README != bare index** | A README is a _summary page_: TL;DR, tables, a map, key takeaways, and hyperlinks. It is never just a list of links. There is no separate `INDEX.md`.                                                                           |
| **Names**                | Match the naming already used in sibling folders. For new docs default to `NN-kebab-title.md` with the next free number.                                                                                                        |
| **Links**                | **Strictly relative**, computed from the file that contains the link (`./02-x.md`, `../README.md`, `../../core/src/x.py`). Never `/home/...` or `file:///...`. Relative links are what make the file clickable in every viewer. |

---

## 2. Workflow

| Step                          | Do this                                                                                                       | Why                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1. Orient                     | Read `reports/README.md`, then the target domain README. Decide: extend an existing doc, or create a new one. | Prevents duplicate docs and orphan folders.                      |
| 2. Pick the type              | Choose from the table in section 3.                                                                           | Each type has a shape that fits its job.                         |
| 3. Pick the verification mode | See section 5.                                                                                                | The user wants research only when they ask for it.               |
| 4. Draft from the template    | Copy `assets/templates/<type>.md` and fill it.                                                                | The template is what keeps every doc structured.                 |
| 5. Update READMEs             | Sub-domain README first, then root README. Do this **automatically**, without asking.                         | A doc that is not in a README does not exist for the reader.     |
| 6. Lint                       | Run `python <skill-dir>/scripts/lint_reports.py reports` and fix every error.                                 | It checks links, structure and README coverage for you.          |
| 7. Report back                | Reply in a short table: path (relative), type, verification mode, lint result.                                | The user should not have to open the file to know what happened. |

---

## 3. Doc types

| Type                    | Use for                                             | Template                                  |
| ----------------------- | --------------------------------------------------- | ----------------------------------------- |
| **Concept note**        | Learning or explaining a topic or component         | `assets/templates/concept-note.md`        |
| **Investigation**       | Bugs, failures, root causes                         | `assets/templates/investigation.md`       |
| **Design / decision**   | Choosing an approach, migration plans, architecture | `assets/templates/design-decision.md`     |
| **Research comparison** | Comparing tools, libraries or options               | `assets/templates/research-comparison.md` |

When a request spans types (an investigation that ends in a design choice), write the main type and link to a second doc instead of merging them.

---

## 4. Writing rules

**Hard rules.** These are checked by the lint script.

| Rule                                                                                                                        | Why                                       |
| --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Every doc opens with a title, a **metadata table**, and a `> **TL;DR:**` box (1-3 lines).                                   | The reader gets the core in five seconds. |
| **Every `##` section contains at least one table or Mermaid diagram.** Only `TL;DR`, `Related` and `Start here` are exempt. | Forces structure over paragraphs.         |
| Every link is a relative path and resolves to a real file.                                                                  | Clickable everywhere.                     |
| The **Q&A Log is the last `##` section** of every doc, and READMEs have none.                                               | See section 6.                            |
| Sub-domain READMEs use `assets/templates/subdomain-readme.md`.                                                              | Same shape in every folder.               |

**Soft defaults.** Follow them unless the content gives a good reason not to.

- Keep paragraphs to about 4 lines. Convert comparisons and lists of facts into tables.
- Put long supporting detail inside `<details><summary>...</summary>...</details>` so the page stays scannable.
- Keep tables compact. Split a table that passes about 8 rows or 4 columns.
- Bold a key term the first time it appears. Use a short plain-English meaning next to any jargon.
- Mermaid diagrams stay under 12 nodes, with quoted labels when they contain brackets or colons. A broken diagram is worse than a table.
- Each visual gets a title line and a one-line "how to read this".
- Tables and prose carry the same depth. A visual never replaces the explanation, and never forces you to trim real content.

---

## 5. Verification

Pick the mode from the request. **Never invent APIs, functions, syntax or facts.** Prefer "I need to research this further" over guessing.

| Mode                   | When                                                                                     | What you do                                                                                                                                          |
| ---------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Codebase** (default) | The doc is about the project's own code or decisions                                     | Read the actual files. Link the real file and line with a relative path. A claim about code is VERIFIED only if you saw it in the file this session. |
| **Research**           | The user says "research", "deep research", "verify", or the doc is a Research comparison | Check each important claim against 2-3 independent sources. Prefer official docs and primary sources. Fill the _Sources and confidence_ table.       |

Marks used in every verification table:

| Mark       | Meaning                                                    |
| ---------- | ---------------------------------------------------------- |
| VERIFIED   | Verified. You saw the file, or two or more sources agree.  |
| UNVERIFIED | Unverified or single source.                               |
| CONFLICT   | Sources conflict or the claim is refuted. Show both sides. |

Optional: put the matching emoji next to the word for quick scanning: check mark button U+2705 (VERIFIED), warning sign U+26A0 (UNVERIFIED), cross mark U+274C (CONFLICT). The word is always required; the emoji is a bonus.

If you have no web access, say so in the doc and mark external claims UNVERIFIED. Set the metadata **Confidence** row to match the weakest important claim.

---

## 6. Q&A Log

The log records questions the user asked about a doc, with short concrete answers.

| Rule          | Detail                                                                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Location**  | The very last `##` section of the doc, named `## Q&A Log`.                                                                                                                                              |
| **Format**    | Table with columns `# \| Question \| Answer (concrete) \| Date`. Rows are `Q1`, `Q2`, ...                                                                                                               |
| **Numbering** | Append-only. New number = last number + 1. Never reuse or renumber.                                                                                                                                     |
| **Style**     | Answers in 1-3 lines, concrete, no storytelling.                                                                                                                                                        |
| **READMEs**   | Never contain a Q&A log or a question list.                                                                                                                                                             |
| **Fusing**    | When an answer changes what a summary reader should know, rewrite the matching TL;DR line, README table cell, or metadata `Context` row **as a plain fact**. Do not write "Q3 says..." outside the log. |

**Offer, don't assume.** After a teaching exchange that touches an existing doc (or a clearly durable doubt), offer once, in one line: `Log this as Q<next> in <relative path>? (yes/no)`. Log only after a yes. If the user says no or ignores it, do not ask again for that topic. Skip the offer for trivial exchanges.

---

## 7. README maintenance

After creating or changing any doc:

1. **Sub-domain README:** add or update the doc's row in _At a glance_ (relative link, type, what it answers, fused context, status), update the doc count and the _Updated_ date, and refresh _Reading path_ and _Key takeaways_ if the doc changes them.
2. **Root README:** update the domain's row (summary, doc count, status), the _Recently updated_ table, and the _Map_.
3. **New domain:** create its README from the template and add a row to the root README.
4. Run the lint script.

---

## 8. Boundaries

- This skill writes documentation. It does not change code; follow the project's own code-change protocol for that.
- If the project's `AGENTS.md` defines other required steps (for example logging findings to a memory or knowledge graph), do those too. This skill does not replace them.
- For the _wording_ of explanations inside a doc, keep it plain and direct. The teaching skill governs live chat, not file content.

## 9. Before you finish

Check silently, never show it:

1. Does the doc have the metadata table, TL;DR box, one visual per `##`, and the Q&A Log last?
2. Is the doc listed in its folder README, and the folder in the root README?
3. Are all links relative, and does the lint script pass with zero errors?
4. Are unverified claims marked UNVERIFIED and does the Confidence row match?
