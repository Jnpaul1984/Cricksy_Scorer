/// <reference types="cypress" />

// Current Chromium hides the content of a closed native <details> with
// `content-visibility: hidden`. Those descendants keep their layout boxes, so
// jQuery/Cypress `:visible` and `be.visible` still report them as visible even
// though nothing is painted. Element.checkVisibility() reflects what the browser
// actually renders, so assertions about collapsed <details> content use it.

/** Assert the exact, ordered labels of the inputs the browser renders inside `selector`. */
export function expectRenderedInputs(selector: string, labels: string[]) {
  cy.get(`${selector} input`).should($inputs => {
    const rendered = $inputs
      .toArray()
      .filter(input => input.checkVisibility())
      .map(input => input.closest('label')?.firstChild?.textContent?.trim() ?? '')
    expect(rendered, `rendered inputs in ${selector}`).to.deep.equal(labels)
  })
}

/** Assert whether the browser renders the element(s) matched by `selector`. */
export function expectRendered(selector: string, rendered: boolean) {
  cy.get(selector).should($elements => {
    const states = $elements.toArray().map(element => element.checkVisibility())
    expect(states, `rendered state of ${selector}`).to.deep.equal(states.map(() => rendered))
  })
}
