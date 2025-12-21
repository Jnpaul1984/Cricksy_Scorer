# Week 5 – AI Integration Phase 1 Implementation Progress

**Status:** 🚀 Week 5 implementation started
**Last Updated:** December 18, 2025
**Target Completion:** End of Week 5 (7 days from Week 3 completion)

---

## 📊 Phase Breakdown

### Phase 1: Foundations (Days 1-2) - IN PROGRESS ✅ PARTIALLY COMPLETE

#### 1.1 Win Probability (API connected)
- **Status:** ✅ **COMPLETE** (Already implemented in codebase)
- **Components:**
  - [x] API endpoint: `GET /games/{game_id}/predictions/win-probability`
  - [x] Real-time Socket.IO emission: `prediction:update` event on every delivery
  - [x] Prediction calculation via `WinProbabilityPredictor.calculate_win_probability()`
  - [x] Error handling (graceful fallback if prediction fails)
  - [x] Response includes: batting/bowling team probabilities, confidence, factors, team names
- **Location:**
  - API: [backend/routes/prediction.py](backend/routes/prediction.py#L21)
  - Emission: [backend/routes/gameplay.py](backend/routes/gameplay.py#L1197-L1219)
  - Service: [backend/services/prediction_service.py](backend/services/prediction_service.py)
- **Testing:**
  - [x] Unit tests in `backend/tests/test_prediction_service.py`
  - [x] Integration tests in `backend/tests/test_ml_integration.py`
- **Frontend Integration:** TODO (Next step - create/update widget)

#### 1.2 Innings Grade (NEW)
- **Status:** ⏳ NOT STARTED
- **Effort:** 4-5 hours
- **Subtasks:**
  - [ ] Create `InningsGradeCalculator` class in `backend/services/`
  - [ ] Implement grade logic:
    - A+: >150% of par score
    - A: 130-150% of par score
    - B: 100-130% of par score
    - C: 70-100% of par score
    - D: <70% of par score
  - [ ] Factor in wickets lost ratio (penalty for high losses)
  - [ ] Factor in boundary percentage
  - [ ] Create API endpoint: `GET /games/{id}/innings/{inning_num}/grade`
  - [ ] Add database table: `innings_grades` (tracks historical grades)
  - [ ] Emit real-time grade on innings completion
  - [ ] Frontend: Add grade badge to Scorer UI + Viewer
- **Database Changes:**
  ```sql
  CREATE TABLE innings_grades (
      id SERIAL PRIMARY KEY,
      game_id INT,
      inning_num INT,
      grade VARCHAR(3),  -- A+, A, B, C, D
      grade_value FLOAT,
      timestamp DATETIME,
      FOREIGN KEY (game_id) REFERENCES games(id)
  );
  ```

#### 1.3 Pressure Mapping (NEW)
- **Status:** ⏳ NOT STARTED
- **Effort:** 5-6 hours
- **Subtasks:**
  - [ ] Create `PressureAnalyzer` class to identify pressure points
  - [ ] Calculate pressure score for each delivery:
    - High dot ball streaks (3+ consecutive dots)
    - Wicket timings (sudden loss of key player)
    - Target gap widening (2nd inns)
    - Required run rate spikes
  - [ ] Return pressure map array (delivery_num → pressure_score)
  - [ ] API endpoint: `GET /games/{id}/pressure-map`
  - [ ] Database table: `pressure_points` (for analytics)
  - [ ] Frontend: Pressure timeline chart (Chart.js/Highcharts)
- **Database Changes:**
  ```sql
  CREATE TABLE pressure_points (
      id SERIAL PRIMARY KEY,
      game_id INT,
      delivery_num INT,
      pressure_score FLOAT,  -- 0-100
      reason VARCHAR(255),
      FOREIGN KEY (game_id) REFERENCES games(id)
  );
  ```

#### 1.4 Phase-Based Predictions (NEW)
- **Status:** ⏳ NOT STARTED
- **Effort:** 6-7 hours
- **Subtasks:**
  - [ ] Create `MatchPhaseAnalyzer` to segment match into phases
  - [ ] Define phases by overs:
    - Powerplay: 0-6 overs
    - Middle: 7-15 overs
    - Death: 16-20 overs
    - Mini-death (2nd inns): Last 3 overs
  - [ ] Calculate phase-specific metrics:
    - Expected run rate for phase
    - Wicket burnout rate
    - Acceleration rate
  - [ ] API endpoint: `GET /games/{id}/phases`
  - [ ] Database: Phase summary in game record
  - [ ] Frontend: Phase timeline visualization
- **Response Structure:**
  ```json
  {
    "phases": [
      {
        "name": "powerplay",
        "overs": "0-6",
        "runs": 45,
        "wickets": 0,
        "avg_rr": 7.5,
        "expected_rr": 8.0,
        "status": "completed"
      },
      ...
    ]
  }
  ```

---

### Phase 2: Mid-Tier Features (Days 3-4) - NOT STARTED

#### 2.1 AI Career Summary (Player Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 5-6 hours
- **Subtasks:**
  - [ ] Create `PlayerCareerAnalyzer` service
  - [ ] Query aggregated player stats:
    - Best innings ever
    - Consistency score (standard deviation of runs)
    - Specialization detection (opener, middle-order, finisher, bowler)
    - Recent form (last 5 matches trend)
  - [ ] API endpoint: `GET /players/{id}/ai-summary`
  - [ ] Database view: Aggregated player stats
  - [ ] Frontend: Player profile page → "AI Summary" section
  - [ ] Response includes: career highlights, specialization badge, form indicator

#### 2.2 Monthly Improvement Tracker (Player Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 4-5 hours
- **Subtasks:**
  - [ ] Create `PlayerImprovementTracker` service
  - [ ] Monthly aggregation logic:
    - Matches played per month
    - Average runs scored
    - Strike rate trend
    - Consistency (variance reduction)
  - [ ] Calculate growth rate (% improvement month-over-month)
  - [ ] API endpoint: `GET /players/{id}/improvement-trend`
  - [ ] Database: `player_monthly_stats` table
  - [ ] Frontend: Line chart showing 12-month progression
  - [ ] Highlight months with biggest improvement
- **Database Changes:**
  ```sql
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
  ```

---

### Phase 3: Coach & Analyst Features (Day 5) - NOT STARTED

#### 3.1 Tactical Suggestion Engine v1 (Coach Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 8-10 hours
- **Sub-features:**

##### 3.1.1 Best Bowler Now
- [ ] Recommend next bowler based on:
  - Dismissals vs this batter type
  - Economy rate vs similar batters
  - Recent form
- API: `GET /games/{id}/suggestions/best-bowler`

##### 3.1.2 Weakness vs Bowler Type
- [ ] Analyze batter weaknesses:
  - Struggles against pace vs spin
  - Weak to yorkers, short balls, line & length
  - Scoring patterns by deliverytype
- API: `GET /games/{id}/suggestions/weakness-analysis`

##### 3.1.3 Recommended Fielding Setup
- [ ] Suggest fielding positions based on:
  - Batter's scoring zones (heatmap)
  - Bowler's release point patterns
  - Match phase (powerplay more aggressive)
- API: `GET /games/{id}/suggestions/fielding-setup`

**Implementation:**
- [ ] Create `TacticalSuggestionEngine` service
- [ ] Dismissal pattern analyzer
- [ ] Batter strength/weakness profiles
- [ ] Fielding zone calculator
- [ ] Real-time suggestions sidebar in Coach Notebook
- [ ] Database: `dismissal_patterns`, `batter_profiles`

#### 3.2 Training Drill Suggestions (Coach Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 3-4 hours
- **Subtasks:**
  - [ ] Create rules-based drill generator
  - [ ] Detect weaknesses from performance data
  - [ ] Match to drill templates:
    - High dot rate → "Practice 50 consecutive dot balls"
    - Weak to pace → "Face 30 deliveries of 140+ kmph"
    - Boundary struggling → "Hit 20 sixes in nets"
  - [ ] Score drill priority (high/medium/low)
  - [ ] API endpoint: `GET /players/{id}/suggested-drills`
  - [ ] Frontend: Coach Notebook → Drill recommendations panel
- **Database:** Drill templates table

#### 3.3 AI Dismissal Pattern Detection (Analyst Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 5-6 hours
- **Subtasks:**
  - [ ] Analyze dismissal contexts
  - [ ] Identify patterns:
    - "Dot ball pressure followed by aggressive shot"
    - "Pace variation catching batter off guard"
    - "Yorker delivery type"
    - "Batter too early in decision-making"
  - [ ] Sequence detector (previous 3 balls before dismissal)
  - [ ] API endpoint: `GET /games/{id}/dismissal-patterns`
  - [ ] Frontend: Analyst Workspace → Dismissal pattern grid
  - [ ] Database: `dismissal_patterns` table

---

### Phase 4: Advanced Analytics (Day 6) - NOT STARTED

#### 4.1 AI Heatmap Overlays (Analyst Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 7-8 hours
- **Subtasks:**
  - [ ] Create pitch coordinate system (0-22 yards, 4-10 feet width)
  - [ ] Heatmaps to generate:
    - Runs by pitch location
    - Dismissals by pitch location
    - Bowler release point zones
  - [ ] Aggregation logic (bin deliveries by coordinates)
  - [ ] API endpoint: `GET /players/{id}/pitch-heatmaps`
  - [ ] Frontend: SVG/Canvas pitch visualization
  - [ ] Overlay heatmap on pitch diagram
- **Database:** Pitch coordinate mapping

#### 4.2 AI Ball Type Clustering (Analyst Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 6-7 hours
- **Subtasks:**
  - [ ] Create `BallTypeClusterer` class
  - [ ] Features for clustering:
    - Delivery angle
    - Speed (if available)
    - Spin (if available)
    - Length (full, good, short, yorker)
    - Line (off, leg, middle)
  - [ ] K-means clustering to identify groups
  - [ ] Label clusters (e.g., "short-ball cluster", "yorker-cluster")
  - [ ] API endpoint: `GET /games/{id}/ball-clusters`
  - [ ] Analyst report: Ball type effectiveness matrix
  - [ ] Database: `ball_type_clusters` table

---

### Phase 5: Org Features + Polish (Day 7) - NOT STARTED

#### 5.1 Basic Sponsor Rotation Logic (Org Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 4-5 hours
- **Subtasks:**
  - [ ] Create `SponsorRotationEngine` service
  - [ ] Rotation rules:
    - Each sponsor gets X exposures per match
    - Rotate every N overs
    - Increase during high-engagement moments (wickets, boundaries)
  - [ ] Exposure tracking DB
  - [ ] API endpoint: `POST /organizations/{org_id}/sponsor-schedule`
  - [ ] Viewer integration: Dynamic sponsor brand swap
  - [ ] Database: Sponsor rotation tracking

#### 5.2 Branding (Logo + Theme) (Org Pro)
- **Status:** ⏳ NOT STARTED
- **Effort:** 3-4 hours
- **Subtasks:**
  - [ ] Create `BrandingService`
  - [ ] Theming features:
    - Logo upload
    - Color picker (primary, secondary, accent)
    - Font family selection
  - [ ] Theme CSS generator
  - [ ] Database: `org_branding_themes` table
  - [ ] Frontend: Org settings → Branding panel
  - [ ] Apply theme to all viewer templates
- **Database Changes:**
  ```sql
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

#### 5.3 Integration & Polish
- [ ] End-to-end testing of all AI features
- [ ] Performance optimization (all predictions <100ms)
- [ ] Error handling & logging
- [ ] Beta tester feedback collection

---

## 🎯 Daily Standup Template

### Today's Focus
- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3

### Blockers
- None yet

### PRs/Commits
- (Update as work progresses)

---

## 📈 Success Metrics

✅ **All 12 AI features functional**
✅ **Real-time Socket.IO updates working smoothly**
✅ **No performance degradation** (delivery scoring stays <1s)
✅ **All features integrated into appropriate tier UIs**
✅ **Beta tester feedback on AI accuracy > 80% positive**

---

## 📝 Implementation Notes

### Key Architecture Decisions
1. **Prediction fallback**: ML models gracefully fall back to rule-based if unavailable
2. **Real-time emission**: Socket.IO events sent on every delivery (prediction:update)
3. **Tier-gated features**: Each feature gated to appropriate subscription tier
4. **Database persistence**: Historical data stored for analytics/reporting

### Performance Constraints
- Prediction calc: <100ms per delivery ✅
- Socket.IO emission: Non-blocking, error-contained ✅
- Database queries: Optimized with indexes
- Frontend rendering: Lazy-loaded charts

### Testing Strategy
1. **Unit tests**: Each calculator class
2. **Integration tests**: Prediction flow through Socket.IO
3. **Data validation**: Real match validation against expected ranges
4. **Performance**: Load testing with concurrent viewers/scorers

---

## 🚀 Next Steps

**Immediate (Today):**
1. ✅ Verify Win Probability API is working end-to-end
2. ⏳ Build frontend Win Probability widget
3. ⏳ Test real-time Socket.IO emission

**This Week:**
1. Build Innings Grade Calculator (Days 1-2)
2. Implement Pressure Mapping (Days 3-4)
3. Build Tactical Suggestion Engine (Day 5)
4. Add heatmap + clustering (Day 6)
5. Polish + testing (Day 7)

---

## 📂 File Structure

**Backend Services:**
- `backend/services/prediction_service.py` - Win probability (✅ exists)
- `backend/services/ml_model_service.py` - ML model loading
- `backend/services/ml_features.py` - Feature building
- `backend/services/game_helpers.py` - Game state management

**Backend Routes:**
- `backend/routes/prediction.py` - Prediction API (✅ exists)
- `backend/routes/gameplay.py` - Scoring + emissions (✅ already emitting)
- `backend/routes/coach_pro.py` - Coach-specific endpoints (TODO)
- `backend/routes/analyst_pro.py` - Analyst-specific endpoints (TODO)

**Frontend Components:**
- `frontend/src/components/PredictionWidget.vue` (TODO - create)
- `frontend/src/components/InningsGradeBadge.vue` (TODO - create)
- `frontend/src/components/PressureChart.vue` (TODO - create)
- `frontend/src/stores/gameStore.ts` - Already has prediction:update listener

**Tests:**
- `backend/tests/test_prediction_service.py` (✅ exists)
- `backend/tests/test_ml_integration.py` (✅ exists)

---

## 🎓 Learning Resources

- [Win Probability Prediction](../docs/AI_PREDICTION_FEATURE.md)
- [ML Model Training](../backend/TRAINING_DATA_MANIFEST.md)
- [Architecture Overview](../docs/continuous_improvement_guide.md)
