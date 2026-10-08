"""
FastAPI Interface for AI Resume Screening & Ranking System.
Endpoints:
  GET  /         - Interactive Web Dashboard for browser testing & drag-and-drop resume upload
  POST /upload   - Upload one or more resumes directly from browser and screen immediately
  POST /screen   - Ingests and processes resumes from a specified directory
  GET  /results  - Returns the latest screening report
  GET  /health   - System status and configuration check
  GET  /docs     - Interactive Swagger OpenAPI UI
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config import settings
from src.pipeline import ScreeningPipeline
from src.models import ScreeningReport

app = FastAPI(
    title="AI Resume Screeening and Ranking System",
    description="(Kasparro assignment) - Automated ingestion, hard eligibility filtering, GitHub enrichment, and 100-point ranking system for SDE Intern candidates.",
    version="1.0.0"
)

# In-memory storage for the latest run result
_LATEST_REPORT: Optional[ScreeningReport] = None

# Auto-load existing results.json if available
results_file = Path("./output/results.json")
if results_file.exists():
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _LATEST_REPORT = ScreeningReport(
                summary=data["batch_summary"],
                ranked_candidates=data["ranked_shortlist"],
                rejected_candidates=data["rejected_candidates"],
                failed_files=data.get("failed_files", [])
            )
    except Exception:
        pass


class ScreenRequest(BaseModel):
    input_dir: str = "./resumes"
    output_file: Optional[str] = "./output/results.json"
    max_concurrency: Optional[int] = 5


@app.get("/health")
def health_check():
    """Health and configuration status."""
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_configured": bool(settings.gemini_api_key or settings.openai_api_key),
        "github_token_configured": bool(settings.github_token),
        "weights": {
            "ai_project_depth": settings.weight_ai_project_depth,
            "python_backend": settings.weight_python_backend,
            "cloud_fullstack": settings.weight_cloud_fullstack,
            "github_activity": settings.weight_github_activity,
            "engineering_depth": settings.weight_engineering_depth
        }
    }


@app.post("/upload", response_model=ScreeningReport)
async def upload_and_screen(files: List[UploadFile] = File(...)):
    """
    Upload one or more candidate resumes (PDF, DOCX, TXT) and screen them immediately.
    Saves uploaded files to the ./resumes directory and updates ranking results.
    """
    global _LATEST_REPORT
    resumes_dir = Path("./resumes")
    resumes_dir.mkdir(parents=True, exist_ok=True)

    allowed_exts = {".pdf", ".docx", ".doc", ".txt", ".md"}

    saved_files = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"File format '{ext}' not supported for {file.filename}. Allowed: PDF, DOCX, TXT, MD"
            )
        dest_path = resumes_dir / file.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(dest_path)

    pipeline = ScreeningPipeline()
    report = await pipeline.run(resumes_dir)
    _LATEST_REPORT = report

    # Export to results.json
    output_path = Path("./output/results.json")
    pipeline.export_json(report, output_path)

    return report


@app.post("/screen", response_model=ScreeningReport)
async def screen_resumes(req: ScreenRequest):
    """
    Screen all candidate resumes located in the specified input directory.
    Filters hard eligibility, enriches public GitHub activity, scores, and ranks candidates.
    """
    global _LATEST_REPORT
    input_path = Path(req.input_dir)

    if not input_path.exists() or not input_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Input directory does not exist or is not a directory: {req.input_dir}"
        )

    pipeline = ScreeningPipeline(max_concurrency=req.max_concurrency)
    try:
        report = await pipeline.run(input_path)
        _LATEST_REPORT = report

        if req.output_file:
            pipeline.export_json(report, Path(req.output_file))

        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/results", response_model=ScreeningReport)
def get_latest_results():
    """Retrieve the latest screening results."""
    global _LATEST_REPORT
    if _LATEST_REPORT is None:
        raise HTTPException(status_code=404, detail="No screening run completed yet. Call POST /screen first.")
    return _LATEST_REPORT


@app.get("/", response_class=HTMLResponse)
def browser_dashboard():
    """Interactive browser dashboard for testing and exploring candidate rankings."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Resume Screeening and Ranking System</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <!-- Navbar -->
  <nav class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-indigo-500/20">
        AI
      </div>
      <div>
        <h1 class="text-lg font-bold text-white tracking-tight">AI Resume Screeening and Ranking System</h1>
        <p class="text-xs text-slate-400 font-medium">(Kasparro assignment)</p>
      </div>
    </div>
    <div class="flex items-center space-x-4">
      <a href="/docs" target="_blank" class="text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-950/60 border border-indigo-800/60 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition">
        <i class="fa-solid fa-code"></i> Swagger API Docs
      </a>
      <button onclick="triggerScreening()" id="runBtn" class="text-xs font-semibold bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 text-white px-4 py-2 rounded-lg shadow-md shadow-indigo-500/20 flex items-center gap-2 transition active:scale-95">
        <i class="fa-solid fa-rotate" id="syncIcon"></i> Re-Run Screening
      </button>
    </div>
  </nav>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-6 py-8">

    <!-- Upload Resume Dropzone Section -->
    <div class="mb-8 bg-slate-900/90 border-2 border-dashed border-indigo-500/40 hover:border-indigo-500 transition rounded-2xl p-6 text-center shadow-lg shadow-indigo-500/5">
      <div class="max-w-xl mx-auto">
        <div class="w-12 h-12 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-cloud-arrow-up text-xl"></i>
        </div>
        <h2 class="text-base font-bold text-white mb-1">Upload New Resume to Screen</h2>
        <p class="text-xs text-slate-400 mb-4">Upload PDF, DOCX, or TXT candidate resumes. They will be immediately parsed, validated for Python + AI eligibility, enriched via GitHub, and ranked.</p>
        
        <form id="uploadForm" onsubmit="handleUpload(event)" class="flex flex-col sm:flex-row items-center justify-center gap-3">
          <input type="file" id="resumeFileInput" multiple accept=".pdf,.docx,.doc,.txt,.md" class="text-xs text-slate-300 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-indigo-400 hover:file:bg-slate-700 cursor-pointer">
          <button type="submit" id="uploadBtn" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl shadow-md flex items-center gap-2 transition active:scale-95">
            <i class="fa-solid fa-file-import"></i> Upload & Screen Now
          </button>
        </form>
        <div id="uploadStatus" class="text-xs mt-3 text-slate-400 hidden"></div>
      </div>
    </div>

    <!-- Stat Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8" id="statsGrid">
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Total Resumes</div>
        <div class="text-3xl font-bold text-white" id="statTotal">--</div>
        <div class="text-xs text-slate-500 mt-1">resumes/ directory</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">Eligible Candidates</div>
        <div class="text-3xl font-bold text-emerald-400" id="statEligible">--</div>
        <div class="text-xs text-slate-500 mt-1">Python + AI verified</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div class="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1">Hard Rejected</div>
        <div class="text-3xl font-bold text-rose-400" id="statRejected">--</div>
        <div class="text-xs text-slate-500 mt-1">Failed Python / AI filters</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-1">Failed / Corrupt</div>
        <div class="text-3xl font-bold text-amber-400" id="statFailed">--</div>
        <div class="text-xs text-slate-500 mt-1">Isolated corrupt files</div>
      </div>
    </div>

    <!-- Controls & Search -->
    <div class="flex flex-col md:flex-row items-center justify-between gap-4 mb-6">
      <div class="flex items-center space-x-2 bg-slate-900 border border-slate-800 p-1 rounded-xl">
        <button onclick="switchTab('shortlist')" id="tabShortlist" class="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition">
          🏆 Ranked Shortlist
        </button>
        <button onclick="switchTab('rejected')" id="tabRejected" class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition">
          ❌ Rejected Profiles
        </button>
      </div>
      <div class="relative w-full md:w-80">
        <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-500 text-xs"></i>
        <input type="text" id="searchInput" oninput="filterResults()" placeholder="Search candidates, skills, or reasons..." class="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition">
      </div>
    </div>

    <!-- Shortlist View -->
    <div id="shortlistView" class="space-y-4">
      <div class="text-center py-12 text-slate-500" id="loadingState">
        <i class="fa-solid fa-spinner fa-spin text-2xl text-indigo-500 mb-2"></i>
        <p>Loading candidate shortlist...</p>
      </div>
      <div id="candidateList" class="space-y-4"></div>
    </div>

    <!-- Rejected View -->
    <div id="rejectedView" class="hidden space-y-4">
      <div id="rejectedList" class="space-y-4"></div>
    </div>
  </main>

  <script>
    let reportData = null;
    let activeTab = 'shortlist';

    async function loadResults() {
      try {
        const res = await fetch('/results');
        if (!res.ok) throw new Error('No results yet');
        reportData = await res.json();
        renderDashboard();
      } catch (err) {
        document.getElementById('loadingState').innerHTML = `
          <div class="text-slate-400">
            <p class="mb-4 text-sm font-medium">No active screening run in memory.</p>
            <button onclick="triggerScreening()" class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-lg">Run Screening Now</button>
          </div>
        `;
      }
    }

    async function handleUpload(e) {
      e.preventDefault();
      const fileInput = document.getElementById('resumeFileInput');
      const statusDiv = document.getElementById('uploadStatus');
      const uploadBtn = document.getElementById('uploadBtn');

      if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please choose at least one resume file (PDF, DOCX, TXT) to upload.');
        return;
      }

      uploadBtn.disabled = true;
      statusDiv.classList.remove('hidden');
      statusDiv.innerHTML = `<span class="text-indigo-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Uploading ${fileInput.files.length} file(s) and screening...</span>`;

      const formData = new FormData();
      for (const file of fileInput.files) {
        formData.append('files', file);
      }

      try {
        const res = await fetch('/upload', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Upload failed');
        }

        reportData = await res.json();
        renderDashboard();
        statusDiv.innerHTML = `<span class="text-emerald-400"><i class="fa-solid fa-check mr-1"></i> Resumes uploaded and ranked successfully!</span>`;
        fileInput.value = '';
      } catch (err) {
        statusDiv.innerHTML = `<span class="text-rose-400"><i class="fa-solid fa-xmark mr-1"></i> Error: ${err.message}</span>`;
      } finally {
        uploadBtn.disabled = false;
      }
    }

    async function triggerScreening() {
      const btn = document.getElementById('runBtn');
      const icon = document.getElementById('syncIcon');
      btn.disabled = true;
      icon.classList.add('fa-spin');
      btn.classList.add('opacity-70');

      try {
        const res = await fetch('/screen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ input_dir: './resumes', max_concurrency: 5 })
        });
        reportData = await res.json();
        renderDashboard();
      } catch (e) {
        alert('Failed to screen: ' + e.message);
      } finally {
        btn.disabled = false;
        icon.classList.remove('fa-spin');
        btn.classList.remove('opacity-70');
      }
    }

    function renderDashboard() {
      if (!reportData) return;
      const s = reportData.summary;
      document.getElementById('statTotal').innerText = s.total_resumes;
      document.getElementById('statEligible').innerText = s.eligible;
      document.getElementById('statRejected').innerText = s.rejected;
      document.getElementById('statFailed').innerText = s.failed_unreadable;
      document.getElementById('loadingState').classList.add('hidden');

      filterResults();
    }

    function switchTab(tab) {
      activeTab = tab;
      const btnShort = document.getElementById('tabShortlist');
      const btnRej = document.getElementById('tabRejected');
      const viewShort = document.getElementById('shortlistView');
      const viewRej = document.getElementById('rejectedView');

      if (tab === 'shortlist') {
        btnShort.className = 'px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition';
        btnRej.className = 'px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';
        viewShort.classList.remove('hidden');
        viewRej.classList.add('hidden');
      } else {
        btnRej.className = 'px-4 py-2 rounded-lg text-xs font-semibold bg-rose-600 text-white transition';
        btnShort.className = 'px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';
        viewRej.classList.remove('hidden');
        viewShort.classList.add('hidden');
      }
      filterResults();
    }

    function filterResults() {
      if (!reportData) return;
      const query = document.getElementById('searchInput').value.toLowerCase();

      if (activeTab === 'shortlist') {
        const container = document.getElementById('candidateList');
        const filtered = reportData.ranked_candidates.filter(c => 
          c.candidate_name.toLowerCase().includes(query) ||
          c.matched_skills.some(s => s.toLowerCase().includes(query)) ||
          c.project_summary.toLowerCase().includes(query)
        );

        container.innerHTML = filtered.map(c => `
          <div class="bg-slate-900 border border-slate-800 hover:border-slate-700 transition rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
              <div class="flex items-center space-x-3">
                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${
                  c.rank === 1 ? 'bg-amber-400/20 text-amber-300 border border-amber-400/40' :
                  c.rank === 2 ? 'bg-slate-400/20 text-slate-300 border border-slate-400/40' :
                  c.rank === 3 ? 'bg-amber-600/20 text-amber-500 border border-amber-600/40' :
                  'bg-slate-800 text-slate-400'
                }">#${c.rank}</span>
                <div>
                  <h3 class="text-base font-bold text-white flex items-center gap-2">
                    ${c.candidate_name}
                    ${c.applied_penalties.length > 0 ? `<span class="bg-rose-950/60 text-rose-400 border border-rose-800/60 text-[10px] px-2 py-0.5 rounded-full font-semibold">Penalized (-${c.applied_penalties.length > 0 ? (c.applied_penalties[0].includes('12') ? '12' : '8') : ''} pts)</span>` : ''}
                  </h3>
                  <div class="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                    <span><i class="fa-regular fa-file text-slate-500"></i> ${c.file_name || 'resume'}</span>
                    <span>•</span>
                    <span class="text-slate-300"><i class="fa-brands fa-github"></i> ${c.github_summary}</span>
                  </div>
                </div>
              </div>
              <div class="flex items-center space-x-4">
                <div class="text-right">
                  <div class="text-2xl font-black text-emerald-400">${c.total_score}<span class="text-xs text-slate-500 font-normal"> / 100</span></div>
                  <div class="text-[10px] text-slate-400 uppercase tracking-wider">Total Score</div>
                </div>
              </div>
            </div>

            <!-- Score Pill Breakdown -->
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-4 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60 text-xs">
              <div class="flex flex-col"><span class="text-slate-500 text-[10px]">AI Depth (40)</span><span class="font-bold text-indigo-400">${c.score_breakdown.ai_project_depth}</span></div>
              <div class="flex flex-col"><span class="text-slate-500 text-[10px]">Python Backend (30)</span><span class="font-bold text-cyan-400">${c.score_breakdown.python_backend}</span></div>
              <div class="flex flex-col"><span class="text-slate-500 text-[10px]">Cloud/Fullstack (15)</span><span class="font-bold text-blue-400">${c.score_breakdown.cloud_fullstack}</span></div>
              <div class="flex flex-col"><span class="text-slate-500 text-[10px]">GitHub (10)</span><span class="font-bold text-emerald-400">${c.score_breakdown.github}</span></div>
              <div class="flex flex-col"><span class="text-slate-500 text-[10px]">Eng Depth (5)</span><span class="font-bold text-purple-400">${c.score_breakdown.engineering_depth}</span></div>
            </div>

            <!-- Project Summary & Strengths -->
            <p class="text-xs text-slate-300 mb-3"><strong class="text-slate-400 font-semibold">Summary:</strong> ${c.project_summary}</p>
            
            ${c.applied_penalties.length > 0 ? `
              <div class="bg-rose-950/30 border border-rose-900/50 p-2.5 rounded-lg mb-3 text-xs text-rose-300">
                <i class="fa-solid fa-triangle-exclamation mr-1 text-rose-400"></i> ${c.applied_penalties.join('; ')}
              </div>
            ` : ''}

            <!-- Skills Pills -->
            <div class="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800/80">
              ${c.matched_skills.map(s => `<span class="bg-slate-800/80 text-slate-300 px-2 py-0.5 rounded-md text-[11px] font-medium border border-slate-700/50">${s}</span>`).join('')}
            </div>
          </div>
        `).join('');
      } else {
        const container = document.getElementById('rejectedList');
        const filtered = reportData.rejected_candidates.filter(r => 
          r.candidate.toLowerCase().includes(query) ||
          r.rejection_reasons.some(reason => reason.toLowerCase().includes(query)) ||
          r.matched_skills.some(s => s.toLowerCase().includes(query))
        );

        container.innerHTML = filtered.map(r => `
          <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h3 class="text-sm font-bold text-white mb-1">${r.candidate}</h3>
                <div class="space-y-1 mb-3">
                  ${r.rejection_reasons.map(reason => `
                    <div class="text-xs text-rose-400 flex items-center gap-1.5">
                      <i class="fa-solid fa-circle-xmark text-[10px]"></i> ${reason}
                    </div>
                  `).join('')}
                </div>
                <div class="flex flex-wrap gap-1">
                  ${r.matched_skills.length > 0 ? r.matched_skills.map(s => `<span class="bg-slate-800 text-slate-400 text-[10px] px-2 py-0.5 rounded">${s}</span>`).join('') : '<span class="text-xs text-slate-500">No qualifying skills matched</span>'}
                </div>
              </div>
              <span class="text-xs font-semibold px-2.5 py-1 rounded bg-rose-950/60 border border-rose-900 text-rose-400">Ineligible</span>
            </div>
          </div>
        `).join('');
      }
    }

    loadResults();
  </script>
</body>
</html>"""
