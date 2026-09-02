import request from './request.js'

export function assistJob(resumeId,jobTitle,company,jdText){
    return request.post('/jobs/assist',{
        resume_id:resumeId,
        job_title:jobTitle,
        company:company,
        jd_text:jdText
    },{
        timeout:60000
    })
}