# 10_DESIGN_SYSTEM.md

# Design System

## 1. Purpose

Define strict visual constraints for the frontend.

This document does not recommend fonts, colors, palettes, components, or visual directions.

The builder must not use personal design judgment.

Use mandatory design tools, skills, plugins, and MCPs before implementation.

---

## 2. Mandatory Design Process

Before building UI, use any and all available design skills/plugins/MCPs, mandatorily including but not limited to:

```text
emil-design-eng
frontend-design
design-taste-frontend
ui-ux-pro-max
shadcn ui
framer-motion
Figma
senior-frontend
```

If `framer-motion` is needed, install through npm.

If any listed tool/skill/plugin/MCP is unavailable, stop and report the missing capability.

Do not proceed by substituting personal design taste.

---

## 3. Product Feel

The interface must support:

```text
credit decisioning
payments risk review
expected-loss interpretation
model-risk validation
policy-threshold analysis
```

The interface must not become:

```text
a generic SaaS dashboard
a cybersecurity interface
a crypto dashboard
a bank marketing website
a black/white minimalist theme
a product-sales landing page
```

---

## 4. Forbidden Fonts

Do not use:

```text
Anthropic
Fraunces
Archivo
IBM Plex
Inter
Geist
Grotesk
Grotesque
Big Shoulder
Saira
Public
Spline
Arial
Calibre
Times New Roman
JetBrains
DM Mono/Sans
Newsreader
Red Hot
Sora
Libre Franklin
Source Serif 4
Terminal
Cascadia
B612
Spectral
```

Source Code Pro is allowed only for fully capitalized text.

Also forbidden:

```text
any sans, serif, mono, display, condensed, pro, or other variant of the listed families
```

Do not use system defaults if they resolve to forbidden families.

---

## 5. Forbidden Dark Theme Colors

For dark themes, do not use:

```text
cyan
steel
graphite
amber
gold
yellow
orange
slate
dark gray
dark blue
pink
magenta
purple
violet
indigo
red
green
near-black
```

Do not create a simple black/white theme.

---

## 6. Forbidden Light Theme Colors

For light themes, do not use:

```text
warm
beige
pure white
cream
off-white
white
gold
amber
yellow
light blue
light gray
orange
```

Do not create a simple black/white theme.

---

## 7. Forbidden UI/UX Patterns

Avoid unless explicitly requested by the user:

```text
rounded cards
SaaS dashboard
cybersecurity aesthetic
neon visuals
terminal PowerShell
products-selling brand identity
random graph effects
random chart animations
mesh backgrounds
decorative financial curves
decorative market lines
generic KPI tiles
generic fintech landing sections
```

If using shadcn/ui, override default rounded-card SaaS styling.

Do not accept default component aesthetics.

---

## 8. Motion Rules

Motion must be functional only.

Allowed motion purposes:

```text
show threshold change
show decision state change
show model verdict change
show stress scenario transition
show selected row focus
```

Forbidden motion:

```text
decorative floating charts
random financial line animations
ambient mesh movement
cyber glow effects
crypto network animations
hero gimmicks
```

Use `framer-motion` only if motion improves risk comprehension.

---

## 9. Chart Rules

Charts must explain risk.

Allowed chart purposes:

```text
PD distribution
approval mix
expected loss
fraud threshold tradeoff
manual-review capacity
stablecoin risk exposure
model calibration
score drift
validation verdicts
```

Forbidden chart use:

```text
decorative charts
fake market graphs
animated financial noise
unlabeled curves
hardcoded metrics
unsupported numbers
```

Every chart must trace to `data/outputs`.

---

## 10. Component Rules

Components must support risk decisions.

Allowed component functions:

```text
decision review
risk scoring
threshold control
loss explanation
model validation
evidence traceability
```

Forbidden component functions:

```text
marketing conversion
decorative storytelling
empty visual polish
fake AI assistant
crypto promotion
unrelated animation
```

No component should exist only because it looks impressive.

---

## 11. Copy Rules

Use precise risk language.

Allowed:

```text
modeled probability
estimated expected loss
manual-review threshold
validation evidence
AML-style risk indicators
synthetic transaction sample
```

Forbidden:

```text
production-ready
institutional-grade
AI-powered magic
guaranteed fraud detection
AML compliance platform
optimal policy
real-time bank system
```

---

## 12. Layout Rules

The layout must prioritize:

```text
risk hierarchy
decision traceability
metric readability
validation evidence
threshold tradeoffs
```

Do not prioritize:

```text
visual drama
brand storytelling
marketing polish
empty whitespace
mobile-first simplification
```

Desktop and laptop are primary.

Mobile only needs readable fallback.

---

## 13. Build Boundary

Project root:

```text
/Users/vatsal/Documents/credits-lab
```

Docs path:

```text
/Users/vatsal/Documents/credits-lab/docs
```

Do not create `README.md` unless explicitly requested by the user.

Do not invent frontend metrics.

Do not use personal design taste.

Do not violate forbidden fonts, colors, patterns, or components.
