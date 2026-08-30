import request from './request.js'

export function askRag(question){
    return request.post('/rag/ask',{
        question:question
    },{
        timeout:30000
    })
}