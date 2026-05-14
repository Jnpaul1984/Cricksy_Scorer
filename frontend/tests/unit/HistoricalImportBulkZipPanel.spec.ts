import { mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import HistoricalImportBulkZipPanel from '@/components/HistoricalImportBulkZipPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalImportBulkZipDryRun: vi.fn(),
  historicalImportBulkZipApply: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

describe('HistoricalImportBulkZipPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  async function selectZip(wrapper: ReturnType<typeof mount>) {
    const input = wrapper.find('input[type="file"]')
    const file = new File([new Uint8Array([80, 75, 3, 4])], 'matches.zip', { type: 'application/zip' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    return file
  }

  it('renders configured ZIP limits and metadata-only dry-run summary', async () => {
    vi.mocked(api.historicalImportBulkZipDryRun).mockResolvedValue({
      status: 'preview_ready',
      source_filename: 'matches.zip',
      total_entries: 150,
      files_scanned: 150,
      json_entries: 140,
      non_json_entries: 10,
      metadata_only_intake_required: true,
      metadata_only_pending_count: 130,
      intake_status: 'scanned',
      cost_control_message: 'Stored safely for later processing; full import is deferred.',
      full_import_deferred: true,
      selected_apply_requires_confirm: true,
      max_files: 2000,
      max_file_size_bytes: 2097152,
      max_total_uncompressed_bytes: 104857600,
      max_total_compressed_bytes: 104857600,
      summary: { valid: 130, invalid: 5, duplicate: 3, unsupported: 10, error: 2 },
      files: [],
    })

    const wrapper = mount(HistoricalImportBulkZipPanel)
    await selectZip(wrapper)
    await wrapper.find('button.hiz-btn--primary').trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Files scanned: 150')
    expect(text).toContain('Max files per ZIP: 2000')
    expect(text).toContain('Unsupported files: 10')
    expect(text).toContain('Stored safely for later processing; full import is deferred.')
  })

  it('shows metadata-only apply result messaging and does not imply training readiness', async () => {
    const dryRun = {
      status: 'preview_ready' as const,
      source_filename: 'matches.zip',
      total_entries: 120,
      files_scanned: 120,
      json_entries: 120,
      non_json_entries: 0,
      metadata_only_intake_required: true,
      metadata_only_pending_count: 1,
      intake_status: 'scanned',
      cost_control_message: 'Stored safely for later processing.',
      full_import_deferred: true,
      selected_apply_requires_confirm: true,
      max_files: 2000,
      max_file_size_bytes: 2097152,
      max_total_uncompressed_bytes: 104857600,
      max_total_compressed_bytes: 104857600,
      summary: { valid: 1, invalid: 0, duplicate: 0, unsupported: 0, error: 0 },
      files: [
        {
          file_name: 'one.json',
          status: 'valid' as const,
          message: 'Valid JSON preview ready.',
          duplicate_within_zip: false,
          duplicate_batch_id: null,
          semantic_duplicate: false,
          detected_format: 'cricsheet_json',
          warnings: [],
          errors: [],
          dry_run_preview: null,
        },
      ],
    }
    vi.mocked(api.historicalImportBulkZipDryRun).mockResolvedValue(dryRun)
    vi.mocked(api.historicalImportBulkZipApply).mockResolvedValue({
      status: 'metadata_recorded',
      source_filename: 'matches.zip',
      selected_count: 1,
      applied_count: 0,
      skipped_count: 0,
      error_count: 0,
      metadata_only_count: 1,
      full_import_deferred: true,
      selected_apply_requires_confirm: true,
      results: [
        {
          file_name: 'one.json',
          status: 'metadata_extracted',
          message: 'Stored safely for later processing.',
          batch_id: 'batch-1',
          applied_game_id: null,
        },
      ],
    })

    const wrapper = mount(HistoricalImportBulkZipPanel)
    await selectZip(wrapper)
    await wrapper.find('button.hiz-btn--primary').trigger('click')
    await flushPromises()
    await wrapper.findAll('button.hiz-btn--primary')[1].trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Metadata-only records stored: 1')
    expect(text).toContain('Stored safely for later processing.')
    expect(text).toContain('not training-ready')
    expect(text).not.toContain('training-ready now')
  })
})
