# AI Ethics and Consent Guidelines

## Overview

The Cricksy Scorer application includes AI-powered features, specifically Optical Character Recognition (OCR) for processing uploaded scorecard images. This document outlines ethical considerations, consent requirements, and best practices for using AI features.

## AI Features

### 1. OCR Processing

**Technology**: Tesseract OCR (open-source)
**Purpose**: Extract text and data from uploaded scorecard images
**Data Processing**: Local or cloud-based processing depending on deployment

**Limitations**:
- OCR accuracy is not 100% - typically 85-95% depending on image quality
- Handwritten text may have lower accuracy than printed text
- Poor image quality, lighting, or angles reduce accuracy
- Non-standard formats may not be recognized correctly

## User Consent

### What Users Should Know

Before using upload and OCR features, users must understand:

1. **Image Storage**: Uploaded images are stored temporarily in S3/MinIO storage
2. **Processing**: Images are processed by automated OCR software
3. **Accuracy**: OCR results require human review and verification
4. **Data Retention**: Images and processing results are retained according to data retention policy
5. **No Guarantees**: OCR is provided as-is without guarantees of accuracy

### Consent Mechanisms

#### Frontend Consent Flow

When users first access the upload feature, display:

```
📷 Upload Scorecard Images

By uploading a scorecard image, you acknowledge:
• Images will be stored securely in our system
• Images will be processed using automated OCR technology
• OCR results are not 100% accurate and require manual review
• You are responsible for verifying all extracted data before applying it

[ ] I understand and agree to these terms

[Continue to Upload]
```

#### API Documentation Consent

API endpoints must clearly document:
- What data is collected
- How it is processed
- Retention periods
- User rights (access, deletion, correction)

## Data Privacy

### Data Collection

**What we collect**:
- Uploaded image files (scorecards)
- OCR extracted text and structured data
- Upload metadata (timestamp, user ID, filename)
- Processing status and error logs

**What we DON'T collect**:
- Personal information from images (unless part of scorecard data)
- User device information (beyond standard HTTP headers)
- User location (unless explicitly provided)

### Data Retention

**Development/Testing**:
- Images retained for 30 days
- Processed data retained for 90 days
- Users can request deletion at any time

**Production**:
- Images retained for 1 year for audit purposes
- Processed data retained indefinitely (as part of match records)
- Users can request data export or deletion per GDPR/privacy laws

### Data Security

**In Transit**:
- All uploads via HTTPS
- Presigned URLs with time-limited access
- TLS 1.2+ encryption

**At Rest**:
- S3 server-side encryption (SSE-S3 or SSE-KMS)
- Database encryption at rest
- Access controls and authentication required

**Access Control**:
- Least privilege principle
- Role-based access (RBAC)
- Audit logging of data access

## Human Oversight

### Required Human Verification

**All OCR results MUST be reviewed by a human before being applied to the delivery ledger.**

This means:
1. OCR processes the image automatically
2. Results are stored in `parsed_preview` field
3. User MUST review all extracted data
4. User MUST explicitly confirm before applying
5. Apply endpoint requires `confirm=true` parameter

### Feedback Mechanism

Users should be able to:
- Report OCR errors or inaccuracies
- Provide feedback on OCR quality
- Suggest improvements to parsing logic
- Request manual review for problematic images

### Quality Assurance

Development team should:
- Monitor OCR accuracy metrics
- Track confidence scores
- Review failed OCR attempts
- Continuously improve parsing algorithms
- Maintain test dataset with known-good examples

## Transparency

### User Visibility

Users should see:
- **Processing Status**: Real-time feedback on OCR progress
- **Confidence Score**: Low/Medium/High confidence in results
- **Raw OCR Text**: Access to original OCR output for verification
- **Validation Errors**: Clear indication of parsing issues

### Explainability

For each parsed field, the system should (where feasible):
- Show source region in original image
- Highlight confidence scores per field
- Provide edit capability before applying
- Log corrections for future improvement

## Bias and Fairness

### Potential Biases

OCR systems may exhibit bias:
- **Language Bias**: Better accuracy for English than other scripts
- **Font Bias**: Better accuracy for standard fonts vs. handwriting
- **Quality Bias**: Better accuracy for high-quality scanned documents
- **Format Bias**: Better accuracy for standardized scorecard formats

### Mitigation Strategies

1. **Diverse Training Data**: Test with variety of formats and handwriting styles
2. **Confidence Thresholds**: Flag low-confidence results for extra review
3. **User Feedback Loop**: Collect corrections to improve accuracy
4. **Alternative Input**: Always provide manual entry option
5. **Clear Limitations**: Document known weaknesses upfront

## Accountability

### Responsibility Matrix

| Role | Responsibility |
|------|----------------|
| **Users** | Review OCR results, verify accuracy, provide feedback |
| **Scorers** | Ensure correct data entry, report issues |
| **Administrators** | Monitor system performance, review error logs |
| **Developers** | Maintain OCR accuracy, address bugs, improve algorithms |
| **Data Stewards** | Ensure privacy compliance, handle data requests |

### Error Handling

When OCR fails or produces low-confidence results:
1. **Notify User**: Clear message explaining the issue
2. **Provide Alternatives**: Offer manual entry option
3. **Log Error**: Record for analysis and improvement
4. **Graceful Degradation**: System remains functional without OCR

### Audit Trail

System must log:
- All uploads (timestamp, user, filename)
- OCR processing attempts (success/failure)
- User corrections to OCR results
- Application of data to delivery ledger
- Data access and modifications

## Compliance

### GDPR Considerations

**Right to Access**: Users can request all data associated with their uploads
**Right to Erasure**: Users can request deletion of uploaded images and processed data
**Right to Rectification**: Users can correct inaccurate OCR results
**Right to Data Portability**: Users can export their data in machine-readable format

### Implementation

```python
# Example: User data export endpoint
@router.get("/api/uploads/my-data")
async def export_my_uploads(user_id: str) -> dict:
    """Export all upload data for a user (GDPR compliance)."""
    uploads = get_user_uploads(user_id)
    return {
        "user_id": user_id,
        "uploads": [
            {
                "upload_id": u.upload_id,
                "filename": u.filename,
                "uploaded_at": u.uploaded_at,
                "parsed_preview": u.parsed_preview,
            }
            for u in uploads
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

# Example: Data deletion endpoint
@router.delete("/api/uploads/{upload_id}")
async def delete_upload(upload_id: str, user_id: str) -> dict:
    """Delete an upload and all associated data."""
    upload = get_upload(upload_id)
    if upload.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    
    # Delete from S3
    delete_s3_object(upload.s3_key)
    
    # Delete from database
    delete_upload_record(upload_id)
    
    return {"message": "Upload deleted successfully"}
```

## Future Considerations

### Advanced AI Features

If adding more advanced AI/ML features in the future:
- **Image Enhancement**: Pre-processing to improve OCR accuracy
- **Layout Analysis**: Automatic detection of scorecard format
- **Player Recognition**: Match names to player database
- **Score Validation**: Cross-check extracted totals for consistency

Each new feature requires:
1. Renewed consent from users
2. Updated privacy documentation
3. Bias and fairness analysis
4. Human oversight mechanisms
5. Audit and compliance review

### Emerging Regulations

Stay informed about:
- EU AI Act
- US state-level AI regulations
- Industry-specific compliance (sports data, education)
- Open-source AI ethics guidelines

## Resources

### Guidelines and Frameworks

- [OECD AI Principles](https://www.oecd.org/going-digital/ai/principles/)
- [IEEE Ethically Aligned Design](https://standards.ieee.org/industry-connections/ec/ead/)
- [Montreal Declaration for Responsible AI](https://www.montrealdeclaration-responsibleai.com/)
- [Google AI Principles](https://ai.google/principles/)

### OCR-Specific Resources

- [Tesseract OCR Documentation](https://tesseract-ocr.github.io/)
- [OCR Accuracy Best Practices](https://github.com/tesseract-ocr/tesseract/wiki/ImproveQuality)
- [ABBYY OCR Accuracy Factors](https://abbyy.technology/en:kb:tipoftheday:ocr:factors)

## Contact

For questions or concerns about AI features, data privacy, or ethical considerations:
- Email: privacy@cricksyscorer.com (placeholder)
- GitHub Issues: https://github.com/Jnpaul1984/Cricksy_Scorer/issues
- Documentation: See README and UPLOAD_WORKFLOW.md

## Version History

- **v1.0** (2025-11-10): Initial AI Ethics documentation for OCR feature
