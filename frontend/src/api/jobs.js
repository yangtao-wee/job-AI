import request from './request.js'

export function fetchJobs(){
    // export表示允许其他Vue文件使用它
    return request.get('/jobs')
}

export function matchJob(resumeId,jobId){
    return request.post('/jobs/match',{
        resume_id:resumeId,
        job_id:jobId
    })
}