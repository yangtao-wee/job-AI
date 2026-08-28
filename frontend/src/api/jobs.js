import request from './request.js'

export function fetchJobs(){
    // export表示允许其他Vue文件使用它
    return request.get('/jobs')
}

export function matchJob(resumeId,jobId,city,minPay){
    return request.post('/jobs/match',{
        resume_id:resumeId,
        job_id:jobId,
        city:city,
        min_pay:minPay
    })
}

export function analyzeJob(jobId){
    if(!jobId){
        throw new Error('缺少岗位ID')
    // throw、new、Error：【语言固定】。主动停止并报告清楚的前端错误。
    }
    return request.post(`/jobs/${jobId}/analysis`)
}