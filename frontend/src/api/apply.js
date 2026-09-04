import request from './request.js'

// 创建投递记录
export function createApply(reportId){
    return request.post('/applications',{report_id:reportId})
}

// 查询投递列表
export function listApply(){
    return request.get('/applications')
}

// 更新投递记录
export function updateApply(id,data){
    return request.patch(`/applications/${id}`,data)
}