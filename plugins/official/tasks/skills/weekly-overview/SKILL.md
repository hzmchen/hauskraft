---
name: Weekly overview
description: A short overview of the week's open tasks, overdue ones first.
tools: [tasks.list]
output: text
evals: evals/weekly-overview.yaml
---

Write a short overview of the household's week for the person.

1. Call tasks.list for open tasks.
2. Start with overdue tasks (due before today), then tasks due in the next seven days, then at most three open tasks
   without a date. Name each by its title; give the weekday for dated tasks.
3. Use at most about 120 words, in the person's language, as a few short lines. No greeting, no advice.
4. If nothing is open, say so in one sentence.
