import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import asyncio
from app.database import get_connection
from app.models.behavioral import (
    BehavioralResponse, 
    BehavioralProfile, 
    CoreTrait, 
    OperatingStyle, 
    StrategicInsight
)

class BehavioralService:
    def __init__(self):
        self.questions_path = Path(__file__).parent.parent / "resources" / "behavioral_questions.json"
        self._questions = None

    @property
    def questions(self):
        if self._questions is None:
            with open(self.questions_path, "r", encoding="utf-8") as f:
                self._questions = json.load(f)
        return self._questions

    async def save_responses(self, user_id: int, responses: List[BehavioralResponse]):
        conn = await get_connection()
        # Clear existing responses
        await conn.execute("DELETE FROM behavioral_responses WHERE user_id = ?", (user_id,))
        
        # Save new responses
        for resp in responses:
            await conn.execute(
                "INSERT INTO behavioral_responses (user_id, question_id, selected_option) VALUES (?, ?, ?)",
                (user_id, resp.question_id, resp.selected_option)
            )
        await conn.commit()
        
        # Calculate and update profile
        return await self.calculate_profile(user_id)

    async def get_responses(self, user_id: int) -> Dict[int, str]:
        conn = await get_connection()
        conn.row_factory = None
        async with conn.execute(
            "SELECT question_id, selected_option FROM behavioral_responses WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    async def calculate_profile(self, user_id: int) -> BehavioralProfile:
        responses = await self.get_responses(user_id)
        if not responses:
            return None

        # 1. Calculate Core Traits (Weighted Scoring)
        # Weights define how much each vector (A/B/C/D) contributes to a trait
        # 0.0 means the behavior actively negates or is antithetical to the trait
        trait_weights = {
            "Execution & Autonomy":           {"A": 0.5,  "B": 0.0,  "C": 0.75, "D": 1.0},
            "Analytical Rigor & Quality":      {"A": 1.0,  "B": 0.25, "C": 0.0,  "D": 0.5},
            "Collaboration & Synergy":         {"A": 0.5,  "B": 1.0,  "C": 0.25, "D": 0.0},
            "Resilience & Pressure Handling":  {"A": 0.75, "B": 0.5,  "C": 1.0,  "D": 0.75},
            "Accountability & Ownership":      {"A": 0.5,  "B": 0.75, "C": 0.0,  "D": 1.0}
        }
        
        trait_questions = {
            "Execution & Autonomy": [1, 2, 3, 4, 21],
            "Analytical Rigor & Quality": [6, 14, 15, 24, 25],
            "Collaboration & Synergy": [9, 11, 12, 13, 16],
            "Resilience & Pressure Handling": [5, 7, 8, 17, 20],
            "Accountability & Ownership": [10, 18, 23, 19, 22]
        }

        trait_descriptions = {
            "Execution & Autonomy": "Ability to deliver results independently and drive projects without micro-management.",
            "Analytical Rigor & Quality": "Commitment to technical excellence, error prevention, and data-driven decision making.",
            "Collaboration & Synergy": "Effectiveness in team environments, conflict resolution, and knowledge sharing.",
            "Resilience & Pressure Handling": "Emotional stability and effectiveness when facing high-stakes or changing environments.",
            "Accountability & Ownership": "Courage to own mistakes, uphold ethical standards, and challenge the status quo when needed."
        }

        core_traits = []
        for trait_name, q_ids in trait_questions.items():
            score_sum = 0
            for q_id in q_ids:
                ans = responses.get(q_id)
                if ans in trait_weights[trait_name]:
                    score_sum += trait_weights[trait_name][ans]
            
            final_score = (score_sum / len(q_ids)) * 100
            core_traits.append(CoreTrait(
                name=trait_name,
                score=float(final_score),
                description=trait_descriptions[trait_name]
            ))

        # Vector Counts for Pattern Identification
        vector_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for q_id, opt in responses.items():
            if opt in vector_counts:
                vector_counts[opt] += 1
        
        sorted_vectors = sorted(vector_counts.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_vectors[0][0]
        secondary = sorted_vectors[1][0]

        # 2. Calculate Operating Styles (Majority based - unchanged logic but consolidated)
        style_categories = {
            "Decision-Making Style": {
                "questions": [5, 6, 7, 8, 10],
                "options": {
                    "A": {"label": "Data-Driven & Risk-Averse", "desc": "Relies on data and structured analysis to minimize risk."},
                    "B": {"label": "Consensus-Oriented", "desc": "Prioritizes team alignment and shared buy-in for decisions."},
                    "C": {"label": "Agile & Intuitive", "desc": "Makes fast decisions based on intuition and MVP thinking."},
                    "D": {"label": "Process-Bound", "desc": "Follows established rules or escalates to higher authority."}
                }
            },
            "Communication & Alignment": {
                "questions": [14, 15, 16],
                "options": {
                    "A": {"label": "Direct & Consequence-Focused", "desc": "Focuses on real impact, deadlines, and risks."},
                    "B": {"label": "Empathetic & Inclusive", "desc": "Prioritizes team morale and smooth interpersonal dynamics."},
                    "C": {"label": "Action-Oriented & Brief", "desc": "Communicates only what is strictly necessary to unblock tasks."},
                    "D": {"label": "Formal & Documented", "desc": "Prefers written reports, tickets, and formal channels."}
                }
            },
            "Conflict Resolution": {
                "questions": [9, 11, 13],
                "options": {
                    "A": {"label": "Objective & Technical", "desc": "Depersonalizes conflict by focusing on technical data."},
                    "B": {"label": "Mediator & Diplomatic", "desc": "Seeks to de-escalate and find common ground."},
                    "C": {"label": "Pragmatic Testing", "desc": "Resolves disputes through practical experimentation."},
                    "D": {"label": "Hierarchical Escalation", "desc": "Relies on management or seniority to resolve issues."}
                }
            },
            "Work Pacing & Focus": {
                "questions": [1, 2, 3, 4],
                "options": {
                    "A": {"label": "Methodical & Iterative", "desc": "Builds step-by-step with constant validation."},
                    "B": {"label": "Highly Interactive", "desc": "Thrives on pair work and constant team contact."},
                    "C": {"label": "Burst & Sprint", "desc": "Works in high-intensity bursts of productivity."},
                    "D": {"label": "Isolated Deep Work", "desc": "Prefers long periods of uninterrupted individual focus."}
                }
            }
        }

        operating_styles = []
        for category, config in style_categories.items():
            counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for q_id in config["questions"]:
                opt = responses.get(q_id)
                if opt in counts:
                    counts[opt] += 1
            majority_opt = max(counts, key=counts.get)
            style_info = config["options"][majority_opt]
            operating_styles.append(OperatingStyle(
                category=category,
                label=style_info["label"],
                description=style_info["desc"]
            ))

        # 3. Strategic Insights (Pattern and Score Based)
        trait_scores = {t.name: t.score for t in core_traits}
        strategic_insights = []

        # --- A. Archetype Insights (Based on Dominant Vector and Thresholds) ---
        archetypes = [
            {
                "trigger": dominant == "A" and trait_scores.get("Analytical Rigor & Quality", 0) >= 70,
                "title": "The Architect",
                "text": "Builds systems for longevity. Excels in environments that value technical debt reduction and robust documentation. May need to delegate more to avoid becoming a bottleneck."
            },
            {
                "trigger": dominant == "B" and trait_scores.get("Collaboration & Synergy", 0) >= 70,
                "title": "The Catalyst",
                "text": "Amplifies team output through alignment and emotional intelligence. Ideal for cross-functional leadership. Watch for conflict avoidance that delays hard decisions."
            },
            {
                "trigger": dominant == "C" and trait_scores.get("Execution & Autonomy", 0) >= 70,
                "title": "The Accelerator",
                "text": "Maximizes velocity and unblocks teams through rapid iteration. Thrives in startups and high-uncertainty environments. May sacrifice long-term stability for short-term speed."
            },
            {
                "trigger": dominant == "D" and trait_scores.get("Accountability & Ownership", 0) >= 70,
                "title": "The Sentinel",
                "text": "Takes full ownership and delivers independently. Highly reliable for critical, high-trust assignments. May struggle in highly collaborative or consensus-driven cultures."
            },
            {
                "trigger": (set([dominant, secondary]) == set(["A", "D"])) and trait_scores.get("Analytical Rigor & Quality", 0) >= 60 and trait_scores.get("Execution & Autonomy", 0) >= 60,
                "title": "The Technical Lead",
                "text": "Combines deep technical rigor with autonomous execution. Natural fit for architecture decisions and system design ownership."
            },
            {
                "trigger": (set([dominant, secondary]) == set(["B", "C"])) and trait_scores.get("Collaboration & Synergy", 0) >= 60 and trait_scores.get("Resilience & Pressure Handling", 0) >= 60,
                "title": "The Agile Coach",
                "text": "Blends team facilitation with fast adaptation. Excellent at keeping teams productive during uncertainty and change."
            },
            {
                "trigger": (set([dominant, secondary]) == set(["A", "B"])) and trait_scores.get("Analytical Rigor & Quality", 0) >= 60 and trait_scores.get("Collaboration & Synergy", 0) >= 60,
                "title": "The Bridge",
                "text": "Connects technical depth with team empathy. Ideal for translating between engineering and business stakeholders."
            },
            {
                "trigger": (set([dominant, secondary]) == set(["C", "D"])) and trait_scores.get("Execution & Autonomy", 0) >= 60 and trait_scores.get("Resilience & Pressure Handling", 0) >= 60,
                "title": "The Operator",
                "text": "Combines speed with independence. Excels in crisis response and time-critical deliveries with minimal oversight."
            }
        ]

        # Add the first matching archetype
        for arch in archetypes:
            if arch["trigger"]:
                strategic_insights.append(StrategicInsight(title=arch["title"], text=arch["text"], type="positive"))
                break

        # --- B. Strength Combo Insights (Based on top 2 traits) ---
        sorted_traits = sorted(trait_scores.items(), key=lambda x: x[1], reverse=True)
        top_2_names = [t[0] for t in sorted_traits[:2]]
        
        strength_combos = {
            frozenset(["Execution & Autonomy", "Analytical Rigor & Quality"]): {
                "title": "Precision Executor",
                "text": "Delivers consistently with high quality. Rarely ships defects but may over-engineer simple tasks."
            },
            frozenset(["Execution & Autonomy", "Resilience & Pressure Handling"]): {
                "title": "Pressure Performer",
                "text": "Output increases under deadlines. Reliable for urgent deliveries but needs recovery time after intense sprints."
            },
            frozenset(["Execution & Autonomy", "Accountability & Ownership"]): {
                "title": "Reliable Owner",
                "text": "Takes tasks to completion with full responsibility. Teams trust this person to handle critical path items."
            },
            frozenset(["Analytical Rigor & Quality", "Collaboration & Synergy"]): {
                "title": "Quality Advocate",
                "text": "Elevates team standards through constructive code reviews and shared best practices."
            },
            frozenset(["Analytical Rigor & Quality", "Accountability & Ownership"]): {
                "title": "Standards Guardian",
                "text": "Upholds technical and ethical standards even when it's uncomfortable. Essential for regulated environments."
            },
            frozenset(["Collaboration & Synergy", "Resilience & Pressure Handling"]): {
                "title": "Team Anchor",
                "text": "Stabilizes team morale during crises. The person everyone turns to when things go wrong."
            },
            frozenset(["Collaboration & Synergy", "Accountability & Ownership"]): {
                "title": "Transparent Leader",
                "text": "Combines team awareness with personal integrity. Creates psychologically safe environments."
            },
            frozenset(["Execution & Autonomy", "Collaboration & Synergy"]): {
                "title": "Force Multiplier",
                "text": "Drives individual results while unblocking others. A rare mix of individual productivity and team orchestration."
            },
            frozenset(["Analytical Rigor & Quality", "Resilience & Pressure Handling"]): {
                "title": "Stoic Architect",
                "text": "Maintains technical standards even under extreme pressure. Doesn't compromise on quality during crunch time."
            },
            frozenset(["Resilience & Pressure Handling", "Accountability & Ownership"]): {
                "title": "Crisis Owner",
                "text": "Doesn't just survive pressure — takes ownership of the solution. First to raise their hand when things break."
            }
        }
        
        combo_key = frozenset(top_2_names)
        if combo_key in strength_combos:
            combo = strength_combos[combo_key]
            strategic_insights.append(StrategicInsight(title=combo["title"], text=combo["text"], type="positive"))

        # --- C. Growth Insights (Alerts for low scores) ---
        growth_alerts = {
            "Execution & Autonomy": {
                "title": "Execution Gap",
                "text": "May rely too heavily on others to drive progress. Consider setting personal delivery milestones independent of team cadence."
            },
            "Analytical Rigor & Quality": {
                "title": "Rigor Gap",
                "text": "Decisions may lack sufficient data backing. Consider building a habit of documenting assumptions before acting."
            },
            "Collaboration & Synergy": {
                "title": "Collaboration Gap",
                "text": "Strong individual contributor who may underinvest in team dynamics. Consider proactive knowledge sharing and pairing sessions."
            },
            "Resilience & Pressure Handling": {
                "title": "Adaptability Gap",
                "text": "May struggle with rapid context switching or ambiguous requirements. Consider exposure to shorter sprint cycles."
            },
            "Accountability & Ownership": {
                "title": "Ownership Gap",
                "text": "Tendency to defer responsibility during failures. Building a post-mortem habit can strengthen this muscle."
            }
        }

        for trait_name, score in trait_scores.items():
            if score < 40:
                alert = growth_alerts[trait_name]
                strategic_insights.append(StrategicInsight(title=alert["title"], text=alert["text"], type="warning"))

        # Store profile in DB
        conn = await get_connection()
        now = datetime.now().isoformat()
        
        profile_data = {
            "core_traits": [t.model_dump() for t in core_traits],
            "operating_styles": [s.model_dump() for s in operating_styles],
            "strategic_insights": [i.model_dump() for i in strategic_insights]
        }
        
        await conn.execute("""
            INSERT INTO behavioral_profile (user_id, core_traits, operating_styles, strategic_insights, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                core_traits=excluded.core_traits,
                operating_styles=excluded.operating_styles,
                strategic_insights=excluded.strategic_insights,
                updated_at=excluded.updated_at
        """, (
            user_id, 
            json.dumps(profile_data["core_traits"]), 
            json.dumps(profile_data["operating_styles"]), 
            json.dumps(profile_data["strategic_insights"]),
            now
        ))
        await conn.commit()

        return BehavioralProfile(
            user_id=user_id,
            core_traits=core_traits,
            operating_styles=operating_styles,
            strategic_insights=strategic_insights,
            created_at=datetime.fromisoformat(now), # Approximation for insert
            updated_at=datetime.fromisoformat(now)
        )

    async def get_profile(self, user_id: int) -> BehavioralProfile:
        conn = await get_connection()
        conn.row_factory = None
        async with conn.execute(
            "SELECT core_traits, operating_styles, strategic_insights, created_at, updated_at FROM behavioral_profile WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            return BehavioralProfile(
                user_id=user_id,
                core_traits=[CoreTrait(**t) for t in json.loads(row[0])],
                operating_styles=[OperatingStyle(**s) for s in json.loads(row[1])],
                strategic_insights=[StrategicInsight(**i) for i in json.loads(row[2])],
                created_at=datetime.fromisoformat(row[3]),
                updated_at=datetime.fromisoformat(row[4])
            )
