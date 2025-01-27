from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
import ollama  # Official Ollama Python library
from enum import Enum
from typing import Dict

# Application Metadata for Swagger
app = FastAPI(
    title="Ollama Model Management API",
    description="API for managing and interacting with models using Ollama Python library. Includes model listing, downloading, and generating responses.",
    version="1.0.0",
    contact={
        "name": "Support",
        "url": "https://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

class ModelRequest(BaseModel):
    model_name: str

class GenerateRequest(BaseModel):
    model_name: str
    prompt: str


@app.get("/", tags=["General"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Ollama model management API is running"}


@app.get("/models", tags=["Models"])
async def list_models():
    """
    List all models currently available in Ollama.
    """
    try:
        response: ListResponse = list()
        response = ollama.list()
        for model in response.models:
            print('Name:', model.model)
            print('  Size (MB):', f'{(model.size.real / 1024 / 1024):.2f}')
            if model.details:
                print('  Format:', model.details.format)
                print('  Family:', model.details.family)
                print('  Parameter Size:', model.details.parameter_size)
                print('  Quantization Level:', model.details.quantization_level)
            print('\n')
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"

# Store download status
download_status: Dict[str, DownloadStatus] = {}

@app.post("/models/download", tags=["Models"])
async def download_model(model: ModelRequest, background_tasks: BackgroundTasks):
    """
    Download a new model asynchronously using background tasks with status tracking.
    """
    def download_in_background(model_name: str):
        try:
            download_status[model_name] = DownloadStatus.DOWNLOADING
            ollama.pull(model_name)
            download_status[model_name] = DownloadStatus.COMPLETED
        except Exception as e:
            download_status[model_name] = DownloadStatus.FAILED
            print(f"Error downloading model {model_name}: {str(e)}")

    download_status[model.model_name] = DownloadStatus.PENDING
    background_tasks.add_task(download_in_background, model.model_name)
    
    return {
        "success": True,
        "message": f"Model {model.model_name} download started in background",
        "status": download_status[model.model_name].value
    }

@app.get("/models/download/{model_name}/status", tags=["Models"])
async def get_download_status(model_name: str):
    """
    Get the download status for a specific model.
    """
    status = download_status.get(model_name, None)
    if status is None:
        return {"status": "unknown"}
    return {"status": status.value}


@app.post("/models/{model_name}/generate", tags=["Models"])
async def generate_with_model(model_name: str, request: GenerateRequest):
    """
    Generate a response from a specific model.
    """
    if model_name != request.model_name:
        raise HTTPException(
            status_code=400, detail="Mismatch between URL model name and request body model name."
        )

    try:
        response = ollama.generate(
            model=model_name,
            prompt=request.prompt,
        )
        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.get("/health", tags=["General"])
def health_check():
    """
    Health check endpoint to verify the API status.
    """
    return {"status": "ok"}
