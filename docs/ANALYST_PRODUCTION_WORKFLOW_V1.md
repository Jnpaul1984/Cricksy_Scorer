# Analyst Production Workflow v1

## Purpose

This document defines how the Cricksy Analyst System should support weekly cricket analysis production, starting with podcast preparation and expanding into coaching, media, scouting, and Sports Intelligence Institute workflows.

The goal is to turn raw match data into clear, useful, and media-ready cricket intelligence.

---

## 1. Core Production Goal

The weekly analyst workflow must help the Cricksy team produce:

- match previews
- match reviews
- tactical breakdowns
- coach-ready talking points
- podcast episode notes
- short-form social media clips
- stat graphics
- player and team insight reports
- reusable intelligence records for future analysis

The analyst should not only find statistics. The analyst should explain what the numbers mean.

---

## 2. Primary User Roles

### 2.1 Data Analyst / Intelligence Lead

Primary responsibility:
- prepare the evidence, visuals, reports, and insight notes.

Typical tasks:
- search match data
- compare teams and players
- identify trends
- generate graphs
- prepare coach talking points
- flag tactical patterns
- create report exports

### 2.2 Coach / On-Camera Analyst

Primary responsibility:
- translate the data into cricket language for players, fans, and coaches.

Typical tasks:
- review analyst notes
- add coaching interpretation
- explain technical and tactical patterns
- record podcast/video breakdowns
- approve final messaging

### 2.3 Media Producer

Primary responsibility:
- turn analysis into audience-ready content.

Typical tasks:
- select clips
- export graphics
- create thumbnails
- prepare captions
- publish social clips
- organize episode assets

### 2.4 Future Institute Instructor

Primary responsibility:
- turn analyst workflows into teachable modules.

Typical tasks:
- create assignments
- review student analysis
- build analyst training exercises
- produce certification material

---

## 3. Weekly Production Cycle

### Day 1 — Match Selection and Research Setup

Objective:
- decide which match, team, player, or tactical topic will be covered.

Inputs:
- recent matches
- upcoming fixtures
- historical matches
- trending cricket topics
- coach requests
- audience questions

Analyst tasks:
- select target match or topic
- pull scorecard and ball-by-ball data
- identify relevant teams and players
- create an analysis workspace
- assign the episode/topic status as `Research Started`

System needs:
- match search
- tournament filters
- team filters
- player lookup
- workspace creation
- saved research folders

Outputs:
- selected match/topic
- initial research workspace
- list of questions to investigate

Example questions:
- Why did the chase fail?
- Which overs changed the match?
- Which batter handled pressure best?
- Did the bowling plan expose a weakness?
- Was the result caused by skill, tactics, pressure, or conditions?

---

### Day 2 — Data Pull and First Analysis

Objective:
- collect the core numbers and identify the first layer of patterns.

Analyst tasks:
- review innings progression
- review wickets timeline
- compare run rates by phase
- review partnerships
- review dot-ball pressure
- review boundary timing
- review bowling economy by phase
- review dismissal types

System needs:
- innings summary dashboard
- phase analysis dashboard
- player comparison dashboard
- partnership graph
- wickets timeline
- run progression chart
- dot-ball pressure chart

Outputs:
- first analysis notes
- early chart set
- shortlist of possible storylines

Required first-pass visuals:
- match worm graph
- run rate by phase
- wickets timeline
- top partnerships
- dot-ball pressure trend
- boundary frequency by phase

---

### Day 3 — Tactical Breakdown

Objective:
- move from basic statistics to cricket intelligence.

Analyst tasks:
- identify turning points
- analyze matchup advantages
- review bowling changes
- review batting tempo changes
- inspect pressure moments
- identify tactical mistakes or successful adjustments
- prepare coach interpretation notes

System needs:
- matchup engine
- over-by-over pressure index
- bowling spell analysis
- batter phase analysis
- fielding event summary
- dismissal context panel
- AI insight suggestions

Outputs:
- tactical storylines
- coach-ready explanation notes
- evidence-backed claims

Example tactical insights:
- Team A lost control between overs 11 and 15 because dot-ball pressure rose before wickets fell.
- Batter X accelerated well against pace but slowed heavily against spin.
- Bowler Y created pressure even without wickets because his spell reduced boundary options.
- The collapse started before the wickets appeared on the scorecard.

---

### Day 4 — Podcast Preparation Package

Objective:
- convert analysis into a usable recording script and visual package.

Analyst tasks:
- create episode outline
- prepare talking points
- choose final charts
- prepare stat cards
- write coach prompts
- flag clips or timestamps if video is available
- prepare audience-friendly explanations

System needs:
- episode builder
- talking-point generator
- stat card exporter
- chart export to PNG
- PDF brief export
- video timestamp notes
- workspace approval status

Outputs:
- podcast brief
- chart pack
- stat cards
- coach talking points
- social clip ideas

Podcast package should include:
- episode title
- 3 to 5 main talking points
- key match facts
- top tactical insight
- best player analysis
- turning point
- coach discussion prompts
- recommended graphics
- possible short-form clips

---

### Day 5 — Recording Support

Objective:
- support the coach during the podcast or video recording.

Analyst tasks:
- keep match notes available
- provide quick clarifications
- track which visuals were used
- mark strong quotes or moments
- capture follow-up questions

System needs:
- live recording view
- quick search panel
- episode notes panel
- used-visual tracker
- quote marker
- follow-up task list

Outputs:
- recorded episode
- quote list
- clip candidate list
- follow-up analysis tasks

Recording support view should show:
- main talking points
- charts in order
- key stats
- player notes
- coach prompts
- simple explanations

---

### Day 6 — Media Export and Social Clips

Objective:
- turn the episode into short-form and shareable content.

Analyst/media tasks:
- select 3 to 7 short clips
- export stat cards
- write captions
- create thumbnails
- create social summaries
- prepare YouTube description
- archive episode assets

System needs:
- clip idea list
- social caption generator
- graphic export
- episode asset folder
- media checklist
- publish status tracker

Outputs:
- social clips
- graphics
- captions
- thumbnail notes
- published episode record

Recommended weekly social assets:
- 1 main episode post
- 3 short tactical clips
- 2 stat cards
- 1 quote graphic
- 1 carousel explaining the main insight

---

### Day 7 — Review and Knowledge Capture

Objective:
- preserve learning and improve the next production cycle.

Analyst tasks:
- review what worked
- note audience questions
- update reusable insights
- save match patterns
- update player/team intelligence profiles
- create future episode ideas

System needs:
- post-episode review form
- audience feedback notes
- reusable insight library
- player/team profile update flow
- next-topic queue

Outputs:
- production review
- updated intelligence records
- next episode topic shortlist

---

## 4. Analyst Workspace Status Flow

Each analysis workspace should move through clear statuses:

1. `Not Started`
2. `Research Started`
3. `Data Pulled`
4. `First Analysis Complete`
5. `Tactical Review Complete`
6. `Coach Review Ready`
7. `Approved for Recording`
8. `Recorded`
9. `Media Export Complete`
10. `Archived`

No workspace should be marked complete without saved outputs.

---

## 5. Minimum Viable Analyst Outputs

For the first production version, each match/topic workspace should produce:

- match summary
- key moments list
- 3 to 5 talking points
- 3 core charts
- 1 player spotlight
- 1 tactical insight
- 1 coach interpretation section
- 3 social clip ideas
- exportable PDF brief

---

## 6. First Dashboard Priorities

### Priority 1 — Match Intelligence Dashboard

Purpose:
- give analysts a complete view of one match.

Must include:
- match summary
- innings scores
- run progression
- wickets timeline
- partnerships
- phase run rates
- top performers
- key turning points

### Priority 2 — Player Spotlight Dashboard

Purpose:
- prepare player-based podcast or coaching content.

Must include:
- recent form
- runs/wickets summary
- strike rate or economy trend
- phase performance
- dismissal patterns
- matchup notes
- pressure performance

### Priority 3 — Team Tactical Dashboard

Purpose:
- compare team strengths and weaknesses.

Must include:
- powerplay performance
- middle-over performance
- death-over performance
- collapse patterns
- bowling phase economy
- batting tempo
- fielding impact

### Priority 4 — Podcast Prep Dashboard

Purpose:
- organize all analysis into a recording-ready format.

Must include:
- episode outline
- talking points
- selected charts
- coach prompts
- social clip ideas
- export buttons
- approval status

---

## 7. First Visualization Priorities

The first version should prioritize visuals that are easy for viewers to understand.

Required first visuals:

1. Run progression graph
2. Wickets timeline
3. Phase run-rate comparison
4. Partnership chart
5. Dot-ball pressure chart
6. Boundary frequency chart
7. Player comparison card
8. Bowler spell impact card
9. Match turning-point card
10. Podcast stat card

Avoid starting with overly complex visuals unless they directly support the podcast story.

---

## 8. AI Assistance Requirements

The AI should support the analyst, not replace the analyst.

### First AI Features

- summarize match events
- suggest key talking points
- detect possible turning points
- suggest player spotlight candidates
- generate coach-friendly explanations
- generate social clip ideas
- draft podcast episode outlines
- draft captions from approved analysis

### AI Guardrails

The AI must:
- cite the match data it used
- avoid inventing unsupported claims
- label uncertain insights as tentative
- separate facts from interpretation
- allow coach approval before publishing
- keep all generated content editable

---

## 9. Data Access Requirements

The analyst section must eventually access:

- all live matches
- all completed matches
- historical imported matches
- team records
- player records
- tournament records
- venue records
- delivery-level data
- video-tagged events
- AI-tagged events

For the first version, it must at minimum access:

- completed matches
- innings summaries
- player scorecards
- team scorecards
- ball-by-ball deliveries where available

---

## 10. Export Requirements

### First Export Formats

- PDF podcast brief
- PNG stat cards
- CSV chart data
- Markdown episode notes

### Future Export Formats

- presentation slides
- video overlays
- OBS graphics
- YouTube description template
- social carousel package
- coach report bundle

---

## 11. Approval Gates

Before recording:

- data reviewed
- charts reviewed
- claims checked
- coach notes prepared
- unsupported claims removed
- episode outline approved

Before publishing:

- final clips selected
- captions reviewed
- graphics checked
- branding checked
- sensitive claims reviewed
- episode archived

---

## 12. Podcast Episode Template

Each podcast episode should follow this structure:

1. Opening hook
2. Match/topic context
3. Key scoreboard facts
4. Main tactical question
5. Analyst evidence
6. Coach interpretation
7. Player spotlight
8. Turning point
9. What teams/players can learn
10. Closing takeaway
11. Social clip callouts

---

## 13. Example Weekly Episode Package

### Episode Title
Why the Chase Failed Before the Wickets Fell

### Main Question
Was the collapse caused by poor shot selection, pressure buildup, or a tactical bowling plan?

### Required Data
- innings progression
- dot-ball percentage by phase
- wickets timeline
- partnership breakdown
- batter strike-rate trend
- bowler spell impact

### Visuals
- run progression graph
- wickets timeline
- dot-ball pressure chart
- turning-point card

### Coach Talking Points
- how pressure changes batting decision-making
- why dot balls create false attacking shots
- how bowlers build dismissals before the wicket ball
- what young players can learn from the collapse

### Social Clips
- The over that changed the match
- Why dot balls are hidden pressure
- This wicket started three overs before it happened

---

## 14. Product Build Implications

This workflow suggests the analyst section should be built in this order:

1. Match access and filtering
2. Match intelligence dashboard
3. Core chart generation
4. Analyst workspace and saved notes
5. Podcast prep dashboard
6. PDF and PNG exports
7. AI talking-point assistant
8. Approval workflow
9. Social media export helper
10. Historical intelligence expansion

---

## 15. Success Criteria

The first version is successful when the Cricksy team can use it to produce one complete analysis package for one match without manually rebuilding everything from scratch.

Minimum success test:

- select one completed match
- generate match summary
- generate 3 core visuals
- create 5 talking points
- prepare coach prompts
- export a PDF brief
- export at least one PNG stat card
- save the workspace for later review

---

## 16. Relationship to Cricksy Analyst System Blueprint v1

This workflow operationalizes `CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`.

The blueprint defines what the analyst system is.

This workflow defines how the analyst system is used every week to create cricket intelligence outputs.
