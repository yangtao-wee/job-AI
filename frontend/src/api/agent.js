import request from './request.js'

export function askAgent(goal,history=[]){
    return request.post('/agent/ask',{goal,history},{
        // Agent 可能连续执行“查列表 → 查详情 → 总结”三轮模型请求。
        timeout:120000
    })
}
