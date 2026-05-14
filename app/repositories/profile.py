from typing import Optional
from app.database import get_connection


class ProfileRepository:
    async def get_by_user_id(self, user_id: int) -> dict | None:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()
    
    async def update_basic(self, user_id: int, name: str = "", title: str = "", summary: str = "", location: str = "", years_of_experience: int = 0, date_of_birth: str = "", phone: str = "", website: str = "", linkedin: str = "", github: str = "") -> dict | None:
        conn = await get_connection()
        
        # Build dynamic update based on what's provided
        fields = []
        values = []
        
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if summary is not None:
            fields.append("summary = ?")
            values.append(summary)
        if location is not None:
            fields.append("location = ?")
            values.append(location)
        if years_of_experience is not None:
            fields.append("years_of_experience = ?")
            values.append(years_of_experience)
        if date_of_birth is not None:
            fields.append("date_of_birth = ?")
            values.append(date_of_birth)
        if phone is not None:
            fields.append("phone = ?")
            values.append(phone)
        if website is not None:
            fields.append("website = ?")
            values.append(website)
        if linkedin is not None:
            fields.append("linkedin = ?")
            values.append(linkedin)
        if github is not None:
            fields.append("github = ?")
            values.append(github)
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        
        values.append(user_id)
        
        query = "UPDATE users SET " + ", ".join(fields) + " WHERE id = ?"
        await conn.execute(query, values)
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()
    
    async def get_work_experience(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM work_experience WHERE user_id = ? ORDER BY start_date DESC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                row["current"] = bool(row["current"])
            return rows
    
    async def create_work_experience(self, user_id: int, company: str, title: str, experience_type: str, location: str,
                                      start_date: str, end_date: str | None, current: bool, description: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO work_experience (user_id, company, title, experience_type, location, start_date, end_date, current, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, company, title, experience_type, location, start_date, end_date, int(current), description)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "company": company, "title": title,
                "experience_type": experience_type,
                "location": location, "start_date": start_date, "end_date": end_date,
                "current": current, "description": description}
    
    async def update_work_experience(self, exp_id: int, user_id: int, company: str, title: str,
                                                  experience_type: str, location: str, start_date: str, end_date: str | None,
                                                  current: bool, description: str) -> dict | None:
        conn = await get_connection()
        await conn.execute(
                """UPDATE work_experience SET company = ?, title = ?, experience_type = ?, location = ?, start_date = ?,
                    end_date = ?, current = ?, description = ? WHERE id = ? AND user_id = ?""",
                (company, title, experience_type, location, start_date, end_date, int(current), description, exp_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM work_experience WHERE id = ?", (exp_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                row["current"] = bool(row["current"])
            return row
    
    async def delete_work_experience(self, exp_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM work_experience WHERE id = ? AND user_id = ?", (exp_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_education(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM education WHERE user_id = ? ORDER BY start_date DESC", (user_id,)) as cursor:
            return await cursor.fetchall()
    
    async def create_education(self, user_id: int, institution: str, degree: str, field: str,
                               start_date: str, end_date: str, gpa: float | None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO education (user_id, institution, degree, field, start_date, end_date, gpa)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, institution, degree, field, start_date, end_date, gpa)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "institution": institution,
                "degree": degree, "field": field, "start_date": start_date, "end_date": end_date, "gpa": gpa}
    
    async def update_education(self, edu_id: int, user_id: int, institution: str, degree: str,
                                field: str, start_date: str, end_date: str, gpa: float | None) -> dict | None:
        conn = await get_connection()
        await conn.execute(
            """UPDATE education SET institution = ?, degree = ?, field = ?, start_date = ?,
               end_date = ?, gpa = ? WHERE id = ? AND user_id = ?""",
            (institution, degree, field, start_date, end_date, gpa, edu_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM education WHERE id = ?", (edu_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete_education(self, edu_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM education WHERE id = ? AND user_id = ?", (edu_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_certifications(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM certifications WHERE user_id = ? ORDER BY issue_date DESC", (user_id,)) as cursor:
            return await cursor.fetchall()
    
    async def create_certification(self, user_id: int, name: str, issuer: str, issue_date: str,
                                   expiry_date: str | None, credential_id: str | None, url: str | None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO certifications (user_id, name, issuer, issue_date, expiry_date, credential_id, url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, issuer, issue_date, expiry_date, credential_id, url)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "name": name, "issuer": issuer,
                "issue_date": issue_date, "expiry_date": expiry_date, "credential_id": credential_id, "url": url}
    
    async def update_certification(self, cert_id: int, user_id: int, name: str, issuer: str,
                                    issue_date: str, expiry_date: str | None, credential_id: str | None,
                                    url: str | None) -> dict | None:
        conn = await get_connection()
        await conn.execute(
            """UPDATE certifications SET name = ?, issuer = ?, issue_date = ?, expiry_date = ?,
               credential_id = ?, url = ? WHERE id = ? AND user_id = ?""",
            (name, issuer, issue_date, expiry_date, credential_id, url, cert_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM certifications WHERE id = ?", (cert_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete_certification(self, cert_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM certifications WHERE id = ? AND user_id = ?", (cert_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_courses(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM courses WHERE user_id = ? ORDER BY completion_date DESC", (user_id,)) as cursor:
            return await cursor.fetchall()
    
    async def create_course(self, user_id: int, name: str, provider: str, completion_date: str,
                            certificate_url: str | None, description: str | None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO courses (user_id, name, provider, completion_date, certificate_url, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, provider, completion_date, certificate_url, description)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "name": name, "provider": provider,
                "completion_date": completion_date, "certificate_url": certificate_url, "description": description}
    
    async def update_course(self, course_id: int, user_id: int, name: str, provider: str,
                            completion_date: str, certificate_url: str | None, description: str | None) -> dict | None:
        conn = await get_connection()
        await conn.execute(
            """UPDATE courses SET name = ?, provider = ?, completion_date = ?, certificate_url = ?,
               description = ? WHERE id = ? AND user_id = ?""",
            (name, provider, completion_date, certificate_url, description, course_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete_course(self, course_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_achievements(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY date DESC", (user_id,)) as cursor:
            return await cursor.fetchall()
    
    async def create_achievement(self, user_id: int, title: str, category: str, description: str,
                                  date: str, organization: str | None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO achievements (user_id, title, category, description, date, organization)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, title, category, description, date, organization)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "title": title, "category": category,
                "description": description, "date": date, "organization": organization}
    
    async def update_achievement(self, ach_id: int, user_id: int, title: str, category: str,
                                  description: str, date: str, organization: str | None) -> dict | None:
        conn = await get_connection()
        await conn.execute(
            """UPDATE achievements SET title = ?, category = ?, description = ?, date = ?,
               organization = ? WHERE id = ? AND user_id = ?""",
            (title, category, description, date, organization, ach_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM achievements WHERE id = ?", (ach_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete_achievement(self, ach_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM achievements WHERE id = ? AND user_id = ?", (ach_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_skills(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY name", (user_id,)) as cursor:
            return await cursor.fetchall()
    
    async def create_skill(self, user_id: int, name: str, category: str, proficiency: int,
                           years_of_experience: int | None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO skills (user_id, name, category, proficiency, years_of_experience)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, name, category, proficiency, years_of_experience)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "name": name, "category": category,
                "proficiency": proficiency, "years_of_experience": years_of_experience}
    
    async def update_skill(self, skill_id: int, user_id: int, name: str, category: str,
                           proficiency: int, years_of_experience: int | None) -> dict | None:
        conn = await get_connection()
        await conn.execute(
            """UPDATE skills SET name = ?, category = ?, proficiency = ?, years_of_experience = ?
               WHERE id = ? AND user_id = ?""",
            (name, category, proficiency, years_of_experience, skill_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete_skill(self, skill_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0
    
    async def get_projects(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY start_date DESC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                if row.get("technologies"):
                    row["technologies"] = row["technologies"].split("|")
                else:
                    row["technologies"] = []
                if row.get("outcomes"):
                    row["outcomes"] = row["outcomes"].split("|")
                else:
                    row["outcomes"] = []
            return rows
    
    async def create_project(self, user_id: int, name: str, description: str, role: str,
                             technologies: list[str], outcomes: list[str], start_date: str,
                             end_date: str | None) -> dict:
        conn = await get_connection()
        tech_str = "|".join(technologies) if technologies else ""
        outcomes_str = "|".join(outcomes) if outcomes else ""
        cursor = await conn.execute(
            """INSERT INTO projects (user_id, name, description, role, technologies, outcomes, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, description, role, tech_str, outcomes_str, start_date, end_date)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "name": name, "description": description,
                "role": role, "technologies": technologies, "outcomes": outcomes,
                "start_date": start_date, "end_date": end_date}
    
    async def update_project(self, proj_id: int, user_id: int, name: str, description: str,
                              role: str, technologies: list[str], outcomes: list[str],
                              start_date: str, end_date: str | None) -> dict | None:
        conn = await get_connection()
        tech_str = "|".join(technologies) if technologies else ""
        outcomes_str = "|".join(outcomes) if outcomes else ""
        await conn.execute(
            """UPDATE projects SET name = ?, description = ?, role = ?, technologies = ?, outcomes = ?,
               start_date = ?, end_date = ? WHERE id = ? AND user_id = ?""",
            (name, description, role, tech_str, outcomes_str, start_date, end_date, proj_id, user_id)
        )
        await conn.commit()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM projects WHERE id = ?", (proj_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                row["technologies"] = row["technologies"].split("|") if row.get("technologies") else []
                row["outcomes"] = row["outcomes"].split("|") if row.get("outcomes") else []
            return row
    
    async def delete_project(self, proj_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (proj_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0