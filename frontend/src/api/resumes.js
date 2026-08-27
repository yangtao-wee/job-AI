import request from "./request.js"

export function fetchMyResumes(){
    return request.get('/resumes/me')
}