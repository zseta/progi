# Example Workflows

Workflows that demonstrate key Progi features. Describe these to the MCP in plain English — it will generate the structure.

---

## 1. Support Ticket Handler

**Use case:** Customer support / ticket handling
**Feature:** Human approval gate — the agent cannot send a customer reply until a human explicitly signs off.

I want a workflow called "Support Ticket Handler" for handling incoming customer support tickets. It has three steps:

1. **Triage** — takes the raw ticket text as input. The agent reads the ticket and categorises it by type (billing, technical, or general) and priority (low, medium, high), and writes a one-sentence summary. No human approval needed, it can just submit.

2. **Draft Reply** — takes the triage result as input. The agent drafts a professional, empathetic reply to the customer. **This step requires human approval** — the agent must show the draft to me and wait for my explicit sign-off before submitting. I may ask for changes; it should iterate until I approve.

3. **Close Ticket** — takes the approved reply as input. The agent asks me for the ticket ID from our support system, records the closure timestamp, and confirms the ticket is closed.

---

## 2. Invoice Processing Pipeline

**Use case:** Document and data processing
**Feature:** Conditional branching — clean invoices go straight to posting; flagged ones detour through a manual review step first.

I want a workflow called "Invoice Processing Pipeline" that processes incoming invoices. It has three steps, but the path through them depends on the invoice:

1. **Extract** — takes the invoice file or pasted invoice text as input. The agent pulls out vendor name, amount, currency, date, and line items. It also decides whether the invoice needs manual review — flag it if the amount is over $10,000, the date is more than 90 days old, the vendor is unrecognised, or any line item is blank.

2. **Manual Review** — only reached if the invoice was flagged. Takes the extracted data as input. The agent presents the data to me, explains what triggered the flag, and asks me to confirm or correct each field before proceeding.

3. **Post to Accounting** — takes clean invoice data as input (either directly from Extract if it wasn't flagged, or from Manual Review if it was). The agent asks which accounting system to post to, walks me through posting, and records the confirmation ID.

The branching rule: if Extract flags the invoice, go to Manual Review then Post to Accounting. If it doesn't, skip Manual Review and go straight to Post to Accounting.

---

## 3. Lead Qualification & Outreach

**Use case:** Sales/lead and CRM tasks
**Feature:** Multi-step handoff chain — each step's output flows automatically into the next step as input, so I never have to repeat myself.

I want a workflow called "Lead Qualification & Outreach" for working a new sales lead from research through to CRM logging. It has five steps in a straight line:

1. **Research Lead** — takes the lead's name, company, and how we found them as input. The agent researches the person and company: their role, company size, industry, likely pain points, and any notable signals like recent funding or hiring activity.

2. **Score & Qualify** — takes the research profile as input. The agent scores the lead against our ideal customer profile (1–10), assigns a fit level (strong, moderate, weak), and recommends an action (schedule a call, send an email, add to nurture). It shows me the score and reasoning and asks if it looks right before submitting.

3. **Draft Outreach** — takes the qualification result as input (and can reference the research from step 1). The agent asks me which channel (email or LinkedIn) and any specific angle I want, then writes a short personalised message with a clear CTA. It shows me the draft and iterates if I ask for changes.

4. **Send Outreach** — takes the drafted message as input. The agent shows me the final message, waits for me to confirm, then guides me through sending it on the chosen channel and records the send timestamp and message ID.

5. **Log to CRM** — takes the send confirmation as input. The agent asks for my CRM and any existing record ID, creates or updates the contact record with everything captured across all previous steps, and confirms the CRM ID and pipeline stage.

---

## 4. Enterprise Deal Pipeline

**Use case:** Sales/lead and CRM tasks — large complex workflow
**Feature:** Everything at once — long linear handoff chain, multiple conditional branches based on deal size and legal requirements, and approval gates at the stages where a human must stay in control.

I want a workflow called "Enterprise Deal Pipeline" that takes a new enterprise sales opportunity from first contact all the way through to a signed contract and onboarding handoff. It has 15 steps. Some steps branch the workflow in different directions depending on the output; others require my explicit approval before proceeding.

1. **Qualify Opportunity** — takes the prospect's name, company, and initial context as input (how we found them, what they asked about). The agent researches the company — size, industry, tech stack, recent news — and produces a qualification summary: estimated deal size (small: under $10k/yr, mid: $10k–$100k/yr, large: over $100k/yr), decision-maker identified (yes/no), and a fit score 1–10. No approval needed, submit immediately.

2. **Route by Deal Size** — takes the qualification result as input. This is a pure routing step: the agent just reads the estimated deal size and sets a `tier` field: `smb`, `mid_market`, or `enterprise`. No other work happens here — it exists purely to branch the workflow.
   - If tier is `smb`, go to **Fast Track Close** (step 3a).
   - If tier is `mid_market`, go to **Discovery Call** (step 4).
   - If tier is `enterprise`, go to **Executive Alignment** (step 3b).

3a. **Fast Track Close** — only reached for SMB deals. Takes the qualification as input. The agent drafts a short proposal email with standard pricing and a Calendly link to book a 30-min close call. **Requires my approval** before sending. After I approve, it sends and records the outcome. Then goes to **Contract Generation** (step 10).

3b. **Executive Alignment** — only reached for enterprise deals. Takes the qualification as input. The agent helps me prepare for an executive-level intro meeting: identifies the right stakeholders on their side, drafts a customised value proposition for their specific industry and size, and suggests an agenda. **Requires my approval** on the meeting prep materials before I go into the call. Then goes to **Discovery Call** (step 4).

4. **Discovery Call** — takes qualification (and executive alignment notes if they exist) as input. The agent helps me structure and run the discovery call: it generates a list of questions tailored to the prospect's industry and deal size, then after the call I paste in my notes and it produces a structured call summary (pain points confirmed, budget signals, timeline, next step agreed). No approval needed.

5. **Assess Technical Fit** — takes the discovery call summary as input. The agent analyses whether our product technically fits their environment based on what came out of the call: integration requirements, compliance needs, scale. It produces a technical fit verdict: `strong_fit`, `fit_with_workarounds`, or `poor_fit`, plus a list of any blockers.
   - If verdict is `poor_fit`, go to **Disqualify & Nurture** (step 6a) — terminal branch.
   - If verdict is `fit_with_workarounds`, go to **Solution Design** (step 6b).
   - If verdict is `strong_fit`, skip Solution Design and go to **Proposal** (step 7).

6a. **Disqualify & Nurture** — only reached if technical fit is poor. Takes the fit assessment as input. The agent drafts a polite disqualification email that explains honestly why we're not the right fit now, and adds the prospect to a long-term nurture sequence. **Requires my approval** before sending — I don't want to burn a relationship without reviewing the message. Terminal step.

6b. **Solution Design** — only reached when there are fit issues to work around. Takes the technical assessment as input. The agent works with me to design a solution that addresses the blockers: custom integrations, phased rollout, or configuration options. Produces a solution design document. **Requires my approval** — this document will be shared externally. Then goes to **Proposal** (step 7).

7. **Proposal** — takes discovery summary and solution design (if it exists) as input. The agent generates a full commercial proposal: executive summary, solution description, pricing options (3 tiers), ROI estimates based on their scale, and a proposed timeline. **Requires my approval** — this is a commercial document going to the prospect. After I approve, it prepares the proposal for delivery.

8. **Send Proposal & Follow Up** — takes the approved proposal as input. The agent guides me through sending the proposal (email or via a tool like DocSend), sets a follow-up reminder, and after I paste in the prospect's response, it summarises their reaction: `positive`, `negotiating`, `stalled`, or `rejected`.
   - If response is `rejected`, go to **Handle Rejection** (step 9a) — terminal branch.
   - If response is `stalled`, go to **Re-engagement** (step 9b).
   - If response is `positive` or `negotiating`, go to **Negotiation** (step 9c).

9a. **Handle Rejection** — only reached on rejection. Takes the prospect's response as input. The agent analyses the rejection reason (price, timing, competitor, fit) and drafts an appropriate closing message — either a breakup email that leaves the door open, or a counter-offer if the reason seems addressable. **Requires my approval**. Terminal step.

9b. **Re-engagement** — only reached when the deal has stalled. Takes the stall context as input. The agent drafts a re-engagement sequence: a check-in message, a relevant case study or new angle, and a suggested trigger event to bring them back. **Requires my approval** before any outreach goes out. Then loops back to **Send Proposal & Follow Up** (step 8) once they re-engage.

9c. **Negotiation** — reached when the prospect is positive or wants to negotiate terms. Takes the proposal and their response as input. The agent helps me track what's on the table: which terms they pushed back on (price, contract length, SLA, payment schedule), what our walk-away limits are, and drafts counter-proposal language for each point. **Requires my approval** on any counter-proposal language before I share it. Then goes to **Contract Generation** (step 10).

10. **Contract Generation** — takes the agreed commercial terms as input (from Fast Track Close, or Negotiation). The agent produces a contract summary document: all agreed terms in plain language, with any non-standard clauses flagged. Asks me whether legal review is required: `yes` or `no`.
    - If legal review required, go to **Legal Review** (step 11).
    - If not, go to **Contract Signing** (step 12).

11. **Legal Review** — only reached if flagged in Contract Generation. Takes the contract summary as input. The agent formats the contract details for legal review, tracks any redlines or comments I paste back in, and produces a clean version incorporating all legal changes. **Requires my approval** on the final version before it goes back to the prospect. Then goes to **Contract Signing** (step 12).

12. **Contract Signing** — takes the approved contract as input. The agent guides me through getting the contract signed: prepares the final document, sends via e-signature tool (DocuSign, HelloSign, etc.), and monitors for completion. Records the signed date and contract ID once both parties have signed. No approval needed — the signing process itself is the gate.

13. **Kickoff Scheduling** — takes the signed contract as input. The agent drafts a kickoff meeting invitation for the new customer: agenda, attendees from both sides (based on deal context), suggested dates, and a pre-meeting questionnaire. **Requires my approval** before sending to the customer.

14. **Onboarding Handoff** — takes all deal context as input. The agent compiles a complete handoff document for the customer success team: company background, what was sold and at what terms, technical requirements identified during the deal, key contacts, any commitments made during negotiation, and the agreed timeline. **Requires my approval** — the CS team will act on this. Then goes to **Close & Log** (step 15).

15. **Close & Log** — takes the handoff confirmation as input. The agent updates the CRM with the final deal status (closed-won), logs the contract value, start date, and account owner, and marks the opportunity as closed. It also sends a brief internal Slack-style summary to paste into the team channel. No approval needed — pure logging. Terminal step.
