/**
 * Gene signature constants — mirrors backend/app/signatures.py.
 * Used by the frontend to initialize visible gene sets before results load.
 */

export const NASCENT_HSC: string[] = [
  "RUNX1", "MLLT3", "HOXA9", "MECOM", "HLF", "SPINK2", "MYB", "GFI1", "STAT5A",
  "ZBTB16", "HOPX", "GATA2", "GBP4", "ITGA2B", "KCNK17", "SVOPL", "C2orf88",
  "SELP", "CD82", "ITGA4", "GP9", "TMEM163", "RAB27B", "SMIM24", "GMPR", "PDLIM1",
  "ALDH1A1", "NRGN", "CCDC173", "CXCL3", "CYTL1", "PRSS57", "ANGPT1", "CD34",
  "PECAM1", "CDH5", "ECSCR", "CALCRL", "PROCR", "ESAM", "TIE1", "EMCN",
];

export const HSC_MATURATION: string[] = [
  "CDH5", "MEIS2", "RUNX1T1", "ESAM", "PLVAP", "SELP", "ITGA2B", "GP9", "RAB27B",
  "GMPR", "GFI1", "GBP4", "MECOM", "IGFBP2", "HMGA2", "LIN28B", "IL3RA", "IL6R",
  "IL11RA", "IFNAR1", "IFNAR2", "IFNGR1", "CSF1R", "CSF2RA", "MKI67", "TOP2A",
  "AURKB", "HLA-A", "HLA-B", "HLA-C", "HLA-E", "B2M", "HLA-DMA", "HLA-DPB1",
  "HLA-DRA", "HLA-DQA1", "HLA-DPA1", "HLA-DQB1", "MLLT3", "HLF", "MALAT1",
  "MSI2", "EVI2B", "SOCS2", "HEMGN", "HOPX", "SPINK2", "CD52", "SELL", "PROM1",
];
