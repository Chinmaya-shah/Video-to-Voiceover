document.addEventListener('DOMContentLoaded', () => {

    // Application State
    let currentVideoPath = "/samples/sample_pitch_deck.mp4";
    let currentScriptSegments = [];
    let currentAudioUrl = null;
    let currentOutputVideoUrl = null;

    let elevenLabsApiKey = "";
    let geminiApiKey = "";

    // DOM Elements
    const dropzone = document.getElementById('dropzone');
    const videoFileInput = document.getElementById('video-file-input');
    const loadSampleBtn = document.getElementById('load-sample-btn');

    const origPlayer = document.getElementById('original-video-player');
    const outPlayer = document.getElementById('output-video-player');
    const tabOrigBtn = document.getElementById('tab-original-btn');
    const tabOutBtn = document.getElementById('tab-output-btn');
    const downloadVideoBtn = document.getElementById('download-video-btn');

    const audioPreviewCard = document.getElementById('audio-preview-card');
    const audioPlayer = document.getElementById('audio-player');
    const voiceEngineBadge = document.getElementById('voice-engine-badge');
    const voiceSelect = document.getElementById('voice-select');

    const scriptListContainer = document.getElementById('script-list-container');
    const segmentCountBadge = document.getElementById('segment-count-badge');

    const btnRunPhase1 = document.getElementById('btn-run-phase1');
    const btnRunPhase2 = document.getElementById('btn-run-phase2');
    const btnRunPhase3 = document.getElementById('btn-run-phase3');
    const btnRunFullPipeline = document.getElementById('run-full-pipeline-btn');

    const progressFill = document.getElementById('progress-fill');
    const statusText = document.getElementById('status-message-text');

    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');

    const settingsModal = document.getElementById('settings-modal');
    const openSettingsBtn = document.getElementById('open-settings-btn');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const inputElevenLabsKey = document.getElementById('input-elevenlabs-key');
    const inputGeminiKey = document.getElementById('input-gemini-key');
    const inputGroqKey = document.getElementById('input-groq-key');

    const settingsStatusBadge = document.getElementById('settings-status-badge');
    const elevenlabsHelpText = document.getElementById('elevenlabs-help-text');
    const geminiHelpText = document.getElementById('gemini-help-text');
    const groqHelpText = document.getElementById('groq-help-text');

    let availableVoices = [];
    const btnPlayVoiceSample = document.getElementById('btn-play-voice-sample');
    const voiceSampleAudioPlayer = document.getElementById('voice-sample-audio-player');
    const samplePlayIcon = document.getElementById('sample-play-icon');
    const samplePlayText = document.getElementById('sample-play-text');
    const sampleStatusText = document.getElementById('sample-status-text');

    // Load available voices from backend with sample preview URLs
    async function loadVoices() {
        try {
            const res = await fetch('/api/voices');
            const data = await res.json();
            if (data.voices && data.voices.length > 0) {
                availableVoices = data.voices;
                if (voiceSelect) {
                    voiceSelect.innerHTML = availableVoices.map(v => 
                        `<option value="${v.id}" data-sample="${v.sample_url || ''}" ${v.id === 'kokoro-am_adam' ? 'selected' : ''}>${v.name}</option>`
                    ).join('');
                }
            }
        } catch (err) {
            console.error("Error loading voices:", err);
        }
    }

    // Play/Pause Voice Sample Preview Audio
    if (btnPlayVoiceSample && voiceSampleAudioPlayer) {
        btnPlayVoiceSample.addEventListener('click', () => {
            const selectedOpt = voiceSelect ? voiceSelect.options[voiceSelect.selectedIndex] : null;
            if (!selectedOpt) return;

            const voiceId = voiceSelect.value;
            const sampleUrl = selectedOpt.getAttribute('data-sample') || `/output/voice_samples/sample_${voiceId.replace(/-/g, '_')}.mp3`;
            const voiceName = selectedOpt.text.split('—')[0] ? selectedOpt.text.split('—')[0].trim() : selectedOpt.text;

            if (voiceSampleAudioPlayer.src.includes(sampleUrl) && !voiceSampleAudioPlayer.paused) {
                voiceSampleAudioPlayer.pause();
                if (samplePlayIcon) samplePlayIcon.className = "fa-solid fa-volume-high";
                if (samplePlayText) samplePlayText.innerText = "Listen to Sample";
                if (sampleStatusText) sampleStatusText.innerText = "Paused preview.";
            } else {
                voiceSampleAudioPlayer.src = sampleUrl;
                voiceSampleAudioPlayer.play().then(() => {
                    if (samplePlayIcon) samplePlayIcon.className = "fa-solid fa-pause";
                    if (samplePlayText) samplePlayText.innerText = "Pause Sample";
                    if (sampleStatusText) sampleStatusText.innerText = `🔊 Playing voice sample: ${voiceName}`;
                }).catch(err => {
                    console.warn("Play error:", err);
                    if (sampleStatusText) sampleStatusText.innerText = "Click again to play sample preview.";
                });
            }
        });

        voiceSampleAudioPlayer.addEventListener('ended', () => {
            if (samplePlayIcon) samplePlayIcon.className = "fa-solid fa-volume-high";
            if (samplePlayText) samplePlayText.innerText = "Listen to Sample";
            if (sampleStatusText) sampleStatusText.innerText = "Sample preview completed.";
        });

        if (voiceSelect) {
            voiceSelect.addEventListener('change', () => {
                if (!voiceSampleAudioPlayer.paused) {
                    voiceSampleAudioPlayer.pause();
                    if (samplePlayIcon) samplePlayIcon.className = "fa-solid fa-volume-high";
                    if (samplePlayText) samplePlayText.innerText = "Listen to Sample";
                }
                const selectedOpt = voiceSelect.options[voiceSelect.selectedIndex];
                const voiceName = selectedOpt.text.split('—')[0] ? selectedOpt.text.split('—')[0].trim() : selectedOpt.text;
                if (sampleStatusText) sampleStatusText.innerText = `Selected ${voiceName}. Click 'Listen to Sample' to preview.`;
            });
        }
    }

    // Load persisted encrypted key status on startup
    async function loadSavedKeyStatus() {
        try {
            const res = await fetch('/api/settings/get-keys');
            const data = await res.json();

            if (data.has_elevenlabs && inputElevenLabsKey) {
                inputElevenLabsKey.value = data.elevenlabs_masked;
                if (elevenlabsHelpText) {
                    elevenlabsHelpText.innerText = `✓ Encrypted & Active (${data.elevenlabs_masked})`;
                    elevenlabsHelpText.style.color = "var(--accent-emerald)";
                }
            }

            if (data.has_gemini && inputGeminiKey) {
                inputGeminiKey.value = data.gemini_masked;
                if (geminiHelpText) {
                    geminiHelpText.innerText = `✓ Encrypted & Active (${data.gemini_masked})`;
                    geminiHelpText.style.color = "var(--accent-emerald)";
                }
            }

            if (data.has_groq && inputGroqKey) {
                inputGroqKey.value = data.groq_masked;
                if (groqHelpText) {
                    groqHelpText.innerText = `✓ Encrypted & Active (${data.groq_masked})`;
                    groqHelpText.style.color = "var(--accent-emerald)";
                }
            }

            if ((data.has_elevenlabs || data.has_gemini || data.has_groq) && settingsStatusBadge) {
                settingsStatusBadge.innerText = "✓ API Keys are encrypted with a machine key and stored persistently.";
            }
        } catch (err) {
            console.error("Error loading key status:", err);
        }
    }

    loadVoices();
    loadSavedKeyStatus();

    // Modals & Settings
    if (openSettingsBtn) {
        openSettingsBtn.addEventListener('click', () => {
            loadSavedKeyStatus();
            if (settingsModal) settingsModal.classList.remove('hidden');
        });
    }
    if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', () => settingsModal && settingsModal.classList.add('hidden'));
    
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', async () => {
            elevenLabsApiKey = inputElevenLabsKey ? inputElevenLabsKey.value.trim() : '';
            geminiApiKey = inputGeminiKey ? inputGeminiKey.value.trim() : '';
            const groqApiKey = inputGroqKey ? inputGroqKey.value.trim() : '';

            try {
                const res = await fetch('/api/settings/save-keys', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        elevenlabs_api_key: elevenLabsApiKey,
                        gemini_api_key: geminiApiKey,
                        groq_api_key: groqApiKey
                    })
                });
                const data = await res.json();
                await loadSavedKeyStatus();
                if (settingsModal) settingsModal.classList.add('hidden');
                updateStatus("API Keys encrypted and saved persistently.", 0);
            } catch (err) {
                updateStatus("Error saving keys: " + err.message, 0);
            }
        });
    }

    // Tab Switching
    if (tabOrigBtn) {
        tabOrigBtn.addEventListener('click', () => {
            tabOrigBtn.classList.add('active');
            if (tabOutBtn) tabOutBtn.classList.remove('active');
            if (origPlayer) origPlayer.classList.add('active');
            if (outPlayer) outPlayer.classList.remove('active');
        });
    }

    if (tabOutBtn) {
        tabOutBtn.addEventListener('click', () => {
            tabOutBtn.classList.add('active');
            if (tabOrigBtn) tabOrigBtn.classList.remove('active');
            if (outPlayer) outPlayer.classList.add('active');
            if (origPlayer) origPlayer.classList.remove('active');
        });
    }

    // Error Modal UI Elements
    const errorModal = document.getElementById('error-modal');
    const errorModalMessage = document.getElementById('error-modal-message');
    const closeErrorBtn = document.getElementById('close-error-btn');
    const errorDismissBtn = document.getElementById('error-dismiss-btn');
    const errorOpenKeysBtn = document.getElementById('error-open-keys-btn');

    function showErrorModal(msg) {
        errorModalMessage.innerText = msg;
        errorModal.classList.remove('hidden');
    }

    if (closeErrorBtn) closeErrorBtn.addEventListener('click', () => errorModal.classList.add('hidden'));
    if (errorDismissBtn) errorDismissBtn.addEventListener('click', () => errorModal.classList.add('hidden'));
    if (errorOpenKeysBtn) errorOpenKeysBtn.addEventListener('click', () => {
        errorModal.classList.add('hidden');
        openSettingsBtn.click();
    });

    // File Upload Handlers
    if (videoFileInput) {
        videoFileInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                await handleVideoUpload(e.target.files[0]);
            }
        });
    }

    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', async (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                await handleVideoUpload(e.dataTransfer.files[0]);
            }
        });
    }

    async function handleVideoUpload(file) {
        const titleEl = document.getElementById('dropzone-display-title');
        const subEl = document.getElementById('dropzone-display-sub');
        if (titleEl) titleEl.innerText = `Uploading ${file.name}...`;
        
        const formData = new FormData();
        formData.append('file', file);
        updateStatus(`Uploading ${file.name}...`, 15);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) {
                const errMsg = data.detail || data.error || "Failed to upload video.";
                showErrorModal(errMsg);
                updateStatus("Upload failed: " + errMsg, 0);
                if (titleEl) titleEl.innerText = "Upload Pitch Deck (.pptx, .pdf) or Video (.mp4)";
                return;
            }
            currentVideoPath = data.video_path;
            if (origPlayer) {
                origPlayer.src = data.url;
                origPlayer.load();
            }
            if (titleEl) titleEl.innerText = `✓ File Selected: ${file.name}`;
            if (subEl) subEl.innerText = `Deck Path: ${data.video_path}`;
            updateStatus(`Pitch deck '${file.name}' processed successfully. Ready to generate founder pitch script.`, 25);
        } catch (err) {
            showErrorModal("Upload failed: " + err.message);
            updateStatus("Upload failed: " + err.message, 0);
            if (titleEl) titleEl.innerText = "Upload Pitch Deck (.pptx, .pdf) or Video (.mp4)";
        }
    }

    // Status & Step Helpers
    function updateStatus(msg, percent = 0) {
        statusText.innerText = msg;
        progressFill.style.width = `${percent}%`;
    }

    function setStepState(activeStepNum) {
        [step1, step2, step3].forEach((s, idx) => {
            s.classList.remove('active');
            if (idx + 1 === activeStepNum) s.classList.add('active');
        });
    }

    // Render Script Table
    function renderScriptTable(segments, totalSlides = null, isWebEnriched = false) {
        currentScriptSegments = segments;
        const slideCountStr = totalSlides ? `${totalSlides} Slides Detected` : `${segments.length} Segments`;
        const webStr = isWebEnriched ? " | 🌐 Web Search Enriched" : "";
        segmentCountBadge.innerText = `${slideCountStr}${webStr}`;

        if (!segments || segments.length === 0) {
            scriptListContainer.innerHTML = `
                <div class="empty-placeholder">
                    <i class="fa-solid fa-align-left empty-icon"></i>
                    <p class="empty-title">No script generated yet</p>
                    <p class="empty-desc">Click 'Generate Slide-Wise Script' to analyze video slides.</p>
                </div>`;
            return;
        }

        scriptListContainer.innerHTML = segments.map((seg, idx) => {
            const slideNum = seg.slide_number || idx + 1;
            const words = seg.narration ? seg.narration.trim().split(/\s+/).filter(w => w).length : 0;
            const dur = Math.max(1.0, (seg.end_time || 0) - (seg.start_time || 0));
            const title = seg.slide_title || `Slide ${slideNum}`;
            return `
            <div class="script-box" data-index="${idx}">
                <div class="script-box-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="segment-name" style="font-weight: 700; color: #38bdf8; font-size: 0.95rem;">
                        📊 Slide ${slideNum}: ${title}
                    </span>
                    <span class="segment-time" style="background: rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 12px; font-size: 0.8rem;">
                        ⏱ ${seg.start_time}s – ${seg.end_time}s (${dur.toFixed(1)}s)
                    </span>
                </div>
                <textarea class="script-textarea" rows="3" data-index="${idx}" style="width: 100%; border-radius: 8px; padding: 10px; font-size: 0.92rem; font-family: inherit;">${seg.narration}</textarea>
            </div>
            `;
        }).join('');

        // Attach editable listener
        document.querySelectorAll('.script-textarea').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.getAttribute('data-index'));
                currentScriptSegments[idx].narration = e.target.value;
            });
        });
    }

    async function safeFetchJson(url, options = {}, timeoutMs = 300000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const fetchOptions = { ...options, signal: controller.signal };
            const res = await fetch(url, fetchOptions);
            clearTimeout(timeoutId);
            const text = await res.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch {
                data = { status: "error", error: text || `Server Error (${res.status} ${res.statusText})` };
            }
            return { ok: res.ok, status: res.status, data };
        } catch (err) {
            clearTimeout(timeoutId);
            if (err.name === 'AbortError') {
                return { ok: false, status: 408, data: { status: "error", error: "Request timed out after 5 minutes. Please check server logs." } };
            }
            return { ok: false, status: 0, data: { status: "error", error: err.message } };
        }
    }

    // Phase 1 Execution: Slide Detection & Script Generation
    btnRunPhase1.addEventListener('click', async () => {
        if (!currentVideoPath) {
            showErrorModal("Please upload a video file (.mp4) first before generating the script.");
            return;
        }
        setStepState(1);
        updateStatus("Scanning video frames for slide transitions & running Web Search Enrichment...", 35);
        btnRunPhase1.disabled = true;

        try {
            const { ok, data } = await safeFetchJson('/api/phase1/generate-script', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: currentVideoPath,
                    gemini_api_key: geminiApiKey
                })
            });

            if (!ok || data.status === 'error') {
                const errMsg = data.detail || data.error || "Slide Script Extraction Failed.";
                showErrorModal(errMsg);
                updateStatus("Script Generation Failed: " + errMsg, 0);
                return;
            }

            renderScriptTable(data.script, data.total_slides, data.web_enriched);
            setStepState(2);
            updateStatus(`Success! Detected ${data.total_slides} slides & generated web-enriched scripts.`, 100);
        } catch (err) {
            showErrorModal("Script Generation Error: " + err.message);
            updateStatus("Script Generation Failed: " + err.message, 0);
        } finally {
            btnRunPhase1.disabled = false;
        }
    });

    // Phase 2 Execution
    if (btnRunPhase2) {
        btnRunPhase2.addEventListener('click', async () => {
            if (!currentScriptSegments || currentScriptSegments.length === 0) {
                showErrorModal("No script segments found. Please extract script first.");
                return;
            }
            setStepState(2);
            updateStatus("Phase 2: Synthesizing voiceover audio via ElevenLabs...", 60);
            btnRunPhase2.disabled = true;

            try {
                const { ok, data } = await safeFetchJson('/api/phase2/generate-audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        script_segments: currentScriptSegments,
                        voice_id: voiceSelect ? voiceSelect.value : "kokoro-am_adam",
                        elevenlabs_api_key: elevenLabsApiKey,
                        total_video_duration: origPlayer ? origPlayer.duration || 0 : 0
                    })
                });

                if (!ok || data.status === 'error') {
                    const errMsg = data.detail || data.error || "Phase 2 Audio Synthesis Failed.";
                    showErrorModal(errMsg);
                    updateStatus("Phase 2 Failed: " + errMsg, 0);
                    return;
                }

                currentAudioUrl = data.audio_url;

                if (voiceEngineBadge) voiceEngineBadge.innerText = data.engine;
                if (audioPlayer) audioPlayer.src = data.audio_url;
                if (audioPreviewCard) audioPreviewCard.classList.remove('hidden');
                if (audioPlayer) audioPlayer.play();

                if (btnRunPhase3) btnRunPhase3.disabled = false;
                setStepState(3);
                updateStatus(`Phase 2 Complete (${data.engine})! Audio synthesized. Proceed to Step 3.`, 75);
            } catch (err) {
                showErrorModal("Phase 2 Error: " + err.message);
                updateStatus("Phase 2 Failed: " + err.message, 0);
            } finally {
                btnRunPhase2.disabled = false;
            }
        });
    }

    // Phase 3 Execution
    if (btnRunPhase3) {
        btnRunPhase3.addEventListener('click', async () => {
            setStepState(3);
            updateStatus("Phase 3: Merging video, voiceover audio & burning in subtitles...", 85);
            btnRunPhase3.disabled = true;

            try {
                const { ok, data } = await safeFetchJson('/api/phase3/combine-video', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_path: currentVideoPath,
                        audio_path: currentAudioUrl ? "." + currentAudioUrl : "output/combined_voiceover.mp3",
                        script_segments: currentScriptSegments
                    })
                });

                if (!ok || data.status === 'error') {
                    const errMsg = data.detail || data.error || "Phase 3 Video Rendering Failed.";
                    showErrorModal(errMsg);
                    updateStatus("Phase 3 Failed: " + errMsg, 0);
                    return;
                }

                currentOutputVideoUrl = data.video_url;

                const outputVideoCard = document.getElementById('output-video-card');
                if (outputVideoCard) outputVideoCard.classList.remove('hidden');

                if (outPlayer) {
                    outPlayer.src = data.video_url;
                    outPlayer.load();
                    outPlayer.play();
                }

                if (downloadVideoBtn) {
                    downloadVideoBtn.href = data.video_url;
                    downloadVideoBtn.classList.remove('hidden');
                }

                updateStatus("Phase 3 Complete! Final executive video with Voicebox voiceover rendered successfully.", 100);
            } catch (err) {
                showErrorModal("Phase 3 Error: " + err.message);
                updateStatus("Phase 3 Failed: " + err.message, 0);
            } finally {
                btnRunPhase3.disabled = false;
            }
        });
    }

    // Run Full Pipeline End-to-End
    if (btnRunFullPipeline) {
        btnRunFullPipeline.addEventListener('click', async () => {
            if (!currentVideoPath) {
                showErrorModal("Please upload a video file (.mp4) first before running the full pipeline.");
                return;
            }
            updateStatus("Starting Full End-to-End Pipeline...", 5);
            btnRunFullPipeline.disabled = true;

            try {
                const { ok, data } = await safeFetchJson('/api/pipeline/run-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_path: currentVideoPath,
                        voice_id: voiceSelect ? voiceSelect.value : "kokoro-am_adam",
                        elevenlabs_api_key: elevenLabsApiKey,
                        gemini_api_key: geminiApiKey
                    })
                });

                if (!ok || data.status === 'error') {
                    const errMsg = data.detail || data.error || "Failed to trigger pipeline.";
                    showErrorModal(errMsg);
                    btnRunFullPipeline.disabled = false;
                    return;
                }
                pollTaskStatus(data.task_id);
            } catch (err) {
                showErrorModal("Pipeline trigger failed: " + err.message);
                updateStatus("Pipeline trigger failed: " + err.message, 0);
                btnRunFullPipeline.disabled = false;
            }
        });
    }

    async function pollTaskStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${taskId}`);
                const data = await res.json();

                updateStatus(data.message, data.progress_percent || 0);
                if (data.current_phase) setStepState(data.current_phase);

                if (data.status === 'completed') {
                    clearInterval(interval);
                    btnRunFullPipeline.disabled = false;

                    renderScriptTable(data.result.script_segments);

                    voiceEngineBadge.innerText = data.result.engine_used || "Audio Generator";
                    audioPlayer.src = data.result.audio_url;
                    audioPreviewCard.classList.remove('hidden');

                    outPlayer.src = data.result.final_video_url;
                    outPlayer.load();
                    tabOutBtn.click();
                    outPlayer.play();

                    downloadVideoBtn.href = data.result.final_video_url;
                    downloadVideoBtn.classList.remove('hidden');

                    btnRunPhase2.disabled = false;
                    btnRunPhase3.disabled = false;
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    btnRunFullPipeline.disabled = false;
                    const errMsg = data.error || "Pipeline execution failed.";
                    showErrorModal(errMsg);
                    updateStatus(`Pipeline Failed: ${errMsg}`, 0);
                }
            } catch (err) {
                console.error("Polling status error:", err);
            }
        }, 1500);
    }

});
