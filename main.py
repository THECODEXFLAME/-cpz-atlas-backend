from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr
import geopandas as gpd
import pymc3 as pm
import numpy as np
import requests
import os
from typing import List
from pydantic import BaseModel

class EmailList(BaseModel):
    emails: List[str]
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import simplekml
import hashlib
from datetime import datetime

def generate_request_id(email: str) -> str:
    """Generate a unique request ID for access requests."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{hashlib.sha256(f'{email}{timestamp}'.encode()).hexdigest()[:8]}"

def mock_send_email(to_email: str, subject: str, body: str):
    """Mock email sending function (replace with real email service in production)."""
    print(f"Mock email to {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")

app = FastAPI(title="CPZ Atlas v0.5.10 - Quantum CBRN Defense")

# In-memory storage for access requests and approved emails
access_requests: Dict[str, dict] = {}
approved_emails: Dict[str, datetime] = {}

# Moderator email with immediate access
MODERATOR_EMAIL = "RIVBILBO12@GMAIL.COM"

class AccessRequest(BaseModel):
    email: EmailStr

class AccessResponse(BaseModel):
    message: str
    request_id: Optional[str] = None

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",  # Local development
        "http://localhost:3000",   # Local Next.js
        "https://cpz-atlas.fly.dev",  # Production
        os.getenv("FRONTEND_URL", "*")  # From environment
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

def fetch_schumann_resonance_data():
    """Mocks fetching Schumann resonance data."""
    try:
        # Mock data generation with realistic Schumann resonance frequencies
        return {
            "timestamp": datetime.now().isoformat(),
            "frequencies": {
                "fundamental": np.random.uniform(7.8, 8.2),  # First mode
                "second_harmonic": np.random.uniform(14.1, 14.4),  # Second mode
                "third_harmonic": np.random.uniform(20.3, 20.9),  # Third mode
                "fourth_harmonic": np.random.uniform(26.4, 27.3),  # Fourth mode
            },
            "amplitudes": {
                "fundamental": np.random.uniform(0.5, 2.0),
                "second_harmonic": np.random.uniform(0.2, 0.8),
                "third_harmonic": np.random.uniform(0.1, 0.5),
                "fourth_harmonic": np.random.uniform(0.05, 0.3),
            },
            "anomaly_score": np.random.uniform(0, 1),  # Normalized anomaly score
            "interference_level": np.random.choice(["LOW", "MEDIUM", "HIGH"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Schumann resonance data: {str(e)}")

@app.get("/api/schumann")
async def get_schumann_resonance():
    """Retrieves Schumann resonance data."""
    try:
        data = fetch_schumann_resonance_data()
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Schumann resonance data: {str(e)}")

# Mock data sources (replace with NOAA Kp Index, IRI 2016, synthetic EEG)
def fetch_noaa_kp_index():
    try:
        response = requests.get("https://services.swpc.noaa.gov/json/kp_index.json")
        response.raise_for_status()
        return response.json()[-1]["kp_index"]
    except Exception:
        return 3.5  # Fallback mock value

def compute_zeta_c(lng: float, lat: float):
    try:
        with pm.Model():
            ξ = pm.Normal("ξ", mu=0, sigma=1)
            η = pm.Normal("η", mu=0, sigma=1)
            ζ_c = pm.Deterministic("ζ_c", ξ * 0.5 + η * 0.3 + np.random.random() * 0.2)
            trace = pm.sample(1000, tune=500, return_inferencedata=False)
        mean_ζ_c = np.mean(trace["ζ_c"])
        confidence = np.std(trace["ζ_c"]) / mean_ζ_c
        return mean_ζ_c, confidence
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ζ_c computation failed: {str(e)}")

@app.get("/api/zeta-c")
async def get_zeta_c(lng: float = None, lat: float = None):
    try:
        if lng is not None and lat is not None:
            ζ_c, confidence = compute_zeta_c(lng, lat)
            return JSONResponse(content={"ζ_c": ζ_c, "confidence": confidence})
        
        # Default: Return data for Kyiv, Taipei, Anchorage
        regions = [
            {"id": "Kyiv", "lng": 30.52, "lat": 50.45},
            {"id": "Taipei", "lng": 121.56, "lat": 25.03},
            {"id": "Anchorage", "lng": -149.90, "lat": 61.22},
        ]
        features = []
        for region in regions:
            ζ_c, confidence = compute_zeta_c(region["lng"], region["lat"])
            tier = "1" if ζ_c > 0.8 else "2" if ζ_c > 0.6 else "3"
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [region["lng"], region["lat"]]},
                "properties": {"id": region["id"], "ζ_c": ζ_c, "confidence": confidence, "tier": tier},
            })
        geojson = {"type": "FeatureCollection", "features": features}
        return JSONResponse(content=geojson)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing ζ_c: {str(e)}")

@app.get("/api/elf-anomalies")
async def get_elf_anomalies():
    try:
        # Mock ELF anomalies (0.1–0.5 Hz) for Kyiv, Anchorage
        regions = [
            {"id": "Kyiv", "lng": 30.52, "lat": 50.45},
            {"id": "Anchorage", "lng": -149.90, "lat": 61.22},
        ]
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
                "properties": {"id": r["id"]},
            }
            for r in regions
        ]
        geojson = {"type": "FeatureCollection", "features": features}
        return JSONResponse(content=geojson)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ELF anomalies: {str(e)}")

@app.post("/api/export")
async def export_report(regions: List[str]):
    try:
        # Generate PDF
        pdf_path = "report.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "CPZ Atlas v0.1 Risk Brief")
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 710, f"Regions: {', '.join(regions)}")
        y = 690
        for region in regions:
            ζ_c, confidence = compute_zeta_c(
                30.52 if region == "Kyiv" else 121.56 if region == "Taipei" else -149.90,
                50.45 if region == "Kyiv" else 25.03 if region == "Anchorage" else 61.22
            )
            c.drawString(100, y, f"{region}: ζ_c = {ζ_c:.2f}, Confidence = {(confidence * 100):.1f}%")
            y -= 20
        c.save()

        # Generate KML
        kml_path = "report.kml"
        kml = simplekml.Kml()
        for region in regions:
            coords = [(30.52, 50.45) if region == "Kyiv" else (121.56, 25.03) if region == "Taipei" else (-149.90, 61.22)]
            kml.newpoint(name=region, coords=coords)
        kml.save(kml_path)

        return FileResponse(pdf_path, filename="cpz-atlas-report.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/request-access", response_model=AccessResponse)
async def request_access(request: AccessRequest):
    try:
        email = request.email.lower()
        
        # Check if email is moderator
        if email == MODERATOR_EMAIL.lower():
            return AccessResponse(
                message="Access granted immediately",
                request_id=generate_request_id(email)
            )
            
        # Check if email is already approved
        if email in approved_emails:
            if approved_emails[email] > datetime.now():
                return AccessResponse(
                    message="Access already granted",
                    request_id=None
                )
                
        # Generate request ID and store request
        request_id = generate_request_id(email)
        access_requests[request_id] = {
            "email": email,
            "timestamp": datetime.now(),
            "status": "pending"
        }
        
        # Mock sending email to moderator
        mock_send_email(
            MODERATOR_EMAIL,
            "New CPZ Atlas Access Request",
            f"Access requested by: {email}\nRequest ID: {request_id}"
        )
        
        return AccessResponse(
            message="Access request submitted. Awaiting approval.",
            request_id=request_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Access request failed: {str(e)}")

@app.post("/api/approve-access/{request_id}")
async def approve_access(request_id: str, moderator_email: str):
    try:
        if moderator_email.lower() != MODERATOR_EMAIL.lower():
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        if request_id not in access_requests:
            raise HTTPException(status_code=404, detail="Request not found")
            
        request = access_requests[request_id]
        if request["status"] != "pending":
            raise HTTPException(status_code=400, detail="Request already processed")
            
        # Approve access
        request["status"] = "approved"
        approved_emails[request["email"]] = datetime.now() + timedelta(days=365)
        
        # Mock sending approval email
        mock_send_email(
            request["email"],
            "CPZ Atlas Access Approved",
            "Your access request has been approved."
        )
        
        return JSONResponse(content={"message": "Access approved"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
