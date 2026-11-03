declare module 'plotly.js-basic-dist-min' {
  type PlotlyInstance = {
    newPlot: (
      target: HTMLElement,
      data: Array<Record<string, unknown>>,
      layout: Record<string, unknown>,
      config: Record<string, unknown>,
    ) => Promise<unknown>
    purge: (target: HTMLElement) => void
  }

  const Plotly: PlotlyInstance
  export default Plotly
}