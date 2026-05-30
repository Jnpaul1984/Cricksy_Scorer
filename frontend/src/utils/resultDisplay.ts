export function normalizeResultDisplayText(result: string | null | undefined): string {
  if (!result) return ''

  return result
    .replace(/\b(\d+)\s+run\(s\)/gi, (_, count: string) => (Number.parseInt(count, 10) === 1 ? '1 run' : `${count} runs`))
    .replace(/\b(\d+)\s+wicket\(s\)/gi, (_, count: string) => (Number.parseInt(count, 10) === 1 ? '1 wicket' : `${count} wickets`))
    .replace(/\b1\s+runs\b/gi, '1 run')
    .replace(/\b1\s+wickets\b/gi, '1 wicket')
}
