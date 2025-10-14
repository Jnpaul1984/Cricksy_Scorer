# Include CI fixtures required by tests/ci_match/test_full_match.py
RUN mkdir -p /app/tests/ci_match/fixtures
COPY backend/tests/ci_smoke/fixtures/first_innings_120.json /app/tests/ci_match/fixtures/first_innings_120.json
COPY backend/tests/ci_smoke/fixtures/second_innings_120.json /app/tests/ci_match/fixtures/second_innings_120.json
