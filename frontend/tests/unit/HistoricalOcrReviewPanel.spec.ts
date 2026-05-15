import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import HistoricalOcrReviewPanel from '@/components/HistoricalOcrReviewPanel.vue';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  historicalOcrCreateCandidate: vi.fn(),
  historicalOcrSubmitReview: vi.fn(),
  historicalOcrDryRunCandidate: vi.fn(),
  historicalOcrRejectCandidate: vi.fn(),
}));

const baseCandidate = {
  candidate_id: 'ocr-candidate-001',
  batch_id: 'ocr-candidate-001',
  status: 'needs_review' as const,
  status_history: ['uploaded', 'extracted', 'needs_review'] as const,
  source_document: {
    filename: 'scorecard.pdf',
    content_type: 'application/pdf',
    size_bytes: 2048,
    storage: { storage: 'local', path: '/tmp/ocr/scorecard.pdf' },
  },
  extraction: {
    method: 'manual_candidate_json',
    confidence: 0.84,
    uncertainty_flags: [],
    ocr_text: null,
    warnings: [],
    non_authoritative_notice:
      'OCR/AI extraction is non-authoritative and must be reviewed before historical import.',
  },
  candidate_json: {
    matchType: 'T20',
    teams: ['Lions', 'Falcons'],
    innings: [],
  },
  reviewed_json: null,
  reviewer_notes: null,
  rejection_reason: null,
  validation_errors: [],
  dry_run_result: null,
  dry_run_batch_id: null,
};

const pdfExtractCandidateWithText = {
  ...baseCandidate,
  status: 'needs_review' as const,
  extraction: {
    method: 'pdf_text_extract',
    confidence: 1.0,
    uncertainty_flags: [],
    ocr_text: 'Lions vs Falcons\nTotal: 185/6 in 20 overs',
    warnings: [],
    non_authoritative_notice:
      'OCR/AI extraction is non-authoritative and must be reviewed before historical import.',
  },
  candidate_json: null,
};

const pdfExtractCandidateNoText = {
  ...baseCandidate,
  status: 'uploaded' as const,
  extraction: {
    method: 'pdf_text_extract',
    confidence: 0.0,
    uncertainty_flags: ['scanned_pdf_no_text'],
    ocr_text: null,
    warnings: [
      'PDF contains no extractable text layer. This is likely a scanned image PDF. Image OCR is not performed — please enter the scorecard JSON manually.',
    ],
    non_authoritative_notice:
      'OCR/AI extraction is non-authoritative and must be reviewed before historical import.',
  },
  candidate_json: null,
};

const flushPromises = async () => {
  await Promise.resolve();
  await Promise.resolve();
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

async function selectFile(wrapper: ReturnType<typeof mount>, fileName = 'scorecard.pdf', type = 'application/pdf') {
  const input = wrapper.find('input[type="file"]');
  const file = new File([new Uint8Array([37, 80, 68, 70])], fileName, { type });
  Object.defineProperty(input.element, 'files', { value: [file] });
  await input.trigger('change');
}

describe('HistoricalOcrReviewPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows an explicit empty state before any candidate is created', () => {
    const wrapper = mount(HistoricalOcrReviewPanel);

    expect(wrapper.get('[data-testid="ocr-empty-state"]').text()).toContain('No OCR review candidate yet');
    expect((wrapper.get('[data-testid="ocr-run-dry-run"]').element as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows a loading state while creating a review candidate', async () => {
    const createDeferred = deferred<typeof baseCandidate>();
    vi.mocked(api.historicalOcrCreateCandidate).mockReturnValue(createDeferred.promise);

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-candidate-json"]').setValue(
      '{"matchType":"T20","teams":["Lions","Falcons"],"innings":[]}',
    );

    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    expect(wrapper.get('[data-testid="ocr-loading-state"]').text()).toContain('Creating OCR review candidate');

    createDeferred.resolve(baseCandidate);
    await flushPromises();

    expect(wrapper.find('[data-testid="ocr-loading-state"]').exists()).toBe(false);
  });

  it('requires review readiness before dry-run and blocks dry-run again after rejection', async () => {
    vi.mocked(api.historicalOcrCreateCandidate).mockResolvedValue(baseCandidate);
    vi.mocked(api.historicalOcrSubmitReview).mockResolvedValue({
      ...baseCandidate,
      status: 'ready_for_dry_run',
      status_history: ['uploaded', 'extracted', 'needs_review', 'reviewed', 'ready_for_dry_run'],
      reviewed_json: baseCandidate.candidate_json,
    });
    vi.mocked(api.historicalOcrRejectCandidate).mockResolvedValue({
      ...baseCandidate,
      status: 'rejected',
      status_history: ['uploaded', 'extracted', 'needs_review', 'rejected'],
      rejection_reason: 'Too blurry to verify.',
    });

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-candidate-json"]').setValue(
      '{"matchType":"T20","teams":["Lions","Falcons"],"innings":[]}',
    );

    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    expect((wrapper.get('[data-testid="ocr-run-dry-run"]').element as HTMLButtonElement).disabled).toBe(true);

    await wrapper.get('[data-testid="ocr-save-review"]').trigger('click');
    await flushPromises();

    expect((wrapper.get('[data-testid="ocr-run-dry-run"]').element as HTMLButtonElement).disabled).toBe(false);

    await wrapper.get('input[placeholder="Why this extraction is unusable"]').setValue('Too blurry to verify.');
    await wrapper.get('[data-testid="ocr-reject-candidate"]').trigger('click');
    await flushPromises();

    expect((wrapper.get('[data-testid="ocr-run-dry-run"]').element as HTMLButtonElement).disabled).toBe(true);
    expect(wrapper.get('[data-testid="ocr-candidate-summary"]').text()).toContain('Too blurry to verify.');
  });

  it('wraps malformed JSON parse errors with operator-facing context', async () => {
    vi.mocked(api.historicalOcrCreateCandidate).mockResolvedValue(baseCandidate);

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-candidate-json"]').setValue('{"matchType":"T20",');

    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    expect(wrapper.get('.hocr-error').text()).toContain('Invalid structured JSON:');
  });

  // Phase 7C — PDF text extraction display tests

  it('renders extracted text preview with non-authoritative notice for pdf_text_extract method', async () => {
    vi.mocked(api.historicalOcrCreateCandidate).mockResolvedValue(pdfExtractCandidateWithText);

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    const preview = wrapper.get('[data-testid="ocr-extracted-text-preview"]');
    expect(preview.exists()).toBe(true);
    // Must show non-authoritative warning
    expect(preview.text()).toContain('not official match data');
    // Must show extracted text content
    const content = wrapper.get('[data-testid="ocr-extracted-text-content"]');
    expect(content.text()).toContain('Lions vs Falcons');
  });

  it('renders no-text fallback message when pdf_text_extract finds no extractable text', async () => {
    vi.mocked(api.historicalOcrCreateCandidate).mockResolvedValue(pdfExtractCandidateNoText);

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    const preview = wrapper.get('[data-testid="ocr-extracted-text-preview"]');
    expect(preview.exists()).toBe(true);
    const noTextMsg = wrapper.get('[data-testid="ocr-no-text-message"]');
    expect(noTextMsg.text()).toContain('No extractable text');
    // Extracted text content block must not render
    expect(wrapper.find('[data-testid="ocr-extracted-text-content"]').exists()).toBe(false);
  });

  it('does not render extracted text preview for manual_candidate_json method', async () => {
    vi.mocked(api.historicalOcrCreateCandidate).mockResolvedValue(baseCandidate);

    const wrapper = mount(HistoricalOcrReviewPanel);
    await selectFile(wrapper);
    await wrapper.get('[data-testid="ocr-candidate-json"]').setValue(
      '{"matchType":"T20","teams":["Lions","Falcons"],"innings":[]}',
    );
    await wrapper.get('[data-testid="ocr-create-candidate"]').trigger('click');
    await flushPromises();

    // No pdf_text_extract preview should render for manual method
    expect(wrapper.find('[data-testid="ocr-extracted-text-preview"]').exists()).toBe(false);
  });
});
