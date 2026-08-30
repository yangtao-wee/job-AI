import request from './request.js'

export function askRag(question,parts){
    return request.post('/rag/ask',{
        question:question,
        parts:parts
    },{
        timeout:30000
    })
}