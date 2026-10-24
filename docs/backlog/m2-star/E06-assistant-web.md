# E06 · Assistant in the web app

**Goal:** Members use the assistant from a side panel on every page, turn pasted notes into tasks and see a weekly
overview on Today, with the same functions in every theme (spec §8.0, §10.1, §10.2.2).
**Out of scope:** Streaming text, voice input, a command palette, phone-optimised layout beyond the narrow-screen rule.
**Dependencies:** E03-02, E04, E05.

Names, roles and German names are in `docs/testing/ui-contract.md` § "M2* additions". Everything is in en and de.

---

## M2S-E06-01 · Assistant button and side panel
- **Story:** As a member, I want to open the assistant from any page without losing my place, so that I can ask while I
  look at my tasks.
- **AC:**
  - When `GET /assistant/status` says `available` and the person has `assistant.use`, every navigation style renders
    the button "Assistant" (`aria-expanded`), which opens the complementary landmark "Assistant"; otherwise there is no
    button.
  - On wide screens the panel sits beside the page content (the page stays usable); below 768 px it covers the page
    and "Close assistant" returns focus to the button.
  - Open or closed is remembered per device (browser storage, with a safe fallback).
  - The button and panel are part of the shell: their accessibility tree is identical in every theme and mode.
- **Tech:** `apps/web/src/assistant/Panel.tsx`, the navigation renderers.
- **Tests:** E2E: `tests/e2e/assistant.spec.ts`, `tests/e2e/agentic.spec.ts` step 2. Vitest: visibility rules.
- **Deps:** E03-02, E04-01 · **Est:** M · **Labels:** area:web

## M2S-E06-02 · Chats in the panel
- **Story:** As a member, I want to start, switch and delete chats, so that topics stay apart and old ones go away.
- **AC:**
  - "New chat" starts an empty chat; the list "Chats" shows my chats newest first, titled by their first message
    ("Untitled chat" before that); choosing one shows its messages.
  - "Delete chat '<title>'" asks in the alert dialog "Delete chat?" (Delete, Cancel); Delete removes it from the list.
- **Tech:** `apps/web/src/assistant/Chats.tsx`.
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 12. Vitest: list and delete flow.
- **Deps:** E06-01 · **Est:** S · **Labels:** area:web

## M2S-E06-03 · Messages and progress
- **Story:** As a member, I want to type a request and read the answer in the panel, so that talking to the assistant
  feels like a chat.
- **AC:**
  - The textbox "Message the assistant" sends with Enter or "Send" (Shift+Enter adds a line); the log "Messages"
    shows my message and the answer, and screen readers announce new answers politely.
  - While a run is going, the status "Working…" shows and sending is disabled.
  - Answers render a safe markdown subset (paragraphs, lists, bold, links to app routes); no raw HTML.
  - A failed run shows an alert with a stable message per `error_code` (e.g. `model_unavailable`: "The assistant is
    not available right now. Try again later.").
- **Tech:** `apps/web/src/assistant/Messages.tsx`, a sanitising markdown renderer (dependency stated in the PR, or
  a small own renderer).
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` steps 3–4. Vitest: rendering, errors.
- **Deps:** E06-01, E04-02 · **Est:** M · **Labels:** area:web

## M2S-E06-04 · Action and confirmation cards
- **Story:** As a member, I want to see exactly what the assistant did and decide before it deletes anything, so that I
  stay in control.
- **AC:**
  - Each `Action` renders as an article named by its `summary_key` text with `record.label` (e.g. "Added task 'Buy
    milk'"; without a key: "Used <tool>"),
    with the link "Open" to the record's page and, when `undo_available`, the button "Undo"; an undone action reads
    "Undone".
  - Each `Confirmation` renders as an article named e.g. "Delete task 'Buy milk'?" with the buttons "Delete" and
    "Cancel"; the answer resumes the run and the card shows the result.
  - After any action or undo, the task lists and widgets refetch, so the Tasks widget shows the change without a
    reload.
- **Tech:** `apps/web/src/assistant/Cards.tsx`; action texts from plugin locales (`<namespace>:tool.<verb>.done`,
  `.confirm`).
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` steps 3, 5, 6. Vitest: cards.
- **Deps:** E06-03, E04-04, E04-06 · **Est:** M · **Labels:** area:web

## M2S-E06-05 · "Add from text" on All tasks
- **Story:** As a member, I want to paste a note and pick which suggested tasks to add, so that turning a list into
  tasks takes seconds.
- **AC:**
  - When the assistant is available, All tasks shows the button "Add from text", which opens the dialog "Add tasks
    from text" with the textbox "Text" and the button "Suggest tasks".
  - Suggestions appear as the list "Suggested tasks" with one checked checkbox per task; the button reads "Add <n>
    tasks" for the number checked and creates them through the normal tasks API; the dialog closes and the list shows
    them.
  - Errors show next to the button; the dialog never creates anything on its own.
- **Tech:** the tasks plugin's web module; the generated client of `@hauskraft/sdk-ts` (no core import).
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 8. Vitest: dialog states.
- **Deps:** E05-03 · **Est:** S · **Labels:** area:tasks, area:web

## M2S-E06-06 · "Weekly overview" widget
- **Story:** As a member, I want the week's overview on Today, so that I see what matters without asking.
- **AC:**
  - The tasks plugin contributes the widget `tasks.overview` titled "Weekly overview"; it shows my latest overview with "Created <relative
    time>", or "No overview yet.", and the button "Create now", which runs the skill and shows the new text.
  - Without an available assistant the widget says "The assistant isn't set up." and has no button.
  - The widget is not part of any seeded or default layout: members add it with Edit layout.
  - The widget is function-invariant across themes like every widget.
- **Tech:** the tasks plugin's web module and manifest.
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 9. Vitest: states.
- **Deps:** E05-04 · **Est:** S · **Labels:** area:tasks, area:web
