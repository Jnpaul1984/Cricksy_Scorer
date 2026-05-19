export type ExportTarget =
  | 'season_summary'
  | 'match_story'
  | 'leaderboards'
  | 'venue_intelligence'
  | 'podcast_facts'

export type ExportFormat = 'podcast_landscape' | 'social_square' | 'story_vertical'

export type CplTemplateFamily =
  | 'match_story'
  | 'season_summary'
  | 'leaderboard'
  | 'venue_intelligence'
  | 'podcast_episode_card'

export type CplTemplateVariant = 'clean_broadcast' | 'bold_social' | 'data_desk' | 'minimal_stat_card'

export interface CplVisualTemplate {
  id: string
  label: string
  family: CplTemplateFamily
  variant: CplTemplateVariant
  description: string
  watermarkPlacement: 'header' | 'footer' | 'overlay'
  requirements: Array<'match_selected' | 'match_delivery_data' | 'leaderboard_data' | 'venue_data' | 'podcast_facts_data'>
}

export const templateFamilyByTarget: Record<ExportTarget, CplTemplateFamily> = {
  season_summary: 'season_summary',
  match_story: 'match_story',
  leaderboards: 'leaderboard',
  venue_intelligence: 'venue_intelligence',
  podcast_facts: 'podcast_episode_card',
}

export const cplVisualTemplates: ReadonlyArray<CplVisualTemplate> = [
  {
    id: 'season-clean-broadcast',
    label: 'Clean Broadcast · Season Summary',
    family: 'season_summary',
    variant: 'clean_broadcast',
    description: 'Balanced hierarchy for podcast screens and recap decks.',
    watermarkPlacement: 'footer',
    requirements: [],
  },
  {
    id: 'season-bold-social',
    label: 'Bold Social · Season Summary',
    family: 'season_summary',
    variant: 'bold_social',
    description: 'High-contrast summary treatment for social posts.',
    watermarkPlacement: 'overlay',
    requirements: [],
  },
  {
    id: 'match-data-desk',
    label: 'Data Desk · Match Story',
    family: 'match_story',
    variant: 'data_desk',
    description: 'Match breakdown with desk-style framing and provenance.',
    watermarkPlacement: 'header',
    requirements: ['match_selected', 'match_delivery_data'],
  },
  {
    id: 'match-minimal-card',
    label: 'Minimal Stat Card · Match Story',
    family: 'match_story',
    variant: 'minimal_stat_card',
    description: 'Compact match story card for quick previews and stories.',
    watermarkPlacement: 'overlay',
    requirements: ['match_selected', 'match_delivery_data'],
  },
  {
    id: 'leaderboard-bold-social',
    label: 'Bold Social · Leaderboard',
    family: 'leaderboard',
    variant: 'bold_social',
    description: 'Leaderboard-first graphic with stronger score emphasis.',
    watermarkPlacement: 'overlay',
    requirements: ['leaderboard_data'],
  },
  {
    id: 'leaderboard-clean-broadcast',
    label: 'Clean Broadcast · Leaderboard',
    family: 'leaderboard',
    variant: 'clean_broadcast',
    description: 'Readable leaderboard layout for long-form podcast visuals.',
    watermarkPlacement: 'footer',
    requirements: ['leaderboard_data'],
  },
  {
    id: 'venue-data-desk',
    label: 'Data Desk · Venue Intelligence',
    family: 'venue_intelligence',
    variant: 'data_desk',
    description: 'Venue intelligence template with contextual footer band.',
    watermarkPlacement: 'header',
    requirements: ['venue_data'],
  },
  {
    id: 'venue-minimal-card',
    label: 'Minimal Stat Card · Venue Intelligence',
    family: 'venue_intelligence',
    variant: 'minimal_stat_card',
    description: 'Venue-focused stat card with reduced visual chrome.',
    watermarkPlacement: 'footer',
    requirements: ['venue_data'],
  },
  {
    id: 'podcast-clean-broadcast',
    label: 'Clean Broadcast · Podcast Episode Card',
    family: 'podcast_episode_card',
    variant: 'clean_broadcast',
    description: 'Podcast episode teaser card grounded in deterministic facts.',
    watermarkPlacement: 'footer',
    requirements: ['podcast_facts_data'],
  },
  {
    id: 'podcast-bold-social',
    label: 'Bold Social · Podcast Episode Card',
    family: 'podcast_episode_card',
    variant: 'bold_social',
    description: 'Social teaser variant for podcast prep fact highlights.',
    watermarkPlacement: 'overlay',
    requirements: ['podcast_facts_data'],
  },
]

export const templateVariantLabels: Record<CplTemplateVariant, string> = {
  clean_broadcast: 'Clean Broadcast',
  bold_social: 'Bold Social',
  data_desk: 'Data Desk',
  minimal_stat_card: 'Minimal Stat Card',
}

export function templateFormatSpacing(format: ExportFormat): {
  wrapperPadding: string
  contentPadding: string
  titleSize: string
  footerSize: string
} {
  switch (format) {
    case 'story_vertical':
      return {
        wrapperPadding: '28px',
        contentPadding: '18px',
        titleSize: '34px',
        footerSize: '14px',
      }
    case 'social_square':
      return {
        wrapperPadding: '26px',
        contentPadding: '20px',
        titleSize: '28px',
        footerSize: '14px',
      }
    default:
      return {
        wrapperPadding: '24px',
        contentPadding: '16px',
        titleSize: '24px',
        footerSize: '13px',
      }
  }
}
