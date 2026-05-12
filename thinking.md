# Part 3 — Thinking Question

## Question A — The Immediate Response

**Draft message:**

> Hi [Guest's first name], I'm really sorry — I completely understand how
> stressful this is, especially with guests arriving in a few hours. I've
> immediately alerted our caretaker and property team. Someone will call
> you within the next 15 minutes to resolve this tonight.
> — Nistula Team

**Why this wording:**
The guest is frustrated at 3am — they need to feel heard and need a
concrete next step, not a long explanation. The message acknowledges the
situation without being defensive, commits to a specific callback window
(15 minutes) rather than a vague "soon", and deliberately does not respond
to the refund demand — that decision requires a human with context on the
stay and costs.

---

## Question B — The System Design

When the message arrives, the platform classifies it as `complaint` and
assigns `action: escalate` regardless of AI confidence.

**Immediately:**
1. The inbound message and AI draft are logged in `messages` and `ai_drafts`.
2. The conversation is flagged `status: escalated`.
3. The on-call caretaker receives an SMS and WhatsApp push alert with the
   guest's name, property, and the message text.
4. The property manager receives a push notification on the agent dashboard.
5. An incident record is created linked to the reservation — capturing the
   issue type (no hot water), timestamp, and property.
6. The AI draft is queued for agent review — it is NOT auto-sent; a human
   must confirm or edit before it goes out.

**If no human responds within 30 minutes:**
- The system sends a follow-up to the guest:
  *"We haven't forgotten you — our property manager has been alerted and
  is on their way to reach you. We apologise for the wait."*
- The escalation is bumped to the senior manager with an alert.
- A flag is added to the reservation record for mandatory post-stay review.

---

## Question C — The Learning

This is the third hot water complaint at Villa B1 in two months. The
system should not treat it as an isolated incident.

**What the system should do now:**
- A recurring issue detector tracks complaint `issue_type` per property.
  Three complaints of the same type within 60 days triggers a maintenance
  alert automatically.
- A non-urgent maintenance ticket is created for Villa B1 (hot water
  system inspection) and assigned to the property manager.
- The incident is added to a property health dashboard surfacing recurring
  issues by frequency.

**What I would build to prevent a fourth complaint:**
1. **Pre-arrival checklist:** A structured checklist caretakers must
   complete and sign off on 2 hours before every check-in. Hot water is a
   line item after the second complaint. No sign-off = no guest access
   confirmed.
2. **Automated property health report:** A weekly digest to property
   managers listing open maintenance items and complaint patterns, so
   issues don't get buried in individual tickets.
3. **Root cause tagging:** When closing a complaint ticket, the agent must
   tag a root cause (e.g. "geyser", "plumbing", "power"). This lets the
   system distinguish between a geyser fault (hardware fix needed) and a
   power cut (external). Over time this data drives smarter alerting.