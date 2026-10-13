const videoIdPattern = /^[A-Za-z0-9_-]{11}$/;
const watchHosts = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com']);

export function normalizeYoutubeVideoUrl(value: string): string | null {
  if (
    !value
    || value.length > 2048
    || [...value].some((character) => {
      const code = character.charCodeAt(0);
      return /\s/.test(character) || code < 32 || (code >= 127 && code <= 159);
    })
  ) return null;

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  const authority = value.slice(value.indexOf('//') + 2).split(/[/?#]/, 1)[0];
  if (
    url.protocol !== 'https:'
    || url.username
    || url.password
    || url.port
    || authority.includes('@')
    || authority.includes(':')
  ) return null;

  let videoId: string | null = null;
  if (url.hostname === 'youtu.be') {
    const match = url.pathname.match(/^\/([A-Za-z0-9_-]+)$/);
    videoId = match?.[1] ?? null;
  } else if (watchHosts.has(url.hostname) && url.pathname === '/watch') {
    const values = url.searchParams.getAll('v');
    if (values.length === 1) videoId = values[0];
  } else if (watchHosts.has(url.hostname)) {
    const match = url.pathname.match(/^\/live\/([A-Za-z0-9_-]+)$/);
    videoId = match?.[1] ?? null;
  }
  return videoId && videoIdPattern.test(videoId) ? videoId : null;
}

export function youtubeVideoUrls(videoId: string): { embedUrl: string; watchUrl: string } | null {
  if (!videoIdPattern.test(videoId)) return null;
  return {
    embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}`,
    watchUrl: `https://www.youtube.com/watch?v=${videoId}`,
  };
}
