# AI Ethics and Media Policy

## Overview

This document outlines the ethical principles, consent requirements, and usage guidelines for AI-powered features in Cricksy Scorer, specifically the OCR-based scorecard upload and processing system.

## Core Principles

### 1. Human-in-the-Loop

**All AI/OCR results require human verification before being applied to official game records.**

- OCR is a **prototype-level** technology that makes errors
- Parsed deliveries must be reviewed and confirmed by a human operator
- The system provides an editing interface for corrections
- No automated application of OCR results without explicit confirmation

### 2. Transparency

Users must understand:
- How their uploaded media is processed
- What happens to their data
- The limitations and accuracy of OCR technology
- Where their data is stored and for how long

### 3. Privacy and Consent

All uploads must comply with privacy regulations and respect individual rights:
- Users must have the right to upload media related to games they are authorized to score
- Images containing identifiable individuals require appropriate consent
- No upload of media containing minors without guardian consent
- Users can delete their uploads at any time

### 4. Data Minimization

Only collect and process what is necessary:
- Store only scorecard-related media (not personal photos)
- Delete temporary files immediately after processing
- Implement retention policies for uploaded media
- Provide tools for users to export or delete their data

## Consent Requirements

### For Uploaders

Before uploading, users must acknowledge:

```
I confirm that:
☐ I have the right to upload this scorecard media
☐ The media contains only cricket scoring information
☐ If the media contains identifiable individuals, I have obtained necessary consent
☐ I understand this media will be processed using OCR technology
☐ I will review and verify OCR results before applying them to the game
```

### For Individuals in Photos

If uploaded scorecards contain identifiable individuals (players, umpires, etc.):

**Required for Minors (under 18):**
- Written parent/guardian consent
- Clear explanation of how images will be used
- Option to request removal at any time

**Required for Adults:**
- Verbal or written consent
- Understanding that images may be stored and processed
- Right to request removal

### For Public Events

For scorecards from public cricket matches:
- General signage informing attendees of media capture is recommended
- Contact information for removal requests must be available
- Comply with local event photography laws

## Prohibited Uses

The following uses of uploaded media are **strictly prohibited**:

### ❌ Forbidden

1. **Biometric Identification**: Using facial recognition or other biometric analysis on individuals in images
2. **Surveillance**: Tracking individuals across multiple uploads or events
3. **Profiling**: Creating profiles of players or spectators beyond basic statistics
4. **Commercial Use**: Selling or licensing uploaded media without explicit consent
5. **Discrimination**: Using data to discriminate based on protected characteristics
6. **Manipulation**: Altering scorecard data to misrepresent game outcomes
7. **Harassment**: Using media to harass, threaten, or harm individuals
8. **Unauthorized Disclosure**: Sharing media beyond authorized users

### ⚠️ Restricted

These uses require additional approval and oversight:

1. **Training Data**: Using uploads to train ML models (requires opt-in consent)
2. **Research**: Academic or commercial research using uploaded data
3. **Marketing**: Using scorecard data for promotional purposes
4. **Cross-Event Analysis**: Comparing performance across multiple games

## Technical Safeguards

### Data Protection

1. **Encryption**:
   - All uploads transmitted via HTTPS
   - Media stored in S3 with encryption at rest
   - Database encryption for parsed results

2. **Access Control**:
   - Upload presigned URLs expire after 1 hour
   - Only authorized users can view uploaded media
   - Role-based access for different user types

3. **Audit Trail**:
   - Log all upload, view, and delete actions
   - Track who approved parsed results
   - Monitor for suspicious access patterns

4. **Data Lifecycle**:
   - Temporary files deleted immediately after processing
   - Uploads retained for configurable period (default: 90 days)
   - Automatic deletion of abandoned uploads (not linked to a game)

### OCR Limitations

Users must be informed of OCR limitations:

1. **Accuracy**: OCR is not 100% accurate and makes mistakes
2. **Confidence Scores**: Low confidence scores indicate uncertain results
3. **Validation**: System validates parsed data but cannot catch all errors
4. **Edge Cases**: Unusual scorecard formats may not parse correctly
5. **Human Review**: Final verification by a human is **mandatory**

## User Rights

### Right to Access

Users can:
- View all their uploaded media
- Download original files
- Export parsed results
- See who has accessed their uploads

### Right to Deletion

Users can:
- Delete uploads at any time
- Request removal of processed data
- Expect deletion within 30 days
- Receive confirmation of deletion

### Right to Correction

Users can:
- Edit parsed results before application
- Report errors in OCR processing
- Request re-processing of uploads

### Right to Export

Users can:
- Export their upload history
- Download all uploaded files
- Receive data in standard formats (JSON, CSV)

## Retention and Deletion

### Standard Retention

| Data Type | Retention Period | Reason |
|-----------|------------------|--------|
| Original Upload | 90 days | Allow re-processing if needed |
| Parsed Results | Indefinite | Part of game record |
| OCR Raw Text | 30 days | Debugging and improvement |
| Temporary Files | 0 days | Deleted immediately |
| Access Logs | 1 year | Security and audit |

### Extended Retention

For research or improvement purposes (requires opt-in):
- Anonymized scorecards: 5 years
- Performance metrics: 3 years
- Error reports: 2 years

### Deletion Triggers

Automatic deletion occurs when:
1. User requests deletion
2. Retention period expires
3. Upload is abandoned (not linked to game after 7 days)
4. Account is closed

## Incident Response

### Data Breach

In case of unauthorized access:
1. Immediately notify affected users
2. Suspend upload feature if necessary
3. Conduct security audit
4. Implement remediation measures
5. Report to authorities if required by law

### OCR Errors

For significant OCR errors:
1. Alert users reviewing parsed results
2. Log error details for improvement
3. Consider disabling problematic file types
4. Provide clear error messages

### Consent Violations

If uploaded media violates consent requirements:
1. Remove media immediately
2. Notify affected individuals
3. Investigate uploader's account
4. Take appropriate enforcement action

## Compliance

### Applicable Regulations

This system must comply with:

- **GDPR** (Europe): Data protection and privacy
- **COPPA** (USA): Children's online privacy
- **CCPA** (California): Consumer privacy rights
- **Local Privacy Laws**: School and sports organization policies

### Regular Reviews

- Quarterly review of uploaded media samples
- Annual privacy and security audit
- Bi-annual user consent form updates
- Continuous monitoring of OCR accuracy

## Responsible AI Checklist

Before deploying OCR features:

- [ ] Human review requirement is enforced
- [ ] Consent forms are displayed and acknowledged
- [ ] Privacy policy is updated
- [ ] Data retention policies are implemented
- [ ] Access logs are configured
- [ ] Deletion mechanisms are tested
- [ ] Error handling is comprehensive
- [ ] User rights (access, delete, export) are functional
- [ ] Security measures are in place
- [ ] Documentation is complete

## Contact and Reporting

### Privacy Concerns

Email: privacy@cricksy.example.com

### Data Deletion Requests

Email: data-requests@cricksy.example.com

### Security Issues

Email: security@cricksy.example.com

### General Inquiries

Email: support@cricksy.example.com

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-10 | Initial policy for OCR upload feature |

## Acknowledgments

This policy draws inspiration from:
- EU AI Act
- IEEE Ethically Aligned Design
- Partnership on AI Guidelines
- ACM Code of Ethics
- Responsible AI principles from major tech companies

## Further Reading

- [Upload Workflow Documentation](./UPLOAD_WORKFLOW.md)
- [Worker Deployment Guide](./DEPLOY_WORKER.md)
- GDPR Compliance Guide
- COPPA Compliance Guide
- Security Best Practices
