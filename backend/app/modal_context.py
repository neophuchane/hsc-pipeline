"""
Modal runtime context.

These are None when running locally (thread pool + in-memory dict are used).
modal_app.py sets them at startup when running on Modal.
"""

# modal.Dict — distributed job store, persists across function invocations
job_store = None

# Callable — spawns the pipeline as a Modal background function
# Signature: (job_id, file_entries, mode, n_top_genes, n_pcs, resolution, remove_duplicates)
pipeline_fn = None

# Callable — commits the uploads Modal.Volume so the pipeline function can see new files
volume_commit = None
