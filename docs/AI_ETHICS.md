# AI Ethics and Privacy Policy

## Purpose

This document outlines the ethical guidelines, privacy policies, and consent requirements for AI-powered features in the Cricksy Scorer application, particularly for uploaded media processing and OCR functionality.

## Core Principles

### 1. Human-in-the-Loop

All AI-generated outputs must be reviewed and confirmed by a human before being applied to the permanent record.

**Implementation**:
- OCR results are marked as "requires verification"
- Users must explicitly review parsed data before applying
- Manual confirmation required via `confirmation: true` flag
- Ability to reject or modify AI-generated data

**Rationale**: Cricket scorekeeping requires high accuracy. AI assists but doesn't replace human judgment.

### 2. Transparency

Users must understand when AI is being used and how their data is processed.

**Implementation**:
- Clear labeling of AI-generated content
- Confidence scores displayed where available
- Processing status visible to users
- Documentation of OCR capabilities and limitations

**Rationale**: Users deserve to know what technology is processing their data.

### 3. Privacy by Design

User privacy is prioritized throughout the data lifecycle.

**Implementation**:
- Minimal data collection (only what's necessary)
- Encrypted storage and transmission
- Access controls on uploaded files
- Data retention policies
- Right to deletion

**Rationale**: Sports data may contain sensitive information about minors and individuals.

### 4. No Bias or Discrimination

AI systems must not discriminate based on protected characteristics.

**Implementation**:
- OCR trained on diverse scorecard formats
- No player profiling or biometric analysis
- Equal treatment of all teams and individuals
- Regular bias audits

**Rationale**: Sports should be inclusive and fair.

## Upload and Media Processing

### Consent Requirements

#### Before Upload
Users must be informed:
- What will happen to uploaded files
- How OCR processing works
- That files are stored temporarily
- Who can access the files
- How to delete uploaded files

**Example Consent Text**:
```
By uploading this file, you confirm that:
- You have the right to upload this scorecard
- You understand the file will be processed using AI/OCR
- The extracted data will require your verification before use
- Files are stored securely and can be deleted upon request
- No personal data will be used for purposes other than scorekeeping
```

#### During Processing
Users should see:
- Processing status (real-time updates)
- What stage the file is in (uploading, OCR, parsing)
- Estimated time remaining

#### Before Applying
Users must:
- Review all extracted data
- Verify accuracy against original scorecard
- Explicitly confirm before data is saved
- Have option to reject and re-upload

### Data Retention

**Uploaded Files**:
- Stored for **30 days** after upload
- Automatically deleted unless user requests earlier deletion
- Can be deleted immediately after successful application
- Retention period configurable via `UPLOAD_RETENTION_DAYS`

**Parsed Data**:
- Stored permanently once applied (as game data)
- Not stored if rejected by user
- No raw OCR text stored (only structured data)

**Metadata**:
- Upload logs kept for **90 days** (audit trail)
- No personally identifiable information in logs
- IP addresses anonymized

### Access Control

**Who can access uploaded files**:
- Only the uploader (via session ID)
- System administrators (for support/debugging)
- Automated OCR worker (during processing only)

**Who cannot access**:
- Other users
- Third parties
- AI training systems (files are NOT used to train models)

**Security measures**:
- Presigned URLs with short expiration (1 hour)
- Private S3 buckets (no public access)
- Encryption in transit (HTTPS/TLS)
- Encryption at rest (S3 encryption)

## AI/OCR Capabilities and Limitations

### What the OCR Can Do

✓ Extract text from scorecard images
✓ Identify team names (with low-medium confidence)
✓ Extract basic scores (runs/wickets)
✓ Parse tabular data (when clearly formatted)

### What the OCR Cannot Do

✗ Understand context or nuance
✗ Validate cricket rules
✗ Identify players from photos
✗ Read very poor quality images
✗ Handle all scorecard formats perfectly
✗ Make decisions about game outcomes

### Confidence Levels

All OCR results include confidence indicators:
- **High**: Clear text, good quality, standard format
- **Medium**: Some ambiguity, requires verification
- **Low**: Poor quality or unusual format, manual entry recommended

**Current prototype**: All results marked as "low" confidence requiring full manual review.

## Forbidden Use Cases

The AI/OCR system **must not** be used for:

### 1. Biometric Profiling
- ✗ Facial recognition of players
- ✗ Body measurement analysis
- ✗ Identity verification
- ✗ Demographic inference

**Rationale**: Protects privacy and prevents surveillance.

### 2. Automated Decision Making
- ✗ Automatic game result determination
- ✗ Player ranking without human review
- ✗ Automated penalties or sanctions
- ✗ Any decision affecting individuals without human oversight

**Rationale**: Maintains human accountability.

### 3. Commercial Exploitation
- ✗ Selling uploaded images to third parties
- ✗ Using uploads to train commercial AI models
- ✗ Data mining for advertising
- ✗ Creating derivative datasets for sale

**Rationale**: User data belongs to users.

### 4. Surveillance or Monitoring
- ✗ Tracking individuals across uploads
- ✗ Building profiles of scorekeepers
- ✗ Monitoring user behavior beyond system usage
- ✗ Sharing data with law enforcement without warrant

**Rationale**: Prevents abuse of trust.

### 5. Discrimination
- ✗ Different processing quality based on team/player
- ✗ Biased parsing algorithms
- ✗ Access restrictions based on protected characteristics

**Rationale**: Ensures fairness.

## User Rights

### Right to Access
Users can request:
- List of their uploaded files
- Status of all their uploads
- Parsed data from their uploads

**How**: Via API endpoint `/api/uploads/status/{upload_id}`

### Right to Deletion
Users can request deletion of:
- Specific uploaded files
- All their uploaded files
- Associated metadata

**How**: Contact system administrator or use delete endpoint (to be implemented)

### Right to Correction
Users can:
- Reject incorrect OCR results
- Manually correct parsed data
- Re-upload with corrections

**How**: Via frontend review interface

### Right to Opt-Out
Users can:
- Disable OCR processing for their uploads
- Use manual data entry instead
- Request feature be disabled for their account

**How**: Via feature flag or account settings

### Right to Portability
Users can:
- Export their uploaded scorecards
- Download parsed data in standard format
- Transfer data to other systems

**How**: Via API or bulk export (to be implemented)

## Data Security

### Encryption

**In Transit**:
- HTTPS/TLS for all API communication
- Encrypted S3 presigned URLs
- TLS for database connections

**At Rest**:
- S3 server-side encryption (SSE-S3 or SSE-KMS)
- Database encryption (if supported)
- Encrypted backups

### Access Logs

All access to uploaded files is logged:
- Timestamp
- Action (upload, download, process, delete)
- Result (success/failure)
- User session ID (anonymized)

Logs are:
- Stored securely
- Retained for 90 days
- Reviewed for suspicious activity
- Not shared externally

### Incident Response

In case of data breach:
1. Immediately stop the breach
2. Assess scope and impact
3. Notify affected users within 72 hours
4. Report to authorities if required
5. Implement preventive measures
6. Publish incident report (anonymized)

## Third-Party Services

### AWS S3 (or MinIO)
**Purpose**: File storage
**Data shared**: Uploaded scorecard files
**Privacy policy**: AWS Data Privacy / MinIO (self-hosted)
**Data residency**: Configurable (default: same region as application)

### Tesseract OCR
**Purpose**: Text extraction
**Data shared**: Images (processed locally)
**Privacy policy**: Open source, no data sent externally
**Notes**: Self-hosted, no third-party data sharing

### Redis
**Purpose**: Task queue and caching
**Data shared**: Task metadata, upload IDs
**Privacy policy**: Self-hosted
**Notes**: No personal data stored

### Celery
**Purpose**: Task orchestration
**Data shared**: Task parameters
**Privacy policy**: Open source library
**Notes**: Self-hosted, no external communication

## Compliance

### GDPR (EU)
- Legal basis: Consent and legitimate interest
- Data minimization: Only necessary data collected
- Right to erasure: Implemented
- Data portability: Planned
- Privacy by design: Implemented

### COPPA (US - Children)
- Parental consent required for users under 13
- Minimal data collection
- No advertising or tracking
- Clear privacy notices

### CCPA (California)
- Right to know: Implemented
- Right to delete: Implemented
- Right to opt-out: Implemented
- No sale of personal information

## Audit and Review

### Regular Reviews

This policy is reviewed:
- **Quarterly**: Internal review by development team
- **Annually**: External privacy audit
- **Ad-hoc**: When new features added or regulations change

### Update Process

When policy changes:
1. Draft updated policy
2. Review with stakeholders
3. Notify users of changes
4. Publish updated policy
5. Archive previous versions

### Feedback

Users can provide feedback on this policy:
- GitHub issues: [repository]/issues
- Email: privacy@cricksy-scorer.com (example)
- Privacy request form: [to be implemented]

## Contact

For privacy concerns, data requests, or questions about AI ethics:

**Data Protection Officer** (or equivalent):
- Email: [to be configured]
- Form: [to be implemented]
- Response time: Within 7 business days

**System Administrator**:
- For technical issues with uploads
- For deletion requests
- For access problems

## Policy Version

- **Version**: 1.0
- **Effective Date**: 2024-11-10
- **Last Updated**: 2024-11-10
- **Next Review**: 2025-02-10

## Acknowledgments

This policy is informed by:
- GDPR requirements
- CCPA guidelines
- IEEE ethical AI principles
- AI Now Institute recommendations
- Partnership on AI best practices

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2024-11-10 | Initial policy | Development Team |

---

**Note**: This is a living document. As AI technology and regulations evolve, this policy will be updated to maintain the highest ethical standards and protect user privacy.
