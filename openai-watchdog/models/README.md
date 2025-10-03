Place-holder for bundled GGUF model.

During CI or release packaging, the file `llama-3.2-3b-instruct-q4_k_m.gguf` should be added here and copied into the image at `/opt/models/llama-3.2-3b-instruct-q4_k_m.gguf` by the Dockerfile.

Note: The actual GGUF file is large and should not be committed to the repository. Instead, see release automation or private artifact storage to provide it at build time.
