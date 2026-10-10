"""Deadline Tracker Agent: manages projects, deadlines, and workload.

Enhanced with:
- Workload health scoring
- Revenue analytics (monthly, projected)
- Client-wise breakdown
- Productivity metrics (hours/day, utilization rate)
- Smart deadline warnings
- Project risk assessment
- Earnings velocity tracking

Storage: /tmp (Render, local) with in-memory fallback.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

DATA_FILE = "/tmp/gigpilot_projects.json"
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
            "created_at": "2026-09-01T10:00:00",
            "notes": "Client needs MVP first, then polish.",
            "hourly_rate": 1667,
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
            "created_at": "2026-09-15T10:00:00",
            "notes": "",
            "hourly_rate": 1875,
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
            "created_at": "2026-08-01T10:00:00",
            "notes": "Delivered and paid.",
            "hourly_rate": 2273,
        },
        {
            "id": 4,
            "client": "CloudNine Labs",
            "title": "Mobile App MVP",
            "status": "active",
            "deadline": "2026-12-15",
            "budget": 350000,
            "currency": "INR",
            "hours_estimated": 200,
            "hours_logged": 12,
            "deliverables": ["React Native app", "Backend API", "Push notifications", "App Store submission"],
            "priority": "high",
            "created_at": "2026-10-01T10:00:00",
            "notes": "New client — signed last week. 30% advance received.",
            "hourly_rate": 1750,
        },
        {
            "id": 5,
            "client": "GreenLeaf Organics",
            "title": "Website Redesign",
            "status": "active",
            "deadline": "2026-10-08",
            "budget": 40000,
            "currency": "INR",
            "hours_estimated": 25,
            "hours_logged": 20,
            "deliverables": ["Landing page", "About page", "Contact form"],
            "priority": "high",
            "created_at": "2026-09-20T10:00:00",
            "notes": "Overdue by 2 days. Client waiting for final delivery.",
            "hourly_rate": 1600,
        },
    ]
    _save_projects(demo)


class DeadlineTrackerAgent:

    def __init__(self):
        _seed_demo()

    def add_project(self, data: dict) -> dict:
        projects = _load_projects()
        budget = float(data.get("budget", 0))
        hours_est = float(data.get("hours_estimated", 0))

        project = {
            "id": max((p.get("id", 0) for p in projects), default=0) + 1,
            "client": data.get("client", "Unknown"),
            "title": data.get("title", "Untitled Project"),
            "status": data.get("status", "active"),
            "deadline": data.get("deadline", ""),
            "budget": budget,
            "currency": data.get("currency", "INR"),
            "hours_estimated": hours_est,
            "hours_logged": float(data.get("hours_logged", 0)),
            "deliverables": data.get("deliverables", []),
            "priority": data.get("priority", "medium"),
            "created_at": datetime.now().isoformat(),
            "notes": data.get("notes", ""),
            "hourly_rate": round(budget / hours_est) if hours_est > 0 else 0,
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
                    hours_est = float(p.get("hours_estimated", 0))
                    hours_logged = float(p.get("hours_logged", 0))
                    progress = round(hours_logged / hours_est * 100) if hours_est > 0 else 0

                    # Risk assessment
                    risk = "on-track"
                    if days_left < 0:
                        risk = "overdue"
                    elif hours_est > 0 and days_left > 0:
                        remaining_hours = hours_est - hours_logged
                        hours_per_day_needed = remaining_hours / max(days_left, 1)
                        if hours_per_day_needed > 8:
                            risk = "at-risk"
                        elif hours_per_day_needed > 5:
                            risk = "tight"

                    entry = {
                        **p,
                        "days_left": days_left,
                        "progress": progress,
                        "risk": risk,
                    }
                    if days_left < 0:
                        overdue.append(entry)
                    else:
                        upcoming.append(entry)
                except (ValueError, TypeError):
                    pass

        upcoming.sort(key=lambda x: x.get("days_left", 999))
        overdue.sort(key=lambda x: x.get("days_left", 0))

        # Analytics
        total_active_revenue = sum(float(p.get("budget", 0)) for p in active)
        total_earned = sum(float(p.get("budget", 0)) for p in completed)
        total_hours = sum(float(p.get("hours_logged", 0)) for p in active)
        total_est_hours = sum(float(p.get("hours_estimated", 0)) for p in active)

        # Workload health
        workload_score = self._calculate_workload_health(active, upcoming, overdue)

        # Client breakdown
        client_breakdown = self._get_client_breakdown(projects)

        # Average hourly rate
        rates = [float(p.get("hourly_rate", 0)) for p in projects if p.get("hourly_rate")]
        avg_hourly = round(sum(rates) / len(rates)) if rates else 0

        # Utilization rate (assuming 8 hrs/day, 22 days/month)
        available_hours_month = 8 * 22  # 176
        utilization = round(total_hours / available_hours_month * 100) if available_hours_month > 0 else 0

        return {
            "total_active_projects": len(active),
            "total_completed": len(completed),
            "overdue_projects": overdue,
            "upcoming_deadlines": upcoming[:5],
            "total_active_revenue": total_active_revenue,
            "total_earned": total_earned,
            "total_hours_logged": total_hours,
            "total_estimated_hours": total_est_hours,
            "projects": self._sort_projects(projects, now),
            "workload_health": workload_score,
            "client_breakdown": client_breakdown,
            "avg_hourly_rate": avg_hourly,
            "utilization_rate": min(utilization, 100),
            "at_risk_count": sum(1 for u in upcoming if u.get("risk") in ("at-risk", "tight")),
        }

    def _sort_projects(self, projects, now):
        """Sort: overdue active → active by deadline → completed → cancelled."""
        def sort_key(p):
            status = p.get("status", "")
            deadline = p.get("deadline", "")
            if status == "active":
                if deadline:
                    try:
                        dl = datetime.fromisoformat(deadline) if "T" in deadline else datetime.strptime(deadline, "%Y-%m-%d")
                        days = (dl - now).days
                        if days < 0:
                            return (0, days)  # overdue first, most overdue at top
                        return (1, days)  # active by closest deadline
                    except (ValueError, TypeError):
                        pass
                return (1, 9999)  # active without deadline
            elif status == "completed":
                return (2, 0)
            return (3, 0)  # cancelled
        return sorted(projects, key=sort_key)

    def _calculate_workload_health(self, active, upcoming, overdue):
        """Calculate workload health: 0-100."""
        score = 100

        # Penalize heavily for overdue — any overdue project should drop out of "healthy"
        score -= len(overdue) * 25

        # Penalize for too many active projects
        if len(active) > 5:
            score -= (len(active) - 5) * 10
        elif len(active) == 0:
            score -= 20  # No work is also unhealthy

        # Penalize for at-risk deadlines
        at_risk = sum(1 for u in upcoming if u.get("risk") in ("at-risk", "tight"))
        score -= at_risk * 10

        # Penalize for high-priority items with very low progress
        for p in active:
            if p.get("priority") == "high":
                hours_est = float(p.get("hours_estimated", 0))
                hours_logged = float(p.get("hours_logged", 0))
                if hours_est > 0 and (hours_logged / hours_est) < 0.15:
                    score -= 5  # Barely started high-priority work

        # Bonus for having buffer time
        if upcoming and upcoming[0].get("days_left", 0) > 7:
            score += 5

        status = "healthy"
        if score >= 75:
            status = "healthy"
        elif score >= 50:
            status = "moderate"
        else:
            status = "stressed"

        return {
            "score": max(0, min(100, score)),
            "status": status,
            "message": self._workload_message(status, len(active), len(overdue)),
        }

    def _workload_message(self, status, active_count, overdue_count):
        if status == "healthy" and overdue_count > 0:
            return f"{active_count} active project(s), but {overdue_count} overdue — address those first."
        elif status == "healthy":
            return f"Looking good! {active_count} active project(s), workload is manageable."
        elif status == "moderate":
            msg = f"Watch your bandwidth — {active_count} active project(s)"
            if overdue_count:
                msg += f" with {overdue_count} overdue"
            return msg + "."
        else:
            msg = f"⚠️ High stress — {active_count} active project(s)"
            if overdue_count:
                msg += f", {overdue_count} overdue"
            return msg + ". Consider delegating or renegotiating deadlines."

    def _get_client_breakdown(self, projects):
        """Group revenue by client."""
        clients = defaultdict(lambda: {"total": 0, "projects": 0, "active": 0})
        for p in projects:
            client = p.get("client", "Unknown")
            clients[client]["total"] += float(p.get("budget", 0))
            clients[client]["projects"] += 1
            if p.get("status") == "active":
                clients[client]["active"] += 1

        return [
            {"client": name, **data}
            for name, data in sorted(clients.items(), key=lambda x: x[1]["total"], reverse=True)
        ]

    def update_project(self, project_id: int, updates: dict) -> dict:
        projects = _load_projects()
        for p in projects:
            if p.get("id") == project_id:
                p.update(updates)
                # Recalculate hourly rate if budget or hours changed
                if "budget" in updates or "hours_estimated" in updates:
                    hours = float(p.get("hours_estimated", 0))
                    if hours > 0:
                        p["hourly_rate"] = round(float(p.get("budget", 0)) / hours)
                _save_projects(projects)
                return p
        return {"error": "Project not found"}

    def log_hours(self, project_id: int, hours: float) -> dict:
        projects = _load_projects()
        for p in projects:
            if p.get("id") == project_id:
                p["hours_logged"] = float(p.get("hours_logged", 0)) + hours
                _save_projects(projects)
                hours_est = float(p.get("hours_estimated", 0))
                progress = round(p["hours_logged"] / hours_est * 100) if hours_est > 0 else 0
                return {
                    "project": p["title"],
                    "hours_logged": p["hours_logged"],
                    "hours_estimated": hours_est,
                    "progress": progress,
                    "remaining": max(0, hours_est - p["hours_logged"]),
                }
        return {"error": "Project not found"}

    def get_analytics(self) -> dict:
        """Return detailed analytics for the analytics page."""
        projects = _load_projects()
        now = datetime.now()

        active = [p for p in projects if p.get("status") == "active"]
        completed = [p for p in projects if p.get("status") == "completed"]

        # Revenue by month (from created_at dates)
        monthly_revenue = defaultdict(float)
        for p in projects:
            created = p.get("created_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    key = dt.strftime("%Y-%m")
                    monthly_revenue[key] += float(p.get("budget", 0))
                except (ValueError, TypeError):
                    pass

        # Priority distribution
        priority_dist = defaultdict(int)
        for p in active:
            priority_dist[p.get("priority", "medium")] += 1

        # Hours efficiency
        total_estimated = sum(float(p.get("hours_estimated", 0)) for p in completed)
        total_actual = sum(float(p.get("hours_logged", 0)) for p in completed)
        efficiency = round(total_estimated / total_actual * 100) if total_actual > 0 else 100

        # Projected monthly income (from active projects)
        projected_monthly = 0
        for p in active:
            budget = float(p.get("budget", 0))
            deadline = p.get("deadline", "")
            if deadline:
                try:
                    dl = datetime.fromisoformat(deadline) if "T" in deadline else datetime.strptime(deadline, "%Y-%m-%d")
                    months_remaining = max(1, (dl - now).days / 30)
                    projected_monthly += budget / months_remaining
                except (ValueError, TypeError):
                    pass

        return {
            "total_revenue": sum(float(p.get("budget", 0)) for p in projects),
            "active_revenue": sum(float(p.get("budget", 0)) for p in active),
            "completed_revenue": sum(float(p.get("budget", 0)) for p in completed),
            "monthly_revenue": dict(sorted(monthly_revenue.items())),
            "projected_monthly_income": round(projected_monthly),
            "total_projects": len(projects),
            "active_count": len(active),
            "completed_count": len(completed),
            "priority_distribution": dict(priority_dist),
            "estimation_accuracy": efficiency,
            "avg_project_value": round(sum(float(p.get("budget", 0)) for p in projects) / len(projects)) if projects else 0,
        }
