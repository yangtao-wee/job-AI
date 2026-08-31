import request from './request.js'

export function askAgent(goal){
    return request.post('/agent/ask',{goal},{
        timeout:30000
    })
}