"""Deadline Tracker Agent: manages projects, deadlines, and workload.

Storage strategy: tries /tmp (works on Vercel per-request, Render, local).
Falls back to in-memory if /tmp is not writable (some read-only environments).
"""

import json
import os
from datetime import datetime

# /tmp is writable on Vercel lambdas and most PaaS; use it instead of project dir
DATA_FILE = "/tmp/gigpilot_projects.json"

# In-memory fallback
_MEMORY_STORE: list = []


def _load_projects() -> list:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return list(_MEMORY_STORE)


def _save_projects(projects: list):
    global _MEMORY_STORE
    _MEMORY_STORE = list(projects)
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(projects, f, indent=2, default=str)
    except Exception:
        pass


# Seed with demo data so the dashboard looks alive on first load
_DEMO_SEEDED = False

def _seed_demo():
    global _DEMO_SEEDED
    if _DEMO_SEEDED:
        return
    _DEMO_SEEDED = True
    if _load_projects():
        return
    demo = [
        {
            "id": 1,
            "client": "TechStart Solutions",
            "title": "E-Commerce Platform",
            "status": "active",
            "deadline": "2026-11-30",
            "budget": 200000,
            "currency": "INR",
            "hours_estimated": 120,
            "hours_logged": 45,
            "deliverables": ["Homepage", "Product catalog", "Checkout", "Admin panel"],
            "priority": "high",
            "created_at": datetime.now().isoformat(),
            "notes": "Client needs MVP first, then polish.",
        },
        {
            "id": 2,
            "client": "FinBridge Corp",
            "title": "Dashboard Redesign",
            "status": "active",
            "deadline": "2026-10-25",
            "budget": 75000,
            "currency": "INR",
            "hours_estimated": 40,
            "hours_logged": 32,
            "deliverables": ["Figma mockups", "React implementation"],
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "notes": "",
        },
        {
            "id": 3,
            "client": "MedTrack Inc",
            "title": "API Integration",
            "status": "completed",
            "deadline": "2026-09-15",
            "budget": 50000,
            "currency": "INR",
            "hours_estimated": 20,
            "hours_logged": 22,
            "deliverables": ["REST API", "Docs"],
            "priority": "low",
            "created_at": datetime.now().isoformat(),
            "notes": "Delivered and paid.",
        },
    ]
    _save_projects(demo)


class DeadlineTrackerAgent:

    def __init__(self):
        _seed_demo()

    def add_project(self, data: dict) -> dict:
        projects = _load_projects()
        project = {
            "id": max((p.get("id", 0) for p in projects), default=0) + 1,
            "client": data.get("client", "Unknown"),
            "title": data.get("title", "Untitled Project"),
            "status": data.get("status", "active"),
            "deadline": data.get("deadline", ""),
            "budget": data.get("budget", 0),
            "currency": data.get("currency", "INR"),
            "hours_estimated": data.get("hours_estimated", 0),
            "hours_logged": data.get("hours_logged", 0),
            "deliverables": data.get("deliverables", []),
            "priority": data.get("priority", "medium"),
            "created_at": datetime.now().isoformat(),
            "notes": data.get("notes", ""),
        }
        projects.append(project)
        _save_projects(projects)
        return project

    def get_dashboard(self) -> dict:
        projects = _load_projects()
        now = datetime.now()

        active = [p for p in projects if p.get("status") == "active"]
        completed = [p for p in projects if p.get("status") == "completed"]

        upcoming = []
        overdue = []
        for p in active:
            if p.get("deadline"):
                try:
                    dl = datetime.fromisoformat(p["deadline"]) if "T" in p["deadline"] else datetime.strptime(p["deadline"], "%Y-%m-%d")
                    days_left = (dl - now).days
                    entry = {**p, "days_left": days_left}
                    if days_left < 0:
                        overdue.append(entry)
                    else:
                        upcoming.append(entry)
                except (ValueError, TypeError):
                    pass

        upcoming.sort(key=lambda x: x.get("days_left", 999))
        overdue.sort(key=lambda x: x.get("days_left", 0))

        return {
            "total_active_projects": len(active),
            "total_completed": len(completed),
            "overdue_projects": overdue,
            "upcoming_deadlines": upcoming[:5],
            "total_active_revenue": sum(float(p.get("budget", 0)) for p in active),
            "total_earned": sum(float(p.get("budget", 0)) for p in completed),
            "total_hours_logged": sum(float(p.get("hours_logged", 0)) for p in active),
            "projects": projects,
        }

    def update_project(self, project_id: int, updates: dict) -> dict:
        projects = _load_projects()
        for p in projects:
            if p.get("id") == project_id:
                p.update(updates)
                _save_projects(projects)
                return p
        return {"error": "Project not found"}

    def log_hours(self, project_id: int, hours: float) -> dict:
        projects = _load_projects()
        for p in projects:
            if p.get("id") == project_id:
                p["hours_logged"] = float(p.get("hours_logged", 0)) + hours
                _save_projects(projects)
                return {"project": p["title"], "hours_logged": p["hours_logged"]}
        return {"error": "Project not found"}
