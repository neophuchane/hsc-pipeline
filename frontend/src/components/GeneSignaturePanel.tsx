import { useState } from "react";
import type { GeneAvailabilityReport } from "@/types";

interface Props {
  mode: "nascent" | "mature";
  availableGenes: string[];
  missingGenes: string[];
  visibleGenes: Set<string>;
  onToggleGene: (gene: string) => void;
  geneAvailability?: GeneAvailabilityReport;
}

export function GeneSignaturePanel({
  mode,
  availableGenes,
  missingGenes,
  visibleGenes,
  onToggleGene,
  geneAvailability,
}: Props) {
  const [showMissing, setShowMissing] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const pct = geneAvailability
    ? (mode === "nascent"
        ? geneAvailability.nascent.pct_available
        : geneAvailability.maturation.pct_available
      ).toFixed(0)
    : null;

  const title = mode === "nascent" ? "Nascent HSC (42 genes)" : "HSC Maturation (50 genes)";

  return (
    <div className="gene-sig-panel">
      <button
        className="panel-heading panel-heading--btn"
        onClick={() => setCollapsed((v) => !v)}
        aria-expanded={!collapsed}
      >
        <span>{title}</span>
        {pct && (
          <span className="avail-badge" title={`${pct}% of genes found in dataset`}>
            {pct}% found
          </span>
        )}
        <svg
          className={`chevron ${collapsed ? "" : "chevron--open"}`}
          width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {!collapsed && (
        <div className="gene-sig-panel__body">
          {/* Available genes */}
          <p className="gene-section-label">
            Available ({availableGenes.length})
            <button
              className="link-btn"
              onClick={() => availableGenes.forEach((g) => {
                if (!visibleGenes.has(g)) onToggleGene(g);
              })}
            >
              all
            </button>
            <button
              className="link-btn"
              onClick={() => availableGenes.forEach((g) => {
                if (visibleGenes.has(g)) onToggleGene(g);
              })}
            >
              none
            </button>
          </p>
          <div className="gene-grid">
            {availableGenes.map((gene) => (
              <label key={gene} className="gene-tag">
                <input
                  type="checkbox"
                  checked={visibleGenes.has(gene)}
                  onChange={() => onToggleGene(gene)}
                  className="gene-checkbox"
                />
                <span className="gene-label">{gene}</span>
              </label>
            ))}
          </div>

          {/* Missing genes */}
          {missingGenes.length > 0 && (
            <>
              <button
                className="missing-toggle"
                onClick={() => setShowMissing((v) => !v)}
              >
                {showMissing ? "Hide" : "Show"} missing ({missingGenes.length})
              </button>
              {showMissing && (
                <div className="gene-grid gene-grid--missing">
                  {missingGenes.map((gene) => (
                    <span key={gene} className="gene-tag gene-tag--missing">{gene}</span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
