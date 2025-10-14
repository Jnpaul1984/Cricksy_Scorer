// src/utils/dls.ts
export type DLSKind = 'odi' | 't20'
export async function fetchRevisedTarget(gameId: string, kind: DLSKind = 'odi') {
  const res = await fetch(`/games/${encodeURIComponent(gameId)}/dls/revised-target`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, innings: 2 }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ R1_total: number; R2_total: number; S1: number; target: number }>
}
export async function fetchPar(gameId: string, kind: DLSKind = 'odi') {
  const res = await fetch(`/games/${encodeURIComponent(gameId)}/dls/par`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, innings: 2 }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ R1_total:number; R2_used:number; S1:number; par:number; ahead_by:number }>
}
