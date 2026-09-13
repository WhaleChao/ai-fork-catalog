# MAGI 技術 Fork 目錄

整理可供 MAGI 研究的開源技術，涵蓋推論效能、記憶體、逐字稿、翻譯與 Agent／MCP 架構。Fork 代表技術收藏，採用建議不代表已整合。

最近檢查（UTC）：2026-09-13T04:45:48+00:00　｜　Fork：64　｜　本次新增：0　｜　本次同步異常：2

摘要沿用原專案語言；星數與授權以來源倉庫為準。私有 MAGI 的實作路徑、設定與資料不在此公開目錄中。

## 推論速度與記憶體（12）

| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |
|---|---|---|---|---:|---|---|---|
| [llama-cpp-turboquant](https://github.com/WhaleChao/llama-cpp-turboquant) · [來源](https://github.com/ggml-org/llama.cpp) | C/C++ LLM inference fork in the llama.cpp network, focused on TurboQuant. | 量化與記憶體參考 | 跨平台待驗證 | 128,028 | MIT | 架構參考 | 需處理：合併衝突 |
| [vllm](https://github.com/WhaleChao/vllm) · [來源](https://github.com/vllm-project/vllm) | High-throughput, memory-efficient LLM inference and serving engine. | 吞吐量與顯存管理 | NVIDIA／Linux；Windows 待驗證 | 91,600 | Apache-2.0 | 優先試驗 | 已是最新 |
| [sglang](https://github.com/WhaleChao/sglang) · [來源](https://github.com/sgl-project/sglang) | High-performance serving framework for language and multimodal models. | 模型服務與批次處理 | NVIDIA／Linux；Windows 待驗證 | 35,870 | Apache-2.0 | 優先試驗 | 已更新 |
| [mlx](https://github.com/WhaleChao/mlx) · [來源](https://github.com/ml-explore/mlx) | Array framework for efficient machine learning on Apple Silicon. | 本機推論核心 | Apple Silicon | 28,398 | MIT | 架構參考 | 已是最新 |
| [omlx](https://github.com/WhaleChao/omlx) · [來源](https://github.com/jundot/omlx) | Apple Silicon LLM server with continuous batching and SSD caching. | 模型服務與快取 | Apple Silicon | 21,667 | Apache-2.0 | 優先試驗 | 已是最新 |
| [LMCache](https://github.com/WhaleChao/LMCache) · [來源](https://github.com/LMCache/LMCache) | Shared KV-cache layer for accelerating repeated LLM inference. | KV 快取與記憶體 | NVIDIA／Linux；Windows 待驗證 | 11,776 | Apache-2.0 | 架構參考 | 已更新 |
| [bitsandbytes](https://github.com/WhaleChao/bitsandbytes) · [來源](https://github.com/bitsandbytes-foundation/bitsandbytes) | Low-bit quantization components for PyTorch language models. | 量化與顯存占用 | CUDA／跨平台待驗證 | 8,475 | MIT | 優先試驗 | 已是最新 |
| [mlx-lm](https://github.com/WhaleChao/mlx-lm) · [來源](https://github.com/ml-explore/mlx-lm) | Run and optimize language models with MLX on Apple Silicon. | 本機模型載入與推論 | Apple Silicon | 6,991 | MIT | 優先試驗 | 已是最新 |
| [esp32-ai](https://github.com/WhaleChao/esp32-ai) · [來源](https://github.com/slvDev/esp32-ai) | Runs a small language model on an ESP32 with most weights stored in flash. | 極低記憶體推論參考 | ESP32 | 4,335 | MIT | 架構參考 | 已是最新 |
| [local-llm](https://github.com/WhaleChao/local-llm) · [來源](https://github.com/jamesob/local-llm) | Practical notes and examples for running language models locally. | 本機模型部署 | 跨平台待驗證 | 1,832 | 未辨識 | 架構參考 | 已是最新 |
| [kvpress](https://github.com/WhaleChao/kvpress) · [來源](https://github.com/NVIDIA/kvpress) | Methods and tools for compressing LLM KV cache. | 上下文記憶體壓縮 | NVIDIA／待驗證 | 1,209 | Apache-2.0 | 架構參考 | 已是最新 |
| [pi-ds4](https://github.com/WhaleChao/pi-ds4) · [來源](https://github.com/mitsuhiko/pi-ds4) | Run a DeepSeek GGUF model locally on Apple Metal from Pi. | Apple 裝置本機模型 | Apple Silicon | 170 | MIT | 架構參考 | 已是最新 |

## 逐字稿與語者辨識（10）

| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |
|---|---|---|---|---:|---|---|---|
| [whisper.cpp](https://github.com/WhaleChao/whisper.cpp) · [來源](https://github.com/ggml-org/whisper.cpp) | Portable C/C++ implementation of Whisper speech recognition. | 低負擔離線逐字稿 | 跨平台 | 53,637 | MIT | 優先試驗 | 已是最新 |
| [faster-whisper](https://github.com/WhaleChao/faster-whisper) · [來源](https://github.com/SYSTRAN/faster-whisper) | Faster Whisper speech recognition powered by CTranslate2. | 逐字稿速度與記憶體 | 跨平台待驗證 | 25,363 | MIT | 優先試驗 | 已是最新 |
| [whisperX](https://github.com/WhaleChao/whisperX) · [來源](https://github.com/m-bain/whisperX) | Whisper transcription with word-level timestamps and diarization. | 逐字時間戳與語者 | 跨平台待驗證 | 24,008 | BSD-2-Clause | 優先試驗 | 已是最新 |
| [FunASR](https://github.com/WhaleChao/FunASR) · [來源](https://github.com/modelscope/FunASR) | Speech toolkit for streaming ASR, VAD, punctuation and diarization. | 中文逐字稿與串流 | 跨平台待驗證 | 20,291 | MIT | 優先試驗 | 已是最新 |
| [WhisperLiveKit](https://github.com/WhaleChao/WhisperLiveKit) · [來源](https://github.com/QuentinFuxa/WhisperLiveKit) | Local real-time transcription with streaming ASR and speaker diarization. | 即時逐字稿 | 跨平台待驗證 | 11,029 | Apache-2.0 | 架構參考 | 已是最新 |
| [pyannote-audio](https://github.com/WhaleChao/pyannote-audio) · [來源](https://github.com/pyannote/pyannote-audio) | Neural components for speaker diarization and speech activity detection. | 語者分離與 VAD | 跨平台待驗證 | 10,539 | MIT | 優先試驗 | 已是最新 |
| [mlx-audio](https://github.com/WhaleChao/mlx-audio) · [來源](https://github.com/Blaizzy/mlx-audio) | MLX library for speech-to-text, text-to-speech and speech processing. | Apple 裝置語音後端 | Apple Silicon | 7,877 | MIT | 優先試驗 | 已是最新 |
| [FluidAudio](https://github.com/WhaleChao/FluidAudio) · [來源](https://github.com/FluidInference/FluidAudio) | On-device speech, VAD and diarization components in Swift/Core ML. | Apple 裝置語音處理 | Apple Silicon | 2,760 | Apache-2.0 | 優先試驗 | 已是最新 |
| [noScribe](https://github.com/WhaleChao/noScribe) · [來源](https://github.com/kaixxx/noScribe) | Offline audio-transcription GUI using Whisper and speaker identification. | 離線逐字稿介面 | 跨平台待驗證 | 2,154 | GPL-3.0 | 架構參考 | 已是最新 |
| [ownscribe](https://github.com/WhaleChao/ownscribe) · [來源](https://github.com/paberr/ownscribe) | Local-first meeting transcription and summarization CLI. | 會議逐字稿 | 跨平台待驗證 | 102 | MIT | 架構參考 | 已是最新 |

## 翻譯（5）

| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |
|---|---|---|---|---:|---|---|---|
| [PDFMathTranslate](https://github.com/WhaleChao/PDFMathTranslate) · [來源](https://github.com/PDFMathTranslate/PDFMathTranslate) | Translate PDFs while preserving document layout and bilingual formatting. | 文件翻譯與版面 | 跨平台待驗證 | 36,876 | AGPL-3.0 | 架構參考 | 已是最新 |
| [pyvideotrans](https://github.com/WhaleChao/pyvideotrans) · [來源](https://github.com/jianchang512/pyvideotrans) | Translate video and generate dubbed audio or subtitles. | 影音逐字稿與字幕 | 跨平台待驗證 | 18,986 | GPL-3.0 | 架構參考 | 已是最新 |
| [LibreTranslate](https://github.com/WhaleChao/LibreTranslate) · [來源](https://github.com/LibreTranslate/LibreTranslate) | Self-hosted machine-translation API with offline deployment options. | 離線翻譯服務 | 跨平台待驗證 | 16,383 | AGPL-3.0 | 架構參考 | 已是最新 |
| [argos-translate](https://github.com/WhaleChao/argos-translate) · [來源](https://github.com/argosopentech/argos-translate) | Offline machine-translation library for Python applications. | 本機文字翻譯 | 跨平台 | 6,454 | MIT | 優先試驗 | 已是最新 |
| [CTranslate2](https://github.com/WhaleChao/CTranslate2) · [來源](https://github.com/OpenNMT/CTranslate2) | Fast inference engine for Transformer translation and speech models. | 翻譯與 ASR 推論速度 | 跨平台待驗證 | 4,670 | MIT | 優先試驗 | 已是最新 |

## Agent 與 MCP 架構（21）

| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |
|---|---|---|---|---:|---|---|---|
| [hermes-agent](https://github.com/WhaleChao/hermes-agent) · [來源](https://github.com/NousResearch/hermes-agent) | Extensible personal AI agent with tools, skills and persistent memory. | Agent 執行與記憶 | 跨平台待驗證 | 244,936 | MIT | 架構參考 | 已更新 |
| [OpenHands](https://github.com/WhaleChao/OpenHands) · [來源](https://github.com/OpenHands/OpenHands) | AI software-development agent that plans, edits and runs code. | 編碼 Agent 工作流 | 跨平台待驗證 | 87,699 | MIT | 架構參考 | 已是最新 |
| [crawl4ai](https://github.com/WhaleChao/crawl4ai) · [來源](https://github.com/unclecode/crawl4ai) | Open-source web crawler that extracts LLM-ready content. | Agent 網頁擷取 | 跨平台待驗證 | 82,711 | Apache-2.0 | 架構參考 | 已是最新 |
| [crewAI](https://github.com/WhaleChao/crewAI) · [來源](https://github.com/crewAIInc/crewAI) | Framework for orchestrating autonomous, role-based agent teams. | 多 Agent 編排 | Python／跨平台 | 58,423 | MIT | 架構參考 | 已是最新 |
| [nanobot](https://github.com/WhaleChao/nanobot) · [來源](https://github.com/HKUDS/nanobot) | Lightweight self-hosted agent framework with tools, memory and MCP. | 輕量 Agent 與記憶 | Python／跨平台待驗證 | 48,068 | MIT | 架構參考 | 已是最新 |
| [langgraph](https://github.com/WhaleChao/langgraph) · [來源](https://github.com/langchain-ai/langgraph) | Stateful workflow framework for building resilient agents. | Agent 狀態與流程 | Python／跨平台 | 41,544 | MIT | 優先試驗 | 已是最新 |
| [financial-services](https://github.com/WhaleChao/financial-services) · [來源](https://github.com/anthropics/financial-services) | Reference financial-services agents, skills and data connectors. | 領域 Agent 參考 | 跨平台待驗證 | 34,806 | Apache-2.0 | 架構參考 | 已是最新 |
| [fastmcp](https://github.com/WhaleChao/fastmcp) · [來源](https://github.com/PrefectHQ/fastmcp) | Python framework for building MCP servers and clients. | MCP 工具介面 | Python／跨平台 | 27,636 | Apache-2.0 | 優先試驗 | 已是最新 |
| [grok-build](https://github.com/WhaleChao/grok-build) · [來源](https://github.com/xai-org/grok-build) | SpaceXAI's coding agent harness and TUI. Fullscreen, mouse interactive, extensible. | Agent 與 MCP 架構 | 待評估 | 26,707 | Apache-2.0 | 待評估 | 已是最新 |
| [haystack](https://github.com/WhaleChao/haystack) · [來源](https://github.com/deepset-ai/haystack) | Modular pipelines for agents, retrieval, memory and generation. | 檢索與 Agent 工作流 | Python／跨平台 | 26,491 | Apache-2.0 | 架構參考 | 已是最新 |
| [open-code-review](https://github.com/WhaleChao/open-code-review) · [來源](https://github.com/alibaba/open-code-review) | Hybrid deterministic and LLM-agent code review with line-level findings. | Agent 程式審查 | 跨平台待驗證 | 22,773 | Apache-2.0 | 架構參考 | 已是最新 |
| [adk-python](https://github.com/WhaleChao/adk-python) · [來源](https://github.com/google/adk-python) | Python toolkit for building, evaluating and deploying AI agents. | Agent 開發與評估 | Python／跨平台 | 21,518 | Apache-2.0 | 架構參考 | 已是最新 |
| [pydantic-ai](https://github.com/WhaleChao/pydantic-ai) · [來源](https://github.com/pydantic/pydantic-ai) | Typed Python framework for agents, tools and model interfaces. | Agent 型別與工具介面 | Python／跨平台 | 19,888 | MIT | 優先試驗 | 已是最新 |
| [agent-framework](https://github.com/WhaleChao/agent-framework) · [來源](https://github.com/microsoft/agent-framework) | Framework for building and orchestrating Python and .NET agents. | Agent 編排與契約 | Python／.NET | 13,497 | MIT | 架構參考 | 已是最新 |
| [camofox-browser](https://github.com/WhaleChao/camofox-browser) · [來源](https://github.com/jo-inc/camofox-browser) | Headless browser built for AI-agent web automation. | Agent 瀏覽器工具 | 跨平台待驗證 | 10,968 | MIT | 架構參考 | 已是最新 |
| [harness-sdk](https://github.com/WhaleChao/harness-sdk) · [來源](https://github.com/strands-agents/harness-sdk) | Open-source SDK for building and controlling agent harnesses. | Agent 執行核心 | Python／TypeScript | 7,226 | Apache-2.0 | 架構參考 | 已是最新 |
| [codex-chatgpt-web](https://github.com/WhaleChao/codex-chatgpt-web) · [來源](https://github.com/miuuyy/codex-chatgpt-web) | Connects ChatGPT Web as a model source for Codex with tool streaming. | Agent 模型介面 | 跨平台待驗證 | 6,671 | MIT | 架構參考 | 已是最新 |
| [project-golem](https://github.com/WhaleChao/project-golem) · [來源](https://github.com/Arvincreator/project-golem) | OS-level autonomous AI agent with long-term memory, multi-agent coordination, Titan Chronos scheduler & Moltbot Social Core | Agent 與 MCP 架構 | 待評估 | 640 | NOASSERTION | 待評估 | 需處理：合併衝突 |
| [stonkfly](https://github.com/WhaleChao/stonkfly) · [來源](https://github.com/nftechie/stonkfly) | Simulation with experimental memory and guarded trading-agent actions. | Agent 記憶與受控動作 | 待評估 | 454 | MIT | 架構參考 | 已是最新 |
| [tw-legal-rag](https://github.com/WhaleChao/tw-legal-rag) · [來源](https://github.com/aa0101181514/tw-legal-rag) | Open-source CLI for semantic Taiwan legal judgment retrieval. Search judgments, package them for your own AI (ChatGPT/Claude/Gemini), and run a bundle… | Agent 與 MCP 架構 | 待評估 | 316 | NOASSERTION | 待評估 | 已是最新 |
| [line-desktop-mcp](https://github.com/WhaleChao/line-desktop-mcp) · [來源](https://github.com/dtwang/line-desktop-mcp) | Windows MCP tools for reading and managing LINE Desktop conversations. | MCP 桌面整合 | Windows | 115 | MIT | 架構參考 | 已是最新 |

## 其他既有 Fork（16）

| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |
|---|---|---|---|---:|---|---|---|
| [skills](https://github.com/WhaleChao/skills) · [來源](https://github.com/mattpocock/skills) | Skills for Real Engineers. Straight from my .agents directory. | — | 待評估 | 260,593 | MIT | 待評估 | 已是最新 |
| [codex](https://github.com/WhaleChao/codex) · [來源](https://github.com/openai/codex) | Lightweight coding agent that runs in your terminal | — | 待評估 | 123,670 | Apache-2.0 | 待評估 | 已是最新 |
| [MinerU](https://github.com/WhaleChao/MinerU) · [來源](https://github.com/opendatalab/MinerU) | Extracts structured text and layout from PDF and Office documents. | 文件擷取與 OCR | 跨平台待驗證 | 79,776 | NOASSERTION | 架構參考 | 已是最新 |
| [VibeVoice](https://github.com/WhaleChao/VibeVoice) · [來源](https://github.com/microsoft/VibeVoice) | Open-source speech generation and voice-model research project. | 語音生成 | 跨平台待驗證 | 54,233 | MIT | 架構參考 | 已是最新 |
| [awesome-gpt-image-2](https://github.com/WhaleChao/awesome-gpt-image-2) · [來源](https://github.com/freestylefly/awesome-gpt-image-2) | Prompt as Code ／ GPT-Image2 工业级提示词引擎与模板库，530+ 个案例逆向工程，20+ 套工业级模板，并提炼出Skills，持续更新中 | — | 待評估 | 31,530 | MIT | 待評估 | 已是最新 |
| [ebook-treasure-chest](https://github.com/WhaleChao/ebook-treasure-chest) · [來源](https://github.com/jbiaojerry/ebook-treasure-chest) | 欢迎来到电子书下载宝库，一个汇聚了各类电子书下载链接的地方。无论你是喜欢阅读经典文学、经管励志、终身学习、职场创业、技术手册还是其他类型的书籍，这里都能满足你的需求。 该库涵盖了帆书app(原樊登读书)、微信读书、京东读书、喜马拉雅等读书app的大部分电子书。 | — | 待評估 | 18,198 | 未辨識 | 待評估 | 已是最新 |
| [PhotoGIMP](https://github.com/WhaleChao/PhotoGIMP) · [來源](https://github.com/Diolinux/PhotoGIMP) | A Patch for GIMP 3+ for Photoshop Users | — | 待評估 | 17,888 | GPL-3.0 | 架構參考 | 已是最新 |
| [chandra](https://github.com/WhaleChao/chandra) · [來源](https://github.com/datalab-to/chandra) | OCR model that handles complex tables, forms, handwriting with full layout. | — | 待評估 | 12,257 | Apache-2.0 | 待評估 | 已是最新 |
| [codex-security](https://github.com/WhaleChao/codex-security) · [來源](https://github.com/openai/codex-security) | SDKs and CLI for Codex Security | — | 待評估 | 10,668 | Apache-2.0 | 待評估 | 已是最新 |
| [mike](https://github.com/WhaleChao/mike) · [來源](https://github.com/open-legal-products/mike) | Open-source legal AI platform and application reference. | 法律領域工作流 | 待評估 | 4,219 | AGPL-3.0 | 架構參考 | 已是最新 |
| [video-autopilot-kit](https://github.com/WhaleChao/video-autopilot-kit) · [來源](https://github.com/Hao0321/video-autopilot-kit) | Fill-in-your-own-data framework for YouTube / short-form video automation: CapCut JSON + ffmpeg tooling + an onboarding questionnaire. Ships with zero… | — | 待評估 | 2,099 | MIT | 待評估 | 已是最新 |
| [rlhf-book-zh-tw](https://github.com/WhaleChao/rlhf-book-zh-tw) · [來源](https://github.com/ai-twinkle/rlhf-book-zh-tw) | 《RLHF Book》繁體中文翻譯與章節互動實驗。 | 模型訓練參考 | 文件 | 178 | NOASSERTION | 架構參考 | 已是最新 |
| [Yuedu-reader](https://github.com/WhaleChao/Yuedu-reader) · [來源](https://github.com/CHANG-JUI-LIN/Yuedu-reader) | Native iOS reader (EPUB, TXT, RSS, web articles) — unified CoreText pipeline, CJK vertical writing, TTS, WebDAV sync, Legado-compatible rules | — | 待評估 | 146 | MPL-2.0 | 待評估 | 已是最新 |
| [legal-skills-open](https://github.com/WhaleChao/legal-skills-open) · [來源](https://github.com/ThomasMoreAI/legal-skills-open) | Open library of legal AI skills (SKILL.md) for MCP-compatible agents — 39 jurisdictions, 200+ plugins, Apache-2.0. | — | 待評估 | 73 | Apache-2.0 | 待評估 | 已是最新 |
| [relay](https://github.com/WhaleChao/relay) · [來源](https://github.com/YuriCrystal/relay) | Self-hosted link shortener with privacy-first click analytics & cookieless conversion tracking, on Cloudflare Workers + D1. A/B split, device & geo ro… | — | 待評估 | 64 | MIT | 待評估 | 已是最新 |
| [BG_record](https://github.com/WhaleChao/BG_record) · [來源](https://github.com/louisophie/BG_record) | My bloog-sugar md log-file for AI analysis. | — | 待評估 | 3 | GPL-3.0 | 架構參考 | 已是最新 |

## 自動化規則

每日台北時間 10:17 搜尋千星以上、可辨識開源授權的專案；新 Fork 每天最多 3 個，使用來源網路去重。全部既有公開 Fork 每日嘗試同步預設分支；衝突不強制覆寫。

[操作與授權](SETUP.md) · [檢視最近執行紀錄](https://github.com/WhaleChao/ai-fork-catalog/actions) · [機器可讀狀態](data/report.json) · [人工調整摘要與分類](data/overrides.json)
