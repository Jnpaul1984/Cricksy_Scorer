import { vi } from 'vitest'
import { defineComponent, h } from 'vue'

const ChartStub = defineComponent({
  name: 'ChartStub',
  props: {
    data: {
      type: Object,
      required: false,
    },
    options: {
      type: Object,
      required: false,
    },
  },
  setup(props, { attrs }) {
    return () =>
      h(
        'div',
        {
          class: 'chart-stub',
          'data-chart': props.data ? JSON.stringify(props.data) : undefined,
          ...attrs,
        },
        [],
      )
  },
})

vi.mock('chart.js', () => {
  type Any = any

  class MockChart {
    config: Any
    ctx: Any
    constructor(ctx: Any, config: Any) {
      this.ctx = ctx
      this.config = config
    }
    update(): void {}
    destroy(): void {}
    static register(): void {}
  }

  const stub = {}
  const stubPlugin = {}

  return {
    Chart: MockChart,
    register: MockChart.register,
    CategoryScale: stub,
    LinearScale: stub,
    PointElement: stub,
    LineElement: stub,
    BarElement: stub,
    Title: stubPlugin,
    Tooltip: stubPlugin,
    Legend: stubPlugin,
    Filler: stubPlugin,
    registerables: [],
    default: MockChart,
  }
})

vi.mock('vue-chartjs', () => ({
  Line: ChartStub,
  Bar: ChartStub,
}))
