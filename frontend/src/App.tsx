import { useCallback, useEffect, useState } from "react";
import { Layout } from "@/components/Layout";
import { UploadPanel } from "@/components/UploadPanel";
import { PipelineStatus } from "@/components/PipelineStatus";
import { StageFilter } from "@/components/StageFilter";
import { GeneSignaturePanel } from "@/components/GeneSignaturePanel";
import { DotPlot } from "@/components/DotPlot";
import { UMAPViewer } from "@/components/UMAPViewer";
import { usePipeline } from "@/hooks/usePipeline";
import { useResults } from "@/hooks/useResults";
import type { PipelineMode, StageSummary, UploadedFile } from "@/types";

import { NASCENT_HSC, HSC_MATURATION } from "@/constants/signatures";

export default function App() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [mode, setMode] = useState<PipelineMode>("nascent");
  const [activeStages, setActiveStages] = useState<Set<string>>(new Set());
  const [visibleGenes, setVisibleGenes] = useState<Set<string>>(new Set(NASCENT_HSC));
  const [activeTab, setActiveTab] = useState<"dotplot" | "umap">("dotplot");

  const pipeline = usePipeline();
  const resultsHook = useResults();

  // When mode changes, reset visible genes to the appropriate signature
  useEffect(() => {
    setVisibleGenes(new Set(mode === "nascent" ? NASCENT_HSC : HSC_MATURATION));
  }, [mode]);

  // Fetch results once pipeline is done
  useEffect(() => {
    if (pipeline.isDone && pipeline.jobId) {
      resultsHook.fetch(pipeline.jobId);
    }
  }, [pipeline.isDone, pipeline.jobId]);

  // Initialize active stages from results
  useEffect(() => {
    if (resultsHook.results) {
      setActiveStages(
        new Set(resultsHook.results.stage_summary.map((s: StageSummary) => s.stage))
      );
    }
  }, [resultsHook.results]);

  const handleUploaded = useCallback((files: UploadedFile[]) => {
    setUploadedFiles((prev) => [...prev, ...files]);
  }, []);

  const handleRunPipeline = useCallback(() => {
    const fileIds = uploadedFiles.map((f) => f.file_id);
    if (!fileIds.length) return;
    pipeline.submit(fileIds, { mode });
  }, [uploadedFiles, mode, pipeline]);

  const handleToggleStage = useCallback((stage: string) => {
    setActiveStages((prev) => {
      const next = new Set(prev);
      if (next.has(stage)) next.delete(stage);
      else next.add(stage);
      return next;
    });
  }, []);

  const handleToggleGroup = useCallback((_group: string, stages: string[]) => {
    setActiveStages((prev) => {
      const allActive = stages.every((s) => prev.has(s));
      const next = new Set(prev);
      if (allActive) {
        stages.forEach((s) => next.delete(s));
      } else {
        stages.forEach((s) => next.add(s));
      }
      return next;
    });
  }, []);

  const handleToggleGene = useCallback((gene: string) => {
    setVisibleGenes((prev) => {
      const next = new Set(prev);
      if (next.has(gene)) next.delete(gene);
      else next.add(gene);
      return next;
    });
  }, []);

  const results = resultsHook.results;
  const geneList = mode === "nascent" ? NASCENT_HSC : HSC_MATURATION;
  const geneAvail = results?.gene_availability;
  const availableGenes = geneAvail
    ? (mode === "nascent" ? geneAvail.nascent.available : geneAvail.maturation.available)
    : geneList;
  const missingGenes = geneAvail
    ? (mode === "nascent" ? geneAvail.nascent.missing : geneAvail.maturation.missing)
    : [];

  const sidebar = (
    <>
      <UploadPanel onUploaded={handleUploaded} />

      <div className="run-controls">
        <div className="mode-tabs">
          <button
            className={`mode-tab ${mode === "nascent" ? "mode-tab--active" : ""}`}
            onClick={() => setMode("nascent")}
          >
            Nascent
          </button>
          <button
            className={`mode-tab ${mode === "mature" ? "mode-tab--active" : ""}`}
            onClick={() => setMode("mature")}
          >
            Mature
          </button>
        </div>

        <button
          className="run-btn"
          onClick={handleRunPipeline}
          disabled={!uploadedFiles.length || pipeline.isRunning}
        >
          {pipeline.isRunning ? (
            <>
              <span className="spinner spinner--sm" />
              Running…
            </>
          ) : (
            "Run Pipeline"
          )}
        </button>
      </div>

      {(pipeline.status || pipeline.error) && (
        <PipelineStatus
          status={pipeline.status}
          progress={pipeline.progress}
          step={pipeline.step}
          error={pipeline.error}
          jobId={pipeline.jobId}
        />
      )}

      {results && (
        <>
          <StageFilter
            stages={results.stage_summary}
            activeStages={activeStages}
            onToggle={handleToggleStage}
            onToggleGroup={handleToggleGroup}
          />
          <GeneSignaturePanel
            mode={mode}
            availableGenes={availableGenes}
            missingGenes={missingGenes}
            visibleGenes={visibleGenes}
            onToggleGene={handleToggleGene}
            geneAvailability={geneAvail}
          />
        </>
      )}
    </>
  );

  const main = (
    <div className="main-content">
      {!results && !pipeline.isRunning && (
        <div className="empty-state">
          <img src="/bloodstem.gif" alt="BloodShot" className="empty-state__gif" />
        </div>
      )}

      {results && (
        <>
          <div className="results-meta">
            <span className="results-stat">{results.n_cells.toLocaleString()} cells</span>
            <span className="results-divider">·</span>
            <span className="results-stat">{results.n_genes.toLocaleString()} genes</span>
            <span className="results-divider">·</span>
            <span className="results-stat">{results.stage_summary.length} stages</span>
          </div>

          <div className="plot-tabs">
            <button
              className={`plot-tab ${activeTab === "dotplot" ? "plot-tab--active" : ""}`}
              onClick={() => setActiveTab("dotplot")}
            >
              Dot Plot
            </button>
            <button
              className={`plot-tab ${activeTab === "umap" ? "plot-tab--active" : ""}`}
              onClick={() => setActiveTab("umap")}
            >
              UMAP
            </button>
          </div>

          {activeTab === "dotplot" && (
            <div className="plot-container">
              <DotPlot
                data={results.dot_plot}
                activeStages={activeStages}
                visibleGenes={visibleGenes}
              />
            </div>
          )}

          {activeTab === "umap" && (
            <div className="plot-container">
              <UMAPViewer data={results.umap} activeStages={activeStages} />
            </div>
          )}
        </>
      )}

      {resultsHook.loading && (
        <div className="loading-overlay">
          <span className="spinner" />
          <p>Loading results…</p>
        </div>
      )}

      {resultsHook.error && (
        <div className="error-banner">
          <strong>Error loading results:</strong> {resultsHook.error}
        </div>
      )}
    </div>
  );

  return <Layout sidebar={sidebar} main={main} noScroll={!results && !pipeline.isRunning} />;
}
