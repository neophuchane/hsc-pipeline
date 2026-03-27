import type { PipelineMode, StageSummary } from "@/types";

const GROUP_ORDER = ["AGM", "Fetal Liver", "Bone Marrow", "Spleen", "Cord Blood"];

interface Props {
  stages: StageSummary[];
  activeStages: Set<string>;
  onToggle: (stage: string) => void;
  onToggleGroup: (group: string, stages: string[]) => void;
  mode: PipelineMode;
  onModeChange: (mode: PipelineMode) => void;
}

export function StageFilter({ stages, activeStages, onToggle, onToggleGroup, mode, onModeChange }: Props) {
  // Group stages by tissue_group
  const grouped: Record<string, StageSummary[]> = {};
  for (const s of stages) {
    (grouped[s.tissue_group] ??= []).push(s);
  }

  const orderedGroups = [
    ...GROUP_ORDER.filter((g) => g in grouped),
    ...Object.keys(grouped).filter((g) => !GROUP_ORDER.includes(g)),
  ];

  return (
    <div className="stage-filter">
      <div className="mode-tabs">
        <button
          className={`mode-tab ${mode === "nascent" ? "mode-tab--active" : ""}`}
          onClick={() => onModeChange("nascent")}
        >
          Nascent
        </button>
        <button
          className={`mode-tab ${mode === "mature" ? "mode-tab--active" : ""}`}
          onClick={() => onModeChange("mature")}
        >
          Mature
        </button>
      </div>
      <h3 className="panel-heading">Developmental Stages</h3>
      {orderedGroups.map((group) => {
        const groupStages = grouped[group] ?? [];
        const allActive = groupStages.every((s) => activeStages.has(s.stage));
        const someActive = groupStages.some((s) => activeStages.has(s.stage));

        return (
          <div key={group} className="stage-group">
            <label className="stage-group__header">
              <input
                type="checkbox"
                checked={allActive}
                ref={(el) => { if (el) el.indeterminate = someActive && !allActive; }}
                onChange={() => onToggleGroup(group, groupStages.map((s) => s.stage))}
                className="stage-checkbox"
              />
              <span className="stage-group__name">{group}</span>
              <span className="stage-group__count">
                {groupStages.reduce((acc, s) => acc + s.n_cells, 0).toLocaleString()} cells
              </span>
            </label>

            <ul className="stage-list">
              {groupStages.map((s) => (
                <li key={s.stage} className="stage-item">
                  <label className="stage-item__label">
                    <input
                      type="checkbox"
                      checked={activeStages.has(s.stage)}
                      onChange={() => onToggle(s.stage)}
                      className="stage-checkbox"
                    />
                    <span className="stage-name" title={s.stage}>{s.stage}</span>
                    <span className="stage-cell-count">{s.n_cells.toLocaleString()}</span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
