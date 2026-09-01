# Notice and credits

The MIT license in this repository covers the content we wrote: the notes, the benchmark tools in `tools/`, the results in
`results/`, the write-up in `docs/` and `REPORT.md`. It does not cover, and we do not redistribute, the upstream work this
deployment stands on. Each of these keeps its own license and terms; follow them at the source:

- **Reederey87 / MiaAI-Lab**, `glm53-flash-exl3-2x-dgx-spark`: the 2-Spark EXL3 serving kit (Dockerfile, start scripts,
  prod-start). We run their kit as published, with the small fixes described in `NOTES.md`; we do not vendor their files.
- **brandonmusic**, `GLM-5.3-Flash-tr3-4bpw`: the EXL3 / TR3 4bpw quantization (ShapleyMCG License).
- **turboderp**, exllamav3: the EXL3 format and kernels.
- **IncoAI**, `GLM-5.3-Flash-DFlash2`: the DFlash2 speculative-decoding drafter.
- **RedHatAI**, `GLM-5.3-Flash-NVFP4`: the NVFP4 weights served on the comparison lane.
- **zai-org**: GLM-5.3-Flash itself.
- **vLLM project**: the serving engine on both lanes.

The NVFP4 lane's launcher is our own separate repository, `tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark`.
Thanks to dfi, Zeus and Mia for the public pushback that produced version 2 of the write-up.
