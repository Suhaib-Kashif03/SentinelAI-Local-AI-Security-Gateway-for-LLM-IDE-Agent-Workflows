from fastapi import FastAPI

from backend.models import ScanRequest, ScanResponse, CommandScanResponse
from backend.scanner import scan_text
from backend.command_analyzer import analyze_command


app = FastAPI(
    title="SentinelAI",
    description="Local AI Security Gateway for scanning prompts, LLM responses, code, and commands.",
    version="0.2.0"
)


@app.get("/")
def root():
    return {
        "project": "SentinelAI",
        "version": "0.2.0",
        "status": "running",
        "message": "Local AI Security Gateway API is active."
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/scan/prompt", response_model=ScanResponse)
def scan_prompt(request: ScanRequest):
    """
    Scan a user prompt before sending it to an LLM.
    """
    return scan_text(
        content=request.content,
        input_type="prompt"
    )


@app.post("/scan/response", response_model=ScanResponse)
def scan_response(request: ScanRequest):
    """
    Scan an LLM response before showing it to the user or executing suggested actions.
    """
    return scan_text(
        content=request.content,
        input_type="response"
    )


@app.post("/scan/command", response_model=CommandScanResponse)
def scan_command(request: ScanRequest):
    """
    Analyze a terminal command before execution.
    """
    return analyze_command(
        command=request.content
    )