import { describe, expect, it } from 'vitest';

import { normalizeYoutubeVideoUrl, youtubeVideoUrls } from '@/utils/youtubeVideo';

const videoId = 'AbCdEf123_-';

describe('YouTube video URL boundary', () => {
  it.each([
    [`https://www.youtube.com/watch?v=${videoId}&list=synthetic#t=2`, videoId],
    [`https://youtu.be/${videoId}?si=synthetic`, videoId],
    [`https://youtube.com/live/${videoId}?feature=share`, videoId],
  ])('normalizes supported URL forms', (url, expectedId) => {
    expect(normalizeYoutubeVideoUrl(url)).toBe(expectedId);
  });

  it.each([
    `http://youtube.com/watch?v=${videoId}`,
    `https://youtube.com.evil.invalid/watch?v=${videoId}`,
    `https://evil.youtube.com/watch?v=${videoId}`,
    `https://youtube.com:443/watch?v=${videoId}`,
    `https://@youtube.com/watch?v=${videoId}`,
    `https://youtube.com@evil.invalid/watch?v=${videoId}`,
    `https://youtube.com/watch?v=${videoId}&v=${videoId}`,
    'https://youtube.com/playlist?list=synthetic',
    `https://youtu.be/short`,
    `<iframe src="https://youtube.com/embed/${videoId}"></iframe>`,
    `javascript:window.location="https://youtu.be/${videoId}"`,
    ` https://youtu.be/${videoId}`,
  ])('rejects unsupported URL %s', (url) => {
    expect(normalizeYoutubeVideoUrl(url)).toBeNull();
  });

  it('builds only the fixed privacy-enhanced embed and watch URLs', () => {
    expect(youtubeVideoUrls(videoId)).toEqual({
      embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}`,
      watchUrl: `https://www.youtube.com/watch?v=${videoId}`,
    });
    expect(youtubeVideoUrls('malformed')).toBeNull();
  });
});
