"""
Gene signature definitions for HSC developmental stage classification.
Copied exactly from R source: nascent_expanded_scorecard.R and mature_expanded_dataset.R
"""

NASCENT_HSC: list[str] = [
    "RUNX1", "MLLT3", "HOXA9", "MECOM", "HLF", "SPINK2", "MYB", "GFI1", "STAT5A",
    "ZBTB16", "HOPX", "GATA2", "GBP4", "ITGA2B", "KCNK17", "SVOPL", "C2orf88",
    "SELP", "CD82", "ITGA4", "GP9", "TMEM163", "RAB27B", "SMIM24", "GMPR", "PDLIM1",
    "ALDH1A1", "NRGN", "CCDC173", "CXCL3", "CYTL1", "PRSS57", "ANGPT1", "CD34",
    "PECAM1", "CDH5", "ECSCR", "CALCRL", "PROCR", "ESAM", "TIE1", "EMCN",
]  # 42 genes

HSC_MATURATION: list[str] = [
    "CDH5", "MEIS2", "RUNX1T1", "ESAM", "PLVAP", "SELP", "ITGA2B", "GP9", "RAB27B",
    "GMPR", "GFI1", "GBP4", "MECOM", "IGFBP2", "HMGA2", "LIN28B", "IL3RA", "IL6R",
    "IL11RA", "IFNAR1", "IFNAR2", "IFNGR1", "CSF1R", "CSF2RA", "MKI67", "TOP2A",
    "AURKB", "HLA-A", "HLA-B", "HLA-C", "HLA-E", "B2M", "HLA-DMA", "HLA-DPB1",
    "HLA-DRA", "HLA-DQA1", "HLA-DPA1", "HLA-DQB1", "MLLT3", "HLF", "MALAT1",
    "MSI2", "EVI2B", "SOCS2", "HEMGN", "HOPX", "SPINK2", "CD52", "SELL", "PROM1",
]  # 50 genes

# Developmental ordering from nascent_expanded_scorecard.R
# Ordered AGM → Fetal Liver → Bone Marrow → Spleen
DEVELOPMENTAL_ORDER: list[str] = [
    "agm-4wk-658",
    "agm-5wk-555",
    "agm-5wk-575",
    "FL_CS16_W9",
    "FL1_hpc_CS22",
    "FL2_hpc_CS22",
    "PCW10_BM_1_10x.h5",
    "PCW10_BM_2_10x.h5",
    "PCW11_BM_1_10x.h5",
    "PCW11_BM_2_10x.h5",
    "PCW12_BM_1_10x.h5",
    "PCW12_BM_2_10x.h5",
    "PCW13_BM_1_10x.h5",
    "PCW13_BM_2_10x.h5",
    "PCW14_BM_10x.h5",
    "hSP_12w_1.h5",
    "hSP_12w_2.h5",
    "hSP_13w_1.h5",
    "hSP_13w_2.h5",
    "hSP_14w.h5",
]

# Extended order used in mature_expanded_dataset.R (includes more timepoints)
DEVELOPMENTAL_ORDER_MATURE: list[str] = [
    "agm-4wk-658",
    "agm-5wk-555",
    "agm-5wk-575",
    "liver-6wk-563",
    "liver-8wk-553",
    "FL_CS16_W9",
    "FL1_hpc_CS22",
    "FL2_hpc_CS22",
    "liver-11wk-569",
    "liver-15wk-101",
    "PCW10_BM_1_10x.h5",
    "PCW10_BM_2_10x.h5",
    "PCW11_BM_1_10x.h5",
    "PCW11_BM_2_10x.h5",
    "PCW12_BM_1_10x.h5",
    "PCW12_BM_2_10x.h5",
    "PCW13_BM_1_10x.h5",
    "PCW13_BM_2_10x.h5",
    "PCW14_BM_10x.h5",
    "hSP_12w_1.h5",
    "hSP_12w_2.h5",
    "hSP_13w_1.h5",
    "hSP_13w_2.h5",
    "hSP_14w.h5",
    "cb-40wk-201",
]

# Stage groupings for UI filter panel
STAGE_GROUPS: dict[str, list[str]] = {
    "AGM": ["agm-4wk-658", "agm-5wk-555", "agm-5wk-575"],
    "Fetal Liver": [
        "liver-6wk-563", "liver-8wk-553", "FL_CS16_W9",
        "FL1_hpc_CS22", "FL2_hpc_CS22", "liver-11wk-569", "liver-15wk-101",
    ],
    "Bone Marrow": [
        "PCW10_BM_1_10x.h5", "PCW10_BM_2_10x.h5",
        "PCW11_BM_1_10x.h5", "PCW11_BM_2_10x.h5",
        "PCW12_BM_1_10x.h5", "PCW12_BM_2_10x.h5",
        "PCW13_BM_1_10x.h5", "PCW13_BM_2_10x.h5",
        "PCW14_BM_10x.h5",
    ],
    "Spleen": ["hSP_12w_1.h5", "hSP_12w_2.h5", "hSP_13w_1.h5", "hSP_13w_2.h5", "hSP_14w.h5"],
    "Cord Blood": ["cb-40wk-201"],
}
