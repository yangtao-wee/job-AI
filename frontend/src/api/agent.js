import request from './request.js'

export function askAgent(goal,history=[]){
    return request.post('/agent/ask',{goal,history},{
        timeout:30000
    })
}
