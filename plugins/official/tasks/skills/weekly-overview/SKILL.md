---
name: Weekly overview
description: A short overview of the week's open tasks, overdue ones first.
tools: [tasks.list]
output: text
evals: evals/weekly-overview.yaml
---

Write a short overview of the household's week for the person.

1. Call tasks.list for open tasks.
2. Start with overdue tasks (due before today), then tasks due in the next seven days. Name each by its title and
   give its weekday.
3. Then name at most three open tasks without a date. If there are more, say only how many more there are ("and 4
   more without a date"); never list their titles.
4. Use at most about 120 words, in the person's language, as a few short lines. No greeting, no advice.
5. If nothing is open, say so in one sentence.
