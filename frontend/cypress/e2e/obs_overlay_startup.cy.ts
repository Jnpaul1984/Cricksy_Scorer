const publicIdentifier = 'org_0123456789abcdef01234567';
const competitionPublicKey = 'cmp_0123456789abcdef01234567';
const scorecardPublicIdentifier = 'sc_0123456789abcdef01234567';
const scorecardPath = `/api/public/organizations/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${scorecardPublicIdentifier}`;
const overlayPath = `/community/${publicIdentifier}/competitions/${competitionPublicKey}/scorecards/${scorecardPublicIdentifier}/overlay`;

const syntheticScorecard = {
  public_identifier: scorecardPublicIdentifier,
  youtube_video_id: 'AbCdEf123_-',
  organization_type: 'club',
  publication_state: 'published_live',
  status: 'in_progress',
  team_a: { name: 'Synthetic Adult XI', players: [] },
  team_b: { name: 'Practice Adults', players: [] },
  match_type: 'limited',
  overs_limit: 20,
  days_limit: null,
  overs_per_day: null,
  toss_winner_team: 'Synthetic Adult XI',
  decision: 'bat',
  batting_team_name: 'Synthetic Adult XI',
  bowling_team_name: 'Practice Adults',
  total_runs: 42,
  total_wickets: 2,
  overs_completed: 7,
  balls_this_over: 3,
  current_inning: 1,
  result: null,
  batting_scorecard: [],
  bowling_scorecard: [],
};

const overlayUrlCases: Array<[string, (path: string) => string]> = [
  ['query', (path) => `${path}?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`],
  ['hash', (path) => `${path}#/?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`],
];

describe('production app startup', () => {
  it('renders an ordinary lazy route after authenticated initial navigation', () => {
    cy.intercept('**/api/**', { statusCode: 200, body: {} });
    cy.intercept('GET', '**/auth/me', {
      id: 'synthetic-adult-user',
      email: 'synthetic@example.invalid',
      name: 'Synthetic Adult',
      role: 'org_pro',
      is_superuser: false,
    }).as('authMe');

    cy.visitWithAuth('/coaches');
    cy.contains('h1', 'Coaches Dashboard').should('be.visible');
    cy.location('pathname').should('eq', '/coaches');
  });

  it('loads analyst data after authenticated lazy-route startup', () => {
    cy.intercept('GET', '**/analytics/**', { statusCode: 200, body: {} });
    cy.intercept('GET', '**/analytics/matches', { items: [], total: 0 }).as('getAnalystMatches');

    cy.visitWithAuth('/analyst/workspace');

    cy.wait('@getAnalystMatches');
    cy.contains('h1', 'Analyst Workspace').should('be.visible');
  });

  overlayUrlCases.forEach(([overrideType, makeUrl]) => {
    it(`starts the public overlay without credentialed or arbitrary-origin requests (${overrideType} override)`, () => {
      const apiRequests: Array<{ url: string; headers: Record<string, string> }> = [];
      const unexpectedRequests: Array<{ url: string; method: string; resourceType: string }> = [];
      const appOrigin = new URL(Cypress.config('baseUrl')!).origin;
      const configuredApiBase = Cypress.env('API_BASE') || 'http://127.0.0.1:8000';
      const canonicalApiOrigin = new URL(configuredApiBase).origin;
      const staticResourceTypes = new Set(['document', 'stylesheet', 'script', 'image', 'font', 'manifest']);

      cy.intercept('**/*', (request) => {
        const url = new URL(request.url);
        const resourceType = request.resourceType || 'unknown';
        const hasAuthorization = Object.keys(request.headers).some(
          (header) => header.toLowerCase() === 'authorization',
        );
        const isCanonicalScorecardRequest =
          request.method === 'GET' &&
          url.origin === canonicalApiOrigin &&
          url.pathname === scorecardPath &&
          !url.search &&
          !hasAuthorization &&
          (resourceType === 'fetch' || resourceType === 'xhr');
        const isOverlayDocument =
          url.origin === appOrigin &&
          url.pathname === overlayPath &&
          request.method === 'GET' &&
          resourceType === 'document';
        const isStaticAsset =
          url.origin === appOrigin &&
          request.method === 'GET' &&
          (url.pathname.startsWith('/assets/') || url.pathname === '/logo.png') &&
          staticResourceTypes.has(resourceType);

        if (isCanonicalScorecardRequest) {
          apiRequests.push({ url: request.url, headers: request.headers });
          request.reply({ statusCode: 200, body: syntheticScorecard });
          return;
        }

        if (isOverlayDocument || isStaticAsset) {
          request.continue();
          return;
        }

        if (url.origin === canonicalApiOrigin || resourceType === 'fetch' || resourceType === 'xhr') {
          apiRequests.push({ url: request.url, headers: request.headers });
        }
        unexpectedRequests.push({ url: request.url, method: request.method, resourceType });
        request.reply({ statusCode: 599, body: {} });
      });

      cy.visit(makeUrl(overlayPath), {
        onBeforeLoad(win) {
          win.localStorage.setItem('cricksy_token', 'synthetic-overlay-test-token');
          (win as any).__overlaySocketUrls = [];
          class BlockedWebSocket {
            constructor(url: string | URL) {
              (win as any).__overlaySocketUrls.push(String(url));
            }

            addEventListener() {}
            removeEventListener() {}
            close() {}
            send() {}
          }
          win.WebSocket = BlockedWebSocket as unknown as typeof win.WebSocket;
        },
      });

      cy.contains('Synthetic Adult XI').should('be.visible');
      cy.contains('42/2').should('be.visible');
      cy.get('iframe').should('not.exist');
      cy.then(() => {
        expect(apiRequests).to.have.length(1);
        const request = apiRequests[0];
        const actualUrl = new URL(request.url);
        expect(actualUrl.pathname).to.equal(scorecardPath);
        expect(actualUrl.origin).to.equal(canonicalApiOrigin);
        expect(request.url).not.to.include('unsafe.example.invalid');
        expect(Object.keys(request.headers).map((header) => header.toLowerCase())).not.to.include('authorization');
        expect(request.url).not.to.match(
          /\/games\/|\/snapshots|\/deliveries|\/api\/ai-usage|socket\.io|private/i,
        );
        expect(unexpectedRequests).to.deep.equal([]);
      });
      cy.window().its('__overlaySocketUrls').should('deep.equal', []);
    });
  });

  it('loads a published YouTube video only after keyboard activation and keeps the watch fallback', () => {
    const scorecardUrl =
      `/community/${publicIdentifier}/competitions/${competitionPublicKey}` +
      `/scorecards/${scorecardPublicIdentifier}`;
    const apiRequests: Array<{ url: string; headers: Record<string, string> }> = [];
    const providerRequests: string[] = [];
    const unexpectedRequests: Array<{ url: string; method: string; resourceType: string }> = [];
    const socketUrls: string[] = [];
    const appOrigin = new URL(Cypress.config('baseUrl')!).origin;
    const configuredApiBase = Cypress.env('API_BASE') || 'http://127.0.0.1:8000';
    const canonicalApiOrigin = new URL(configuredApiBase).origin;
    const expectedFeed = new URL(scorecardPath, configuredApiBase);
    const staticResourceTypes = new Set(['document', 'stylesheet', 'script', 'image', 'font', 'manifest']);

    cy.viewport(375, 812);
    cy.intercept('**/*', (request) => {
      const url = new URL(request.url);
      const resourceType = request.resourceType || 'unknown';
      const hasAuthorization = Object.keys(request.headers).some(
        (header) => header.toLowerCase() === 'authorization',
      );
      if (url.origin === 'https://www.youtube-nocookie.com') {
        providerRequests.push(request.url);
        request.reply({ statusCode: 503, body: 'Synthetic blocked player' });
        return;
      }

      const isCanonicalScorecardRequest =
        request.method === 'GET' &&
        url.origin === canonicalApiOrigin &&
        url.pathname === expectedFeed.pathname &&
        !url.search &&
        !hasAuthorization &&
        (resourceType === 'fetch' || resourceType === 'xhr');
      const isScorecardDocument =
        url.origin === appOrigin &&
        url.pathname === scorecardUrl &&
        request.method === 'GET' &&
        resourceType === 'document';
      const isStaticAsset =
        url.origin === appOrigin &&
        request.method === 'GET' &&
        (url.pathname.startsWith('/assets/') ||
          url.pathname === '/logo.png' ||
          url.pathname.startsWith('/favicon')) &&
        staticResourceTypes.has(resourceType);

      if (isCanonicalScorecardRequest) {
        apiRequests.push({ url: request.url, headers: request.headers });
        request.reply({ statusCode: 200, body: syntheticScorecard });
        return;
      }
      if (isScorecardDocument || isStaticAsset) {
        request.continue();
        return;
      }
      if (url.origin === canonicalApiOrigin || resourceType === 'fetch' || resourceType === 'xhr') {
        apiRequests.push({ url: request.url, headers: request.headers });
      }
      unexpectedRequests.push({ url: request.url, method: request.method, resourceType });
      request.reply({ statusCode: 599, body: {} });
    });

    cy.visit(`${scorecardUrl}?apiBase=${encodeURIComponent('https://unsafe.example.invalid')}`, {
      onBeforeLoad(win) {
        win.localStorage.setItem('cricksy_token', 'synthetic-video-test-token');
        (win as any).__scorecardSocketUrls = socketUrls;
        class BlockedWebSocket {
          constructor(url: string | URL) {
            socketUrls.push(String(url));
          }
          addEventListener() {}
          removeEventListener() {}
          close() {}
          send() {}
        }
        win.WebSocket = BlockedWebSocket as unknown as typeof win.WebSocket;
      },
    });

    cy.contains('Synthetic Adult XI').should('be.visible');
    cy.get('.youtube-player').should('be.visible');
    cy.get('iframe').should('not.exist');
    cy.wait(300);
    cy.then(() => {
      expect(apiRequests).to.have.length(1);
      expect(new URL(apiRequests[0].url).pathname).to.equal(expectedFeed.pathname);
      expect(apiRequests[0].url).not.to.include('unsafe.example.invalid');
      expect(Object.keys(apiRequests[0].headers).map((header) => header.toLowerCase())).not.to.include('authorization');
      expect(providerRequests).to.deep.equal([]);
      expect(unexpectedRequests).to.deep.equal([]);
      expect(socketUrls).to.deep.equal([]);
    });

    cy.contains('button', 'Load YouTube video').focus().type('{enter}');
    cy.get('.youtube-player iframe')
      .should('have.attr', 'src', 'https://www.youtube-nocookie.com/embed/AbCdEf123_-')
      .and('have.attr', 'referrerpolicy', 'strict-origin-when-cross-origin')
      .and('have.attr', 'title', 'Associated YouTube video');
    cy.contains('a', 'Watch on YouTube')
      .should('have.attr', 'href', 'https://www.youtube.com/watch?v=AbCdEf123_-')
      .and('have.attr', 'target', '_blank')
      .and('have.attr', 'rel', 'noopener noreferrer');
    cy.wait(300);
    cy.get('.youtube-player').should('be.visible');
    cy.get('.youtube-frame').invoke('width').should('be.lte', 375);
    cy.then(() => {
      expect(providerRequests).to.deep.equal([
        'https://www.youtube-nocookie.com/embed/AbCdEf123_-',
      ]);
      expect(apiRequests).to.have.length(1);
      expect(unexpectedRequests).to.deep.equal([]);
    });
    cy.screenshot('synthetic-adult-scorecard-video-mobile');
  });
});
