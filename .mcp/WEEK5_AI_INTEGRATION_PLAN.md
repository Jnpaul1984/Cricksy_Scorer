# Week 5 – AI Integration Phase 1 Implementation Plan

## Current State Assessment

✅ **Existing AI Infrastructure:**
- `WinProbabilityPredictor` class with rule-based predictions
- ML model service with XGBoost models (win_probability, score_predictor)
- AI commentary service (`ai_commentary.py`)
- Player insights service (`ai_player_insights.py`)
- Match AI service (`match_ai_service.py`)
- Match context service (`match_context_service.py`)
- ML features building (`ml_features.py`)
- Agent budget tracking (`agent_budget.py`)

✅ **Frontend Components:**
- Win probability widget already exists
- State management ready in Pinia store

---

## Week 5 Deliverables Breakdown

### 1. AI Basics (Core Features)

#### 1.1 Win Probability (API connected) ✅ MOSTLY DONE
- **Status:** Already implemented via `WinProbabilityPredictor`
- **What's needed:**
  - [ ] API endpoint to expose `/games/{id}/predictions/win-probability`
  - [ ] Real-time Socket.IO emission of predictions with each delivery
  - [ ] Frontend widget to display probability curve over time
- **Effort:** 2-3 hours

#### 1.2 Innings Grade (NEW)
- **Description:** Letter grade (A+, A, B, C, D) for batting performance in innings
- **Factors:**
  - Run rate vs par score
  - Wickets lost ratio
  - Strike rotation quality
  - Boundary percentage
- **What to build:**
  - [ ] `InningsGradeCalculator` class in `services/`
  - [ ] Grade logic (A+: >150% par, A: 130-150%, B: 100-130%, C: 70-100%, D: <70%)
  - [ ] API endpoint: `GET /games/{id}/innings/{inning_num}/grade`
  - [ ] Display grade badge in Scorer UI + Viewer
- **Effort:** 4-5 hours

#### 1.3 Pressure Mapping (NEW)
- **Description:** Heat map visualization showing high-pressure moments
- **Factors:**
  - Dot ball streaks
  - Wicket timings
  - Target gap widening/narrowing
  - Required run rate spikes
- **What to build:**
  - [ ] `PressureAnalyzer` class to identify pressure points
  - [ ] Score pressure map (array of pressure values by delivery)
  - [ ] API endpoint: `GET /games/{id}/pressure-map`
  - [ ] Frontend chart component (Highcharts/Chart.js)
- **Effort:** 5-6 hours

#### 1.4 Phase-Based Predictions (NEW)
- **Description:** Break match into phases (powerplay, middle, death, mini-death for 2nd inns)
- **Factors by phase:**
  - Powerplay (0-6 overs): Expected runs, wicket burnout rate
  - Middle (7-15 overs): Acceleration rate, 3rd man patterns
  - Death (16-20 overs): Boundary dot ratio, last-over context
  - Mini-death (2nd inns, last 3 overs): Finishing rate needed
- **What to build:**
  - [ ] `MatchPhaseAnalyzer` to segment match
  - [ ] Phase-specific prediction logic
  - [ ] API endpoint: `GET /games/{id}/phases`
  - [ ] Frontend phase timeline component
- **Effort:** 6-7 hours

---

### 2. Player Pro Tier Features

#### 2.1 AI Career Summary (NEW)
- **Description:** Auto-generated player career highlights and stats
- **Data:**
  - Best innings
  - Consistency score (std dev of runs)
  - Specialization (opener, finisher, bowler, all-rounder)
  - Recent form (last 5 matches trend)
- **What to build:**
  - [ ] `PlayerCareerAnalyzer` service
  - [ ] Database view for aggregated player stats
  - [ ] API endpoint: `GET /players/{id}/ai-summary`
  - [ ] Player profile page section
- **Effort:** 5-6 hours

#### 2.2 Monthly Improvement Algo (NEW)
- **Description:** Track player skill progression month-over-month
- **Metrics:**
  - Batting average trend
  - Strike rate improvement
  - Consistency (variance reduction)
  - Role adaptation (if role changed)
- **What to build:**
  - [ ] `PlayerImprovementTracker` service
  - [ ] Monthly aggregation queries
  - [ ] Growth rate calculation (% improvement)
  - [ ] API endpoint: `GET /players/{id}/improvement-trend`
  - [ ] Chart: Line graph showing month-over-month progress
- **Effort:** 4-5 hours

---

### 3. Coach Pro Tier Features

#### 3.1 Tactical Suggestion Engine v1 (NEW)
- **Description:** AI-powered real-time suggestions for coaches during scoring
- **Sub-components:**

##### 3.1.1 Best Bowler Now
- When to bowl next delivery: Recommends pitcher with best stats vs batter
- Data: Bowler economy, dismissals vs this batter type
- API: `GET /games/{id}/suggestions/best-bowler`

##### 3.1.2 Weakness vs Bowler Type
- Predicts what delivery type will work: (pace, spin, length)
- Data: Historical dismissal patterns, batter performance by ball type
- API: `GET /games/{id}/suggestions/weakness-analysis`

##### 3.1.3 Recommended Fielding Setup
- Positions for next bowler based on batter's scoring zones
- Data: Heat map of batter runs, bowler release points
- API: `GET /games/{id}/suggestions/fielding-setup`

**What to build:**
  - [ ] `TacticalSuggestionEngine` class
  - [ ] Dismissal pattern analysis
  - [ ] Batter strength/weakness profiles
  - [ ] Fielding zone recommendations
  - [ ] Real-time suggestion sidebar in Coach Notebook
- **Effort:** 8-10 hours

#### 3.2 Training Drill Suggestions (NEW)
- **Description:** Rules-based training drills based on identified weaknesses
- **Examples:**
  - High dot rate → "Practice 50 consecutive dot balls"
  - Weak to pace → "Face 30 deliveries of 140+ kmph pace"
  - Boundary struggling → "Hit 20 sixes in practice nets"
- **What to build:**
  - [ ] `TrainingDrillGenerator` rules engine
  - [ ] Drill templates database
  - [ ] Severity scoring (high/medium/low priority)
  - [ ] API endpoint: `GET /players/{id}/suggested-drills`
  - [ ] Coach Notebook drill recommendation section
- **Effort:** 3-4 hours

---

### 4. Analyst Pro Tier Features

#### 4.1 AI Dismissal Pattern Detection (NEW)
- **Description:** Automatic clustering of dismissal modes by context
- **Patterns to detect:**
  - "Dot-ball pressure followed by aggressive shot"
  - "Pace variation catching batter off guard"
  - "Yorker delivery type"
  - "Batter too early in decision"
- **What to build:**
  - [ ] `DismissalPatternAnalyzer` class
  - [ ] Sequence detector (previous 3 balls before dismissal)
  - [ ] API endpoint: `GET /games/{id}/dismissal-patterns`
  - [ ] Analyst Workspace: Dismissal pattern grid/timeline
- **Effort:** 5-6 hours

#### 4.2 AI Heatmap Overlays (NEW)
- **Description:** Pitch map overlays showing scoring/dismissal zones
- **Heatmaps:**
  - Runs by pitch location
  - Dismissals by pitch location
  - Bowler release point zones
- **What to build:**
  - [ ] `PitchHeatmapGenerator` service
  - [ ] Pixel-to-pitch-coordinate mapping
  - [ ] Heatmap aggregation logic
  - [ ] API endpoint: `GET /players/{id}/pitch-heatmaps`
  - [ ] Frontend SVG/Canvas pitch visualization
- **Effort:** 7-8 hours

#### 4.3 AI Ball Type Clustering (NEW)
- **Description:** Automatic detection of ball type (pace, spin, length, line)
- **ML approach:**
  - Train on delivery metadata (angle, speed, spin)
  - Cluster similar deliveries
  - Label clusters (e.g., "short-ball cluster", "yorker-cluster")
- **What to build:**
  - [ ] `BallTypeClusterer` using K-means or custom rules
  - [ ] Ball metadata enrichment
  - [ ] API endpoint: `GET /games/{id}/ball-clusters`
  - [ ] Analyst report: Ball type effectiveness matrix
- **Effort:** 6-7 hours

---

### 5. Org Pro Tier Features

#### 5.1 Basic Sponsor Rotation Logic (NEW)
- **Description:** Auto-rotate sponsor branding on viewer throughout match
- **Rules:**
  - Each sponsor gets X exposures per match
  - Rotate every N overs
  - Increase during high-engagement moments (wickets, boundaries)
- **What to build:**
  - [ ] `SponsorRotationEngine` service
  - [ ] Rotation schedule builder
  - [ ] Exposure tracking DB
  - [ ] API endpoint: `POST /organizations/{org_id}/sponsor-schedule`
  - [ ] Viewer integration: Dynamic brand swap
- **Effort:** 4-5 hours

#### 5.2 Branding (Logo + Theme) (NEW)
- **Description:** White-label theming for org-specific branding
- **Features:**
  - Custom logo upload
  - Theme color picker (primary, secondary, accent)
  - Font/typography options
  - Apply to all viewer templates
- **What to build:**
  - [ ] `BrandingService` to store org themes
  - [ ] Theme CSS generator
  - [ ] Frontend theme provider (CSS variables)
  - [ ] Org settings page: Branding panel
  - [ ] Database: OrgBrandingTheme table
- **Effort:** 3-4 hours

---

## Implementation Priority & Phasing

### Phase 1 (Days 1-2): Foundations
1. Win Probability API + Socket.IO real-time ✅
2. Innings Grade Calculator
3. Player Career Summary

### Phase 2 (Days 3-4): Mid-Tier Features
4. Pressure Mapping
5. Phase-Based Predictions
6. Monthly Improvement Tracker

### Phase 3 (Days 5): Coach & Analyst Features
7. Tactical Suggestion Engine (Best Bowler, Weakness Analysis, Fielding)
8. Training Drill Suggestions
9. Dismissal Pattern Detection

### Phase 4 (Days 6): Advanced Analytics
10. AI Heatmap Overlays
11. Ball Type Clustering

### Phase 5 (Day 7): Org Features + Polish
12. Sponsor Rotation Logic
13. Branding System
14. Testing & Integration

---

## Database Changes Needed

```sql
-- Innings Grade tracking
CREATE TABLE innings_grades (
    id SERIAL PRIMARY KEY,
    game_id INT,
    inning_num INT,
    grade VARCHAR(3),  -- A+, A, B, C, D
    grade_value FLOAT,
    timestamp DATETIME,
    FOREIGN KEY (game_id) REFERENCES games(id)
);

-- Pressure points
CREATE TABLE pressure_points (
    id SERIAL PRIMARY KEY,
    game_id INT,
    delivery_num INT,
    pressure_score FLOAT,  -- 0-100
    reason VARCHAR(255),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

-- Player improvement tracking
CREATE TABLE player_monthly_stats (
    id SERIAL PRIMARY KEY,
    player_id INT,
    year INT,
    month INT,
    matches_played INT,
    runs_scored INT,
    avg_score FLOAT,
    strike_rate FLOAT,
    consistency_score FLOAT,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Ball clusters
CREATE TABLE ball_type_clusters (
    id SERIAL PRIMARY KEY,
    game_id INT,
    cluster_label VARCHAR(50),  -- "short", "yorker", "spin", etc
    deliveries_in_cluster INT,
    effectiveness_score FLOAT,
    FOREIGN KEY (game_id) REFERENCES games(id)
);

-- Org branding
CREATE TABLE org_branding_themes (
    id SERIAL PRIMARY KEY,
    org_id INT,
    logo_url VARCHAR(255),
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    font_family VARCHAR(50),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);
```

---

## Testing Strategy

1. **Unit Tests:** Each calculator (GradeCalculator, PressureAnalyzer, etc.) gets test suite
2. **Integration Tests:** Predictions flow end-to-end through Socket.IO
3. **Data Validation:** Real match data validation against expected ranges
4. **Performance:** Prediction calculations must stay < 100ms per delivery

---

## Success Criteria

✅ All 12 AI features functional and tested
✅ No performance degradation (delivery scoring still <1s)
✅ All features integrated into appropriate tier UIs
✅ Real-time Socket.IO updates working smoothly
✅ Beta tester feedback on AI accuracy > 80% positive

---

## Next Steps

1. Start with **Win Probability API endpoint** (today)
2. Build **Innings Grade Calculator** (tomorrow)
3. Implement **Pressure Mapping** (day 3)
4. Continue through priority phases...

Ready to begin Phase 1?
