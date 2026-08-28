> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Cashfree Agent Skills

> Install Cashfree Agent Skills to load Cashfree product knowledge into Cursor, Claude Code, VS Code Copilot, Gemini CLI, and other AI coding assistants.

<div class="hidden mb-4" data-table-of-contents="top">
  <iframe height="150" width="100%" class="shadow-2xl rounded-md" src="https://www.youtube.com/embed/mHPxTyGoW2w?enablejsapi=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen />
</div>

The **Cashfree Agent Skills** CLI loads Cashfree Payments product knowledge directly into your AI coding assistant. A single command installs a full set of **skill files** (concise markdown documents covering every Cashfree product: PG, Payouts, Subscriptions, Secure ID, Cross Border, Settlements, Auto Collect, and more), plus a **manifest** that tells the assistant which skill to read for a given user intent.

Each skill is split into two files:

* **`SKILL.md`**: the core happy path for the product (when to use, core workflow, security rules, testing, quick diagnostic).
* **`references/REFERENCE.md`**: the deep reference (full field schemas, per-language SDK code, webhook payloads, troubleshooting).

Your AI assistant reads `SKILL.md` first and only pulls from `REFERENCE.md` when it needs deeper detail, keeping answers fast and accurate.

<Frame>
  <iframe width="100%" height="400" src="https://www.youtube.com/embed/TZ2PiZcM-8A?enablejsapi=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen />
</Frame>

## Quick start

Run the following command in your project root. You'll be prompted to select which AI assistants to configure:

<CodeGroup>
  ```bash Install agent skills theme={"dark"}
  npx @cashfreepayments/agent-skills add skills
  ```
</CodeGroup>

<Tip>
  One invocation installs **all** Cashfree skills for the selected assistants. There is no per-product flag; the assistant picks the right skill at query time based on the generated manifest.
</Tip>

## Supported assistants

The CLI supports every mainstream AI coding environment. Each one has its own convention for where skill files and the manifest live; the CLI writes to the correct location automatically.

| Assistant              | Skills directory                    | Manifest file                     |
| ---------------------- | ----------------------------------- | --------------------------------- |
| **Claude Code**        | `.claude/skills/cashfree-skills/`   | `CLAUDE.md` (project root)        |
| **Cursor**             | `.cursor/cashfree-skills/`          | `.cursor/rules/cashfree.mdc`      |
| **OpenCode**           | `.opencode/skills/cashfree-skills/` | `AGENTS.md` (project root)        |
| **VS Code Copilot**    | `.github/skills/cashfree-skills/`   | `.github/copilot-instructions.md` |
| **GitHub Copilot CLI** | `.github/skills/cashfree-skills/`   | `.github/copilot-instructions.md` |
| **Gemini CLI**         | `.gemini/skills/cashfree-skills/`   | `GEMINI.md` (project root)        |
| **Antigravity**        | `.agent/skills/cashfree-skills/`    | `AGENTS.md` (project root)        |
| **OpenAI Codex CLI**   | `.agents/skills/cashfree-skills/`   | `AGENTS.md` (project root)        |

## Installation

<Steps>
  <Step title="Interactive setup">
    The easiest way to get started is to run the CLI interactively and pick one or more assistants from the prompt:

    <CodeGroup>
      ```bash Interactive setup theme={"dark"}
      npx @cashfreepayments/agent-skills add skills
      ```
    </CodeGroup>

    You'll see a multi-select list with every supported assistant; tick the ones you use and press Enter.
  </Step>

  <Step title="Non-interactive / CI setup">
    Pass `--frameworks` with a comma-separated list to skip the prompt. This is useful in CI, `postinstall` hooks, or monorepo bootstrap scripts:

    <CodeGroup>
      ```bash Claude Code + Cursor + Gemini CLI theme={"dark"}
      npx @cashfreepayments/agent-skills add skills --frameworks claude-code,cursor,gemini-cli
      ```

      ```bash VS Code Copilot only, custom project path theme={"dark"}
      npx @cashfreepayments/agent-skills add skills \
        --frameworks vscode-copilot \
        --path /path/to/my-app
      ```

      ```bash All assistants at once theme={"dark"}
      npx @cashfreepayments/agent-skills add skills \
        --frameworks claude-code,cursor,opencode,vscode-copilot,copilot-cli,gemini-cli,antigravity,codex
      ```
    </CodeGroup>

    Valid `--frameworks` values: `claude-code`, `cursor`, `opencode`, `vscode-copilot`, `copilot-cli`, `gemini-cli`, `antigravity`, `codex`.
  </Step>

  <Step title="Restart your AI assistant">
    Most AI assistants load skill files at startup. Restart (or reload the window/workspace) so the new skills and manifest are picked up.
  </Step>
</Steps>

## What gets installed

A single command creates the full skills tree and a routing manifest for every selected assistant.

### Skills directory structure

The CLI installs a structured tree of skill files organised by product and concern. Below is the full directory layout showing every `SKILL.md` and `REFERENCE.md` file that gets created.

<Accordion title="View full directory tree">
  ```
  cashfree-skills/
  ├── getting-started/
  │   └── SKILL.md                     ← Setup, auth, environment config
  ├── eligible-payment-modes/
  │   └── SKILL.md                     ← Check enabled payment modes for a merchant
  ├── pg/
  │   ├── SKILL.md                     ← Payment Gateway overview & sub-skill index
  │   ├── apis/
  │   │   ├── SKILL.md                 ← S2S REST API integration (core flow)
  │   │   └── references/REFERENCE.md  ← Full endpoint map, idempotency, edge cases
  │   ├── backend-sdks/
  │   │   ├── SKILL.md                 ← Backend SDK (Node.js, Python, Java, Go)
  │   │   └── references/REFERENCE.md  ← Refunds, settlements, pre-auth, S2S, token vault, .NET TLS fix
  │   ├── mobile-sdks/
  │   │   ├── SKILL.md                 ← Mobile SDKs (Android, iOS, React Native, Flutter, Cordova)
  │   │   └── references/REFERENCE.md  ← Per-platform callback → backend verify, all SDK options
  │   ├── webhooks/
  │   │   ├── SKILL.md                 ← Webhook setup, signature verification, event bifurcation
  │   │   └── references/REFERENCE.md  ← Full payload schemas for all event types
  │   ├── go-live/
  │   │   ├── SKILL.md                 ← Production checklist & go-live steps
  │   │   └── references/REFERENCE.md  ← Advanced production config & compliance details
  │   ├── refunds/
  │   │   ├── SKILL.md                 ← Refunds lifecycle, INSTANT vs STANDARD, partial/multi
  │   │   └── references/REFERENCE.md  ← Full schema, eligibility, per-language SDK code
  │   ├── disputes/
  │   │   ├── SKILL.md                 ← Dispute lifecycle, accept/contest, evidence, SLAs
  │   │   └── references/REFERENCE.md  ← 24 status values, reason codes, evidence limits
  │   ├── payment-links/
  │   │   ├── SKILL.md                 ← Hosted URLs, partial payments, auto-reminders
  │   │   └── references/REFERENCE.md  ← Full schema, PAYMENT_LINK_EVENT, per-language code
  │   ├── token-vault/
  │   │   ├── SKILL.md                 ← RBI card tokenization, saved cards, CoF
  │   │   └── references/REFERENCE.md  ← Instrument + cryptogram schemas, network behaviour
  │   ├── web-sdk/
  │   │   ├── SKILL.md                 ← Cashfree.js v3: Drop-in, Elements, SPA wiring
  │   │   └── references/REFERENCE.md  ← Full API, React/Vue/Next/Angular, CSP
  │   ├── easy-split/
  │   │   ├── SKILL.md                 ← Marketplace splits, vendor management
  │   │   └── references/REFERENCE.md  ← Vendor KYC schema, on-demand transfer, vendor recon
  │   └── offers/
  │       ├── SKILL.md                 ← Bank/BIN offers, discounts, cashback, no-cost EMI
  │       └── references/REFERENCE.md  ← payment_method filter variants, stacking, tenure table
  ├── secure-id/
  │   ├── SKILL.md                     ← Bank account verification, PAN, GSTIN, DigiLocker
  │   └── references/REFERENCE.md      ← All API endpoints, webhook payloads, frontend SDKs
  ├── subscriptions/
  │   ├── SKILL.md                     ← Recurring payments, plans, mandates, charge lifecycle
  │   └── references/REFERENCE.md      ← Cut-off timelines, mobile SDKs, full webhook payloads
  ├── cross-border/
  │   ├── SKILL.md                     ← International payments & currency conversion
  │   └── references/REFERENCE.md      ← Verification parameters, order tags, webhook payloads
  ├── payouts/
  │   ├── SKILL.md                     ← Bulk payouts, disbursements, beneficiary management
  │   └── references/REFERENCE.md      ← 2FA RSA setup, batch transfers, V1 APIs, webhook payloads
  ├── settlements-and-reconciliation/
  │   ├── SKILL.md                     ← Settlement cycle, recon APIs, UTR matching, finance ops
  │   └── references/REFERENCE.md      ← Full recon row schema, event types, sample reconciler
  ├── auto-collect/
  │   ├── SKILL.md                     ← Virtual bank accounts, static UPI VPAs, QR codes
  │   └── references/REFERENCE.md      ← VBA schema, bank rails (Axis / ICICI / Yes), credit webhook
  ├── migrate-from-razorpay/
  │   ├── SKILL.md                     ← Razorpay → Cashfree migration: 5 gotchas, 7-step cutover
  │   └── references/REFERENCE.md      ← Endpoint map, per-language SDK rewrites, webhook diff
  ├── migrate-from-juspay/
  │   ├── SKILL.md                     ← Juspay → Cashfree migration: session/status rewrites
  │   └── references/REFERENCE.md      ← Endpoint map, field diffs, orchestrator feature checklist
  ├── validation-and-testing/
  │   └── SKILL.md                     ← Post-integration validation & test data
  └── common-mistakes/
      └── SKILL.md                     ← Debugging guide: signatures, IP whitelist, mobile SDK, rate limits
  ```
</Accordion>

### The manifest file

In addition to the skill files, the CLI writes a **manifest** to the location your assistant conventionally reads for project instructions. The manifest acts as a routing table, directing the assistant to the correct skill file for each query.

The CLI writes the manifest to different locations depending on the assistant (for example, `CLAUDE.md` for Claude Code, `.cursor/rules/cashfree.mdc` for Cursor, `AGENTS.md` for OpenCode / Codex / Antigravity).

The manifest:

1. Instructs the assistant to read `getting-started/SKILL.md` first when a user is new to Cashfree.
2. Contains a **skill map**: a table routing user intents (e.g. "accept payments on mobile", "respond to a dispute", "migrate from Razorpay") to the correct skill file.
3. Reminds the assistant to read `validation-and-testing/SKILL.md` after generating integration code.

For Cursor, the manifest uses the `.mdc` format with Cursor's metadata frontmatter. For every other assistant, it's plain Markdown.

## How AI assistants use the skills

When you ask a Cashfree-related question, your AI assistant follows a four-step process to locate and deliver the most relevant information.

<Steps>
  <Step title="Manifest lookup">
    On any Cashfree-related question, the assistant first consults the manifest's skill map to find the matching `SKILL.md`.
  </Step>

  <Step title="Core skill read">
    The assistant reads that `SKILL.md` for the happy path, scope boundaries, and core workflow.
  </Step>

  <Step title="Deep reference (as needed)">
    If the question needs field-level detail, per-language SDK code, or edge-case troubleshooting, the assistant pulls the corresponding `references/REFERENCE.md`.
  </Step>

  <Step title="Validation after coding">
    Once integration code has been generated, the assistant reads `validation-and-testing/SKILL.md` to output a testing checklist and sandbox test data.
  </Step>
</Steps>

### Example interactions

The following examples illustrate how an AI assistant uses the skill files to answer common Cashfree integration questions.

<Accordion title="View example interactions">
  ```
  You: "I want to integrate Cashfree Payments in my Express app"
  AI: *reads manifest → getting-started/SKILL.md → pg/SKILL.md → pg/backend-sdks/SKILL.md*
      Walks through API keys, SDK install, Create Order, backend verification.

  You: "Customer wants a partial refund on order 42, instant if possible"
  AI: *reads pg/refunds/SKILL.md → references/REFERENCE.md*
      Creates refund via SDK with refund_speed: INSTANT, wires REFUND_STATUS_WEBHOOK,
      explains the eligibility matrix.

  You: "We got a chargeback on cf_payment_id 789, help me respond"
  AI: *reads pg/disputes/SKILL.md → references/REFERENCE.md*
      Fetches the dispute, covers every preferred_evidence category,
      POSTs contest with evidence URLs before respond_by.

  You: "Match this UTR on our bank statement back to a Cashfree settlement"
  AI: *reads settlements-and-reconciliation/SKILL.md → references/REFERENCE.md*
      Fetches settlement by UTR, walks recon events, reconciles fees/TDS/adjustments.

  You: "Build a marketplace splitting 85% to vendor, 10% to logistics, 5% commission"
  AI: *reads pg/easy-split/SKILL.md → references/REFERENCE.md*
      Creates vendors with KYC, adds order_splits on POST /pg/orders,
      sets refund_splits on refunds.

  You: "Run a 10% HDFC credit card offer + no-cost EMI on 3/6-month tenures"
  AI: *reads pg/offers/SKILL.md → references/REFERENCE.md*
      Creates two offers (DISCOUNT + NO_COST_EMI), attaches offer_id at Order Pay,
      validates redemption_status in webhook.

  You: "Give each dealer a virtual bank account number for monthly invoice collection"
  AI: *reads auto-collect/SKILL.md → references/REFERENCE.md*
      POST /pg/vba with remitter lock, subscribes to VBA_CREDIT, reconciles by
      virtual_account_id.

  You: "Migrate my Express app from Razorpay to Cashfree"
  AI: *reads migrate-from-razorpay/SKILL.md → references/REFERENCE.md*
      Maps keys/amounts/signatures, rewrites orders/checkout/webhook,
      plans a parallel-run cutover.

  You: "My .NET app fails with SSL/TLS error when calling Cashfree"
  AI: *reads pg/backend-sdks/references/REFERENCE.md*
      Applies the TLS 1.2 ServicePointManager fix.
  ```
</Accordion>

## Skill index

The table below lists every skill included in the installation, grouped by category. Expand each group to see the individual skills and what they cover.

<AccordionGroup>
  <Accordion title="Onboarding">
    * **getting-started**: merchant account setup, API key retrieval, sandbox vs. production config, environment variables.
    * **eligible-payment-modes**: how to check which payment methods (UPI, cards, net banking, wallets, paylater, or EMI) are enabled for the merchant.
  </Accordion>

  <Accordion title="Payment Gateway (PG)">
    * **pg**: PG overview and sub-skill index.
    * **pg/apis**: server-to-server REST API integration (any backend language).
    * **pg/backend-sdks**: official SDKs for Node.js, Python, Java, Go, PHP, .NET.
    * **pg/mobile-sdks**: Android, iOS, React Native, Flutter, Cordova / Capacitor.
    * **pg/web-sdk**: Cashfree.js v3 Drop-in and Elements (headless) for React, Vue, Next.js, Angular.
    * **pg/webhooks**: signature verification, event bifurcation, full payload schemas.
    * **pg/go-live**: production checklist, domain whitelisting, integrity checks.
    * **pg/refunds**: full or partial or multi-refunds, `INSTANT` vs `STANDARD`, refund webhook.
    * **pg/disputes**: chargeback lifecycle, accept vs. contest, evidence submission, SLAs.
    * **pg/payment-links**: hosted URLs, partial payments, auto-reminders.
    * **pg/token-vault**: RBI-compliant card tokenisation (saved cards, card-on-file, cryptograms).
    * **pg/easy-split**: marketplace splits, vendor management, static vs. dynamic splits.
    * **pg/offers**: bank/BIN/issuer offers, discounts, cashback, no-cost EMI.
  </Accordion>

  <Accordion title="Other products">
    * **secure-id**: KYC / verification (bank account, PAN, GSTIN, Aadhaar, DigiLocker).
    * **subscriptions**: plans, mandates, recurring charge lifecycle, pause or resume or cancel.
    * **cross-border**: international payments and currency handling.
    * **payouts**: bulk disbursements, beneficiary management, V1 / V2 auth.
    * **settlements-and-reconciliation**: settlement cycle, recon APIs, UTR matching, finance ops.
    * **auto-collect**: virtual bank accounts, static UPI VPAs, QR codes for inbound collection.
  </Accordion>

  <Accordion title="Migration skills">
    * **migrate-from-razorpay**: Razorpay → Cashfree migration: concept map, 7-step cutover, code diffs.
    * **migrate-from-juspay**: Juspay → Cashfree migration: orchestrator exit, session/payment-session mapping, webhook rewrites.
  </Accordion>

  <Accordion title="Validation & debugging">
    * **validation-and-testing**: sandbox test data (cards, UPI VPAs), post-integration checklist.
    * **common-mistakes**: diagnostic guide: signature mismatches, IP whitelisting, mobile SDK callbacks, rate limits, go-live pitfalls.
  </Accordion>
</AccordionGroup>

## Resources

Explore additional resources to help you get started with the Cashfree Agent Skills.

<CardGroup cols={2}>
  <Card title="GitHub Repository" icon="github" href="https://github.com/cashfree/agent-skills">
    View the source code, report issues, and contribute to the toolkit.
  </Card>

  <Card title="npm Package" icon="npm" href="https://www.npmjs.com/package/@cashfreepayments/agent-skills">
    Package details, install metadata, and version history on npm.
  </Card>
</CardGroup>

## Troubleshooting

If you encounter issues during or after installation, expand the relevant section below for guidance.

<AccordionGroup>
  <Accordion title="Assistant doesn't see the skills after install">
    * **Restart** the assistant (or reload the IDE window). Most AI coding assistants only scan skill directories at startup.
    * **Verify files were written**: check that `cashfree-skills/` exists under the correct base directory for your assistant (see the "Supported assistants" table above).
    * **Verify the manifest**: open the manifest file (e.g. `CLAUDE.md`, `.cursor/rules/cashfree.mdc`, `AGENTS.md`) and confirm the "Cashfree Payments Integration Skills" section is present. Without the manifest, the assistant has no routing table.
  </Accordion>

  <Accordion title="Unknown framework error">
    The `--frameworks` flag accepts only these values: `claude-code`, `cursor`, `opencode`, `vscode-copilot`, `copilot-cli`, `gemini-cli`, `antigravity`, `codex`. Double-check for typos or extra whitespace in the comma-separated list.
  </Accordion>

  <Accordion title="Permission errors (EACCES)">
    If you see `EACCES` when running the command, check that your current user has write permissions on the project path passed via `--path` (defaulting to the working directory). Avoid `sudo` with `npx`; fix folder ownership instead (`chown -R $USER .`). On CI, ensure the workspace step runs before the skills install step.
  </Accordion>

  <Accordion title="Node.js or npx version issues">
    The CLI requires Node.js ≥ 18. If `npx @cashfreepayments/agent-skills` fails with an unexpected syntax error, upgrade Node (`nvm install --lts` works in most setups) and retry.
  </Accordion>
</AccordionGroup>
