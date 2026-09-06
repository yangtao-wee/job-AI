import request from './request.js'

export function assistJob(resumeId,jobTitle,company,jdText){
    return request.post('/jobs/report',{
        resume_id:resumeId,
        job_title:jobTitle,
        company:company,
        jd_text:jdText
    },{
        timeout:180000
    })
}

export function fetchRoprts(){
    return request.get('/jobs/reports')
}

export function fetchRoprt(id){
    return request.get(`/jobs/reports/${id}`)
}