import { mount } from '@vue/test-utils'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

describe('ScoreboardWidget', () => {
  it('renders title prop if provided', () => {
    const wrapper = mount(ScoreboardWidget, {
      props: { title: 'Live Score' }
    })
    expect(wrapper.html()).toContain('Live Score')
  })
})
