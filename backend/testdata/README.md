# Test Data Directory

This directory contains sample scorecard files for testing the OCR upload pipeline.

## Files

### sample_scorecard.txt
Plain text sample of a scorecard that simulates OCR output. Can be used for testing the parser without requiring actual OCR processing.

### sample_scorecard_template.md
Template showing the expected format for scorecards that can be OCR'd successfully.

## Usage

These files can be used to test:
1. The scorecard parser (`parse_scorecard.py`)
2. The upload workflow with mock files
3. Frontend upload and review UI

## Adding New Test Files

When adding new test files:
1. Use realistic cricket scorecard formats
2. Include various edge cases (extras, wickets, bowling changes)
3. Document the expected parsing output in comments
4. Keep files small (<1MB) to avoid bloating the repository
