// Single source of truth for Plotly — prevents bundling it twice.
// Both the Plot component and direct Plotly.relayout calls use the same instance.
import Plotly from "plotly.js";
import createPlotlyComponent from "react-plotly.js/factory";

export default Plotly;
export const Plot = createPlotlyComponent(Plotly);
