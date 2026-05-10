export async function fetchRevisedTarget(gameId, kind = 'odi') {
    const res = await fetch(`/games/${encodeURIComponent(gameId)}/dls/revised-target`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, innings: 2 }),
    });
    if (!res.ok)
        throw new Error(await res.text());
    return res.json();
}
export async function fetchPar(gameId, kind = 'odi') {
    const res = await fetch(`/games/${encodeURIComponent(gameId)}/dls/par`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, innings: 2 }),
    });
    if (!res.ok)
        throw new Error(await res.text());
    return res.json();
}
