from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from app.services.ai_service import AIService
from app.controllers.profile import get_current_user
from google.genai import types
import json
import asyncio

router = APIRouter()
ai_service = AIService()


@router.websocket("/ai/stt/ws")
async def stt_websocket(websocket: WebSocket):
    await websocket.accept()
    
    user_id = None
    # Wait for the first message to authenticate and get user_id
    try:
        auth_msg = await websocket.receive_text()
        auth_data = json.loads(auth_msg)
        user_id = auth_data.get("user_id")
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    if not user_id:
        await websocket.close(code=1008, reason="User ID required")
        return

    try:
        async with ai_service.connect_live_stt(user_id) as ai_session:
            
            async def receive_from_ai():
                try:
                    async for message in ai_session.receive():
                        # We are looking for input_transcription (ASR)
                        if message.server_content and message.server_content.input_transcription:
                            transcription = message.server_content.input_transcription
                            transcript = transcription.text
                            # Use getattr to safely check for final status
                            is_final = getattr(transcription, 'is_final', False)
                            await websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": is_final
                            })
                        elif message.server_content and message.server_content.turn_complete:
                            # Log but don't close; keep session alive for continuous streaming
                            print("DEBUG: Turn complete received, keeping session alive")
                except Exception as e:
                    print(f"Error receiving from AI: {e}")

            # Start receiver task
            receiver_task = asyncio.create_task(receive_from_ai())
            
            try:
                while True:
                    # Receive audio chunks from browser
                    data = await websocket.receive_bytes()
                    # Gemini Live API expects raw PCM 16-bit 16kHz
                    # Wrap audio data in types.Blob
                    audio_blob = types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                    await ai_session.send_realtime_input(audio=audio_blob)
            except WebSocketDisconnect:
                print("DEBUG: WebSocket disconnected")
                pass
            finally:
                receiver_task.cancel()
                
    except Exception as e:
        print(f"STT WebSocket Error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()


@router.get("/ai/providers")
async def get_providers(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    providers = await ai_service.get_available_providers()
    return JSONResponse(content=providers)


@router.get("/ai/{provider}/models")
async def get_models(provider: str, request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    models = await ai_service.get_models(provider)
    return JSONResponse(content=models)


@router.get("/ai/{provider}/models/grouped")
async def get_models_grouped(provider: str, request: Request, category: str = None):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    models = await ai_service.get_models_grouped(provider, category)
    return JSONResponse(content=models)


@router.get("/ai/settings")
async def get_settings(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    settings = await ai_service.get_user_settings(user_id)
    if not settings:
        return JSONResponse(content={"configured": False})
    
    return JSONResponse(content={
        "configured": True,
        "provider": settings["provider"],
        "model": settings["model"],
        "stt_provider": settings.get("stt_provider", "browser"),
        "stt_model": settings.get("stt_model", "Browser Built In"),
        "tts_provider": settings.get("tts_provider", "browser"),
        "tts_model": settings.get("tts_model", "Browser Built In"),
    })


@router.post("/ai/settings")
async def save_settings(request: Request, 
                        provider: str = Form(), 
                        model: str = Form(),
                        stt_provider: str = Form(default="browser"),
                        stt_model: str = Form(default="Browser Built In"),
                        stt_mode: str = Form(default="batch"),
                        tts_provider: str = Form(default="browser"),
                        tts_model: str = Form(default="Browser Built In")):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await ai_service.save_user_settings(user_id, provider, model, stt_provider, stt_model, stt_mode, tts_provider, tts_model)
    return JSONResponse(content={
        "status": "ok", 
        "provider": provider, 
        "model": model,
        "stt_provider": stt_provider,
        "stt_model": stt_model,
        "stt_mode": stt_mode,
        "tts_provider": tts_provider,
        "tts_model": tts_model
    })


@router.post("/ai/stt")
async def transcribe(request: Request, file: UploadFile = File(...)):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    try:
        audio_data = await file.read()
        text = await ai_service.transcribe_audio_batch(user_id, audio_data)
        return JSONResponse(content={"text": text})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@router.get("/ai/tts")
async def speak(request: Request, text: str):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    try:
        audio_data = await ai_service.text_to_speech(user_id, text)
        # Detect if it's a WAV (starts with RIFF)
        media_type = "audio/wav" if audio_data.startswith(b"RIFF") else "audio/mpeg"
        return Response(content=audio_data, media_type=media_type)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
