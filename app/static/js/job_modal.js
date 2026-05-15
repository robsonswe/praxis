// Job Modal Logic
function openJobModal(job = null) {
    const modal = document.getElementById('jobModal');
    const form = document.getElementById('jobForm');
    const title = document.getElementById('jobModalTitle');
    
    form.reset();
    if (job) {
        title.textContent = 'Edit Role';
        document.getElementById('job-id').value = job.id;
        document.getElementById('job-title').value = job.title;
        document.getElementById('job-company').value = job.company;
        document.getElementById('job-location').value = job.location || '';
        document.getElementById('job-type').value = job.job_type;
        document.getElementById('job-salary').value = job.salary || '';
        document.getElementById('job-link').value = job.link || '';
        document.getElementById('job-description').value = job.description;
        document.getElementById('job-company-description').value = job.company_description || '';
    } else {
        title.textContent = 'Add role';
        document.getElementById('job-id').value = '';
    }
    modal.classList.add('active');
}

function closeJobModal() {
    document.getElementById('jobModal').classList.remove('active');
}

document.getElementById('saveJobBtn').addEventListener('click', async () => {
    const form = document.getElementById('jobForm');
    const data = new FormData(form);
    const jobId = data.get('id');
    const job = {
        id: jobId ? parseInt(jobId) : null,
        title: data.get('title').trim(),
        company: data.get('company').trim(),
        location: data.get('location').trim(),
        job_type: data.get('job_type'),
        salary: data.get('salary').trim(),
        link: data.get('link').trim(),
        description: data.get('description').trim(),
        company_description: data.get('company_description').trim()
    };
    try {
        let result;
        if (jobId) {
            result = await fetchJson(`/api/jobs/${jobId}`, {
                method: 'PUT',
                body: JSON.stringify(job)
            });
            window.dispatchEvent(new CustomEvent('jobUpdated', { detail: { ...job, ...result } }));
        } else {
            result = await fetchJson('/api/jobs', {
                method: 'POST',
                body: JSON.stringify(job)
            });
            window.dispatchEvent(new CustomEvent('jobCreated', { detail: result }));
        }
        closeJobModal();
    } catch (error) {
        console.error('Failed to save job', error);
        showAlert('Error', 'Failed to save role details.');
    }
});
