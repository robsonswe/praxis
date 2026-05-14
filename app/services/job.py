from typing import Optional
from app.models.job import JobPost, JobPostCreate
from app.repositories.job import JobRepository


class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    async def list_jobs(self, user_id: int) -> list[JobPost]:
        data = await self.repository.list_by_user(user_id)
        return [JobPost(**row) for row in data]

    async def get_job(self, job_id: int, user_id: int) -> Optional[JobPost]:
        data = await self.repository.get_by_id(job_id, user_id)
        return JobPost(**data) if data else None

    async def create_job(self, user_id: int, data: JobPostCreate) -> JobPost:
        result = await self.repository.create(
            user_id,
            data.title,
            data.company,
            data.location,
            data.job_type,
            data.salary,
            data.link,
            data.description,
            data.company_description
        )
        return JobPost(**result)

    async def update_job(self, job_id: int, user_id: int, data: JobPostCreate) -> bool:
        return await self.repository.update(
            job_id,
            user_id,
            data.title,
            data.company,
            data.location,
            data.job_type,
            data.salary,
            data.link,
            data.description,
            data.company_description
        )

    async def delete_job(self, job_id: int, user_id: int) -> bool:
        return await self.repository.delete(job_id, user_id)
